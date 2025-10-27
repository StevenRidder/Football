#!/usr/bin/env python3
"""
Backfill historical predictions for weeks 1-7
Generates predictions for each week and stores them in the database
"""
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
from nfl_edge.data_ingest import fetch_teamweeks_live, fetch_market_lines_live, fetch_weather_for_matchups, fetch_injury_index
from nfl_edge.features import build_features, join_matchups, apply_weather_and_injuries
from nfl_edge.model import fit_expected_points_model, predict_expected_points
from nfl_edge.simulate import monte_carlo
from nfl_edge.kelly import add_betting_columns, generate_betting_card
from nfl_edge.situational_features import add_all_situational_features
from nfl_edge.schedule_fetcher import get_upcoming_matchups
import requests


def get_week_schedule(season: int, week: int):
    """Get schedule for a specific week from ESPN"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {'seasontype': 2, 'week': week, 'year': season}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            matchups = []
            
            for event in data.get('events', []):
                competition = event.get('competitions', [{}])[0]
                competitors = competition.get('competitors', [])
                
                if len(competitors) >= 2:
                    home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
                    away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
                    
                    home_abbr = home.get('team', {}).get('abbreviation')
                    away_abbr = away.get('team', {}).get('abbreviation')
                    
                    if home_abbr and away_abbr:
                        matchups.append((away_abbr, home_abbr))
            
            return matchups
    except Exception as e:
        print(f"Error fetching schedule for week {week}: {e}")
        return []


def generate_predictions_for_week(week: int, season: int = 2025):
    """Generate predictions for a specific historical week"""
    print(f"\n{'='*60}")
    print(f"Generating predictions for Week {week} ({season})")
    print(f"{'='*60}")
    
    cfg = yaml.safe_load(open("config.yaml"))
    
    # Get schedule for this week
    matchups = get_week_schedule(season, week)
    
    if not matchups:
        print(f"❌ No games found for week {week}")
        return None
    
    print(f"Found {len(matchups)} games")
    
    # Fetch data
    print("Fetching team data...")
    
    # For early weeks of 2025, use 2024 data as training
    # For later weeks, use current 2025 data
    if week <= 4:
        # Use 2024 season data (weeks 10-18 for recency)
        print(f"Using 2024 season data for training (weeks 10-18)")
        url = "https://github.com/nflverse/nflverse-data/releases/download/pbp/stats_team_week_2024.csv"
        import pandas as pd
        teamweeks = pd.read_csv(url)
        teamweeks = teamweeks[(teamweeks['season_type'] == 'REG') & (teamweeks['week'] >= 10)].copy()
    else:
        # Use current 2025 season data through previous week
        print(f"Using 2025 season data through week {week-1}")
        teamweeks = fetch_teamweeks_live()
        teamweeks = teamweeks[teamweeks['week'] < week].copy()
    
    if teamweeks.empty:
        print(f"❌ No training data available for week {week}")
        return None
    
    print(f"Using {len(teamweeks)} team-weeks of training data")
    
    # Build features
    print("Building features...")
    feats = build_features(teamweeks, recent_weight=cfg["recent_weight"])
    
    # Create matchups
    print("Creating matchups...")
    base = join_matchups(feats, matchups)
    
    # Get weather and injuries (using live data as approximation)
    print("Fetching weather and injuries...")
    weather = fetch_weather_for_matchups(matchups=matchups)
    injuries = fetch_injury_index(matchups=matchups)
    situational = add_all_situational_features(matchups, current_week=week)
    
    # Apply adjustments
    matches = apply_weather_and_injuries(base, weather, injuries, situational)
    
    # Train model
    print("Training model...")
    models = fit_expected_points_model(matches)
    
    # Predict
    print("Generating predictions...")
    calibration = cfg.get("score_calibration_factor", 1.0)
    muA, muH = predict_expected_points(models, matches, cfg["home_field_pts"], calibration)
    
    # Get market lines (using live data as approximation)
    lines = fetch_market_lines_live()
    
    spread = []
    total = []
    for i, (_, r) in enumerate(matches.iterrows()):
        m = lines.get((r["away"], r["home"]), {})
        s = m.get("spread_home", muH[i] - muA[i])
        t = m.get("total", muA[i] + muH[i])
        spread.append(s)
        total.append(t)
    
    spread = np.array(spread, dtype=float)
    total = np.array(total, dtype=float)
    
    # Monte Carlo simulation
    print("Running Monte Carlo simulation...")
    out = monte_carlo(muA, muH, team_sd=cfg["team_sd"], n_sims=cfg["n_sims"], 
                     spread_home=spread, total_line=total)
    
    # Build results dataframe
    df = matches.copy()
    df["week"] = week
    df["Exp score (away-home)"] = [f"{a:.1f}-{h:.1f}" for a, h in zip(muA, muH)]
    df["Model spread home-"] = out["model_spread_home"]
    df["Model total"] = out["model_total"]
    df["Spread used (home-)"] = out["spread_used"]
    df["Total used"] = out["total_used"]
    df["Home cover %"] = (out["home_cover_prob"] * 100).round(1)
    df["Home win %"] = (out["home_win_prob"] * 100).round(1)
    df["Over %"] = (out["over_prob"] * 100).round(1)
    df["Edge_pts"] = df["Model spread home-"] - df["Spread used (home-)"]
    df["Edge_total_pts"] = df["Model total"] - df["Total used"]
    
    # Add betting intelligence
    bankroll = cfg.get("bankroll", 10000.0)
    min_ev = cfg.get("min_ev", 0.02)
    kelly_cap = cfg.get("kelly_fraction", 0.25)
    
    df = add_betting_columns(df, bankroll=bankroll, min_ev=min_ev, kelly_fraction_cap=kelly_cap)
    
    print(f"✅ Generated {len(df)} predictions")
    
    return df


def main():
    """Generate predictions for weeks 1-7"""
    Path("artifacts").mkdir(exist_ok=True)
    
    all_predictions = []
    
    for week in range(1, 8):
        try:
            df = generate_predictions_for_week(week)
            
            if df is not None:
                # Save individual week file
                week_date = date(2025, 9, 1) + timedelta(weeks=week-1)  # Approximate dates
                filename = f"artifacts/predictions_2025_week{week}_{week_date.isoformat()}.csv"
                df.to_csv(filename, index=False)
                print(f"💾 Saved to {filename}")
                
                all_predictions.append(df)
        except Exception as e:
            print(f"❌ Error generating week {week}: {e}")
            import traceback
            traceback.print_exc()
    
    # Combine all predictions
    if all_predictions:
        combined = pd.concat(all_predictions, ignore_index=True)
        combined.to_csv("artifacts/predictions_weeks_1-7_combined.csv", index=False)
        print(f"\n{'='*60}")
        print(f"✅ Generated predictions for {len(all_predictions)} weeks")
        print(f"💾 Combined file: artifacts/predictions_weeks_1-7_combined.csv")
        print(f"{'='*60}")
        
        # Summary statistics
        print("\n📊 SUMMARY:")
        print(f"Total games: {len(combined)}")
        print(f"Recommended bets: {combined['best_bet'].notna().sum()}")
        print(f"Average EV: {combined['ev'].mean()*100:.2f}%")
        print(f"Total stake: ${combined['kelly_stake'].sum():.0f}")


if __name__ == "__main__":
    main()

