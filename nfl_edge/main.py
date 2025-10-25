
import yaml, numpy as np, pandas as pd
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
def run_week():
    cfg = yaml.safe_load(open("config.yaml"))
    teamweeks = fetch_teamweeks_live()
    lines = fetch_market_lines_live()
    
    # Manual line overrides to match user's casino
    manual_lines = {
        ("CHI", "BAL"): {"spread_home": -6.5, "total": 47.5},
        ("BUF", "CAR"): {"spread_home": +7.5, "total": 47.5},
        ("MIN", "LAC"): {"spread_home": -3.0, "total": 44.5},  # User's casino: MIN +3
    }
    lines.update(manual_lines)
    
    feats = build_features(teamweeks, recent_weight=cfg["recent_weight"])
    base = join_matchups(feats, THIS_WEEK)
    weather = fetch_weather_for_matchups(matchups=THIS_WEEK)
    injuries = fetch_injury_index(matchups=THIS_WEEK)
    matches = apply_weather_and_injuries(base, weather, injuries)
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
    df["Exp score (away-home)"] = [f"{a:.1f}-{h:.1f}" for a,h in zip(muA, muH)]
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
    proj = Path("artifacts")/f"week_{dt}_projections.csv"
    clv  = Path("artifacts")/f"week_{dt}_model_line_vs_market.csv"
    dbg  = Path("artifacts")/f"week_{dt}_debug_sample.csv"
    bets = Path("artifacts")/f"week_{dt}_betting_card.txt"
    
    # Enhanced projections with betting columns
    df_out = df[["away","home","Exp score (away-home)","Model spread home-","Spread used (home-)","Edge_pts",
                 "Model total","Total used","Edge_total_pts","Home win %","Home cover %","Over %",
                 "EV_spread","EV_total","Kelly_spread_pct","Kelly_total_pct",
                 "Stake_spread","Stake_total","Rec_spread","Rec_total","Best_bet"]]
    df_out.to_csv(proj, index=False)
    
    df[[ "away","home","away_OFF_EPA","home_DEF_EPA","home_OFF_EPA","away_DEF_EPA",
         "away_OFF_SR","home_DEF_SR","home_OFF_SR","away_DEF_SR",
         "away_PF","home_PF","away_PF_adj","home_PF_adj",
         "wind_kph","is_dome","away_injury","home_injury"]].to_csv(dbg, index=False)
    df[[ "away","home","Model spread home-","Spread used (home-)","Edge_pts","Model total","Total used","Edge_total_pts"]].to_csv(clv, index=False)
    
    # Write betting card
    bets.write_text(betting_card)
    
    print(f"Wrote {proj}\nWrote {clv}\nWrote {dbg}\nWrote {bets}")
    print("\n" + betting_card)
    
    return proj, clv, dbg, bets
if __name__ == "__main__":
    run_week()
