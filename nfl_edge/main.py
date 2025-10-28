
import yaml
import numpy as np
from pathlib import Path
from datetime import date
try:
    from nfl_edge.schedule_fetcher import get_upcoming_matchups
    THIS_WEEK = get_upcoming_matchups()
except Exception:
    from schedules import THIS_WEEK
from nfl_edge.data_ingest import fetch_teamweeks_live, fetch_market_lines_live, fetch_weather_for_matchups, fetch_injury_index
from nfl_edge.features import build_features, join_matchups, apply_weather_and_injuries
from nfl_edge.model import fit_expected_points_model, predict_expected_points
from nfl_edge.simulate import monte_carlo
from nfl_edge.kelly import add_betting_columns, generate_betting_card
from nfl_edge.situational_features import add_all_situational_features
def run_week(week_number=None, matchups=None):
    """
    Run predictions for a specific week.
    
    Args:
        week_number: Optional week number (1-18). If None, uses current week.
        matchups: Optional list of (away, home) tuples. If None, uses THIS_WEEK.
    """
    cfg = yaml.safe_load(open("config.yaml"))
    teamweeks = fetch_teamweeks_live()
    lines = fetch_market_lines_live()
    
    # Manual line overrides (if needed)
    # manual_lines = {}
    # lines.update(manual_lines)
    
    # Use provided matchups or default to THIS_WEEK
    games = matchups if matchups is not None else THIS_WEEK
    current_week = week_number if week_number is not None else 1
    
    feats = build_features(teamweeks, recent_weight=cfg["recent_weight"])
    base = join_matchups(feats, games)
    weather = fetch_weather_for_matchups(matchups=games)
    injuries = fetch_injury_index(matchups=games)
    situational = add_all_situational_features(games, current_week=current_week)
    matches = apply_weather_and_injuries(base, weather, injuries, situational)
    models = fit_expected_points_model(matches)
    calibration = cfg.get("score_calibration_factor", 1.0)
    muA, muH = predict_expected_points(models, matches, cfg["home_field_pts"], calibration)
    spread = []; total = []
    missing_games = []
    for i, (_, r) in enumerate(matches.iterrows()):
        m = lines.get((r["away"], r["home"]), {})
        s = m.get("spread_home")
        t = m.get("total")
        # Use model predictions as fallback if market lines are missing
        if s is None or t is None:
            missing_games.append(f"{r['away']}@{r['home']}")
            if s is None:
                s = muH[i] - muA[i]  # home advantage in points
            if t is None:
                t = muA[i] + muH[i]
        spread.append(s)
        total.append(t)
    if missing_games:
        print(f"WARNING: Missing market lines for {len(missing_games)} game(s), using model predictions as fallback:")
        for g in missing_games:
            print(f"  - {g}")
    spread = np.array(spread, dtype=float); total = np.array(total, dtype=float)
    out = monte_carlo(muA, muH, team_sd=cfg["team_sd"], n_sims=cfg["n_sims"], spread_home=spread, total_line=total)
    df = matches.copy()
    df["Exp score (away-home)"] = [f"{round(a)}-{round(h)}" for a,h in zip(muA, muH)]
    df["Model spread home-"] = out["model_spread_home"]
    df["Model total"] = out["model_total"]
    df["Spread used (home-)"] = out["spread_used"]
    df["Total used"] = out["total_used"]
    df["Home cover %"] = (out["home_cover_prob"]*100).round(1)
    df["Home win %"] = (out["home_win_prob"]*100).round(1)
    df["Over %"] = (out["over_prob"]*100).round(1)
    df["Edge_pts"] = df["Model spread home-"] - df["Spread used (home-)"]
    df["Edge_total_pts"] = df["Model total"] - df["Total used"]
    
    # Add betting intelligence: EV, Kelly sizing, recommendations
    bankroll = cfg.get("bankroll", 10000.0)
    min_ev = cfg.get("min_ev", 0.02)
    kelly_cap = cfg.get("kelly_fraction", 0.25)
    
    df = add_betting_columns(df, bankroll=bankroll, min_ev=min_ev, kelly_fraction_cap=kelly_cap)
    
    # Generate betting card report
    betting_card = generate_betting_card(df, min_ev=min_ev)
    
    Path("artifacts").mkdir(exist_ok=True)
    dt = date.today().isoformat()
    week_suffix = f"week{current_week}_" if week_number is not None else ""
    proj = Path("artifacts")/f"predictions_2025_{week_suffix}{dt}.csv"
    clv  = Path("artifacts")/f"week_{week_suffix}{dt}_model_line_vs_market.csv"
    dbg  = Path("artifacts")/f"week_{week_suffix}{dt}_debug_sample.csv"
    bets = Path("artifacts")/f"week_{week_suffix}{dt}_betting_card.txt"
    
    # Enhanced projections with betting columns and confidence levels
    df_out = df[["away","home","Exp score (away-home)","Model spread home-","Spread used (home-)","Edge_pts",
                 "Model total","Total used","Edge_total_pts","Home win %","Home cover %","Over %",
                 "EV_spread","EV_total","Kelly_spread_pct","Kelly_total_pct",
                 "Stake_spread","Stake_total","Rec_spread","Rec_total","Best_bet",
                 "confidence_level","confidence_pct"]]
    df_out.to_csv(proj, index=False)
    
    df[[ "away","home","away_OFF_EPA","home_DEF_EPA","home_OFF_EPA","away_DEF_EPA",
         "away_OFF_SR","home_DEF_SR","home_OFF_SR","away_DEF_SR",
         "away_PF","home_PF","away_PF_adj","home_PF_adj",
         "wind_kph","is_dome","away_injury","home_injury"]].to_csv(dbg, index=False)
    df[[ "away","home","Model spread home-","Spread used (home-)","Edge_pts","Model total","Total used","Edge_total_pts"]].to_csv(clv, index=False)
    
    # Write betting card
    bets.write_text(betting_card)
    
    print(f"Wrote {proj}\nWrote {clv}\nWrote {dbg}\nWrote {bets}")
    
    # Auto-record predictions for accuracy tracking
    try:
        from nfl_edge.accuracy_tracker import create_tracker
        tracker = create_tracker()
        
        # Determine current week and season
        current_week = dt.isocalendar()[1] - 35  # Approximate NFL week
        current_season = dt.year
        
        print(f"\n📊 Recording predictions for accuracy tracking (Week {current_week})...")
        
        for _, row in df_out.iterrows():
            # Record prediction
            tracker.record_prediction(
                week=current_week,
                season=current_season,
                away=row['away'],
                home=row['home'],
                your_model={
                    'away_win_prob': 100 - row['Home win %'],
                    'home_win_prob': row['Home win %'],
                    'spread': row['Model spread home-'],
                    'total': row['Model total']
                },
                fivethirtyeight=None,
                vegas=None
            )
        
        print(f"✅ Recorded {len(df_out)} predictions for Week {current_week}")
        print("   These will be compared to actual results after games complete")
        print("   Visit http://localhost:9876/accuracy to track performance")
        
    except Exception as e:
        print(f"⚠️ Could not auto-record predictions: {e}")
        print("   Predictions saved to CSV but not tracked for accuracy")
    print("\n" + betting_card)
    
    return proj, clv, dbg, bets
if __name__ == "__main__":
    run_week()
