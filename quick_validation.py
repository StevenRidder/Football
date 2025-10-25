"""
Quick validation: Check if model's total predictions are systematically too high.
Compares recent actual game totals to what the model would predict.
"""

import pandas as pd
import numpy as np
from nfl_edge.data_ingest import fetch_teamweeks_live

print("=" * 80)
print("QUICK VALIDATION: Are Model Totals Realistic?")
print("=" * 80)

# Fetch current season data
teamweeks = fetch_teamweeks_live()

# Calculate actual totals per week
print("\n📊 Actual NFL Totals This Season (2025):")
print("-" * 80)

week_totals = []
for week in sorted(teamweeks['week'].unique()):
    week_data = teamweeks[teamweeks['week'] == week]
    
    # For each game (each team appears once per week)
    total_points = week_data['points'].sum() / 2  # Divide by 2 since each game counted twice
    n_games = len(week_data) / 2
    avg_total = total_points / n_games if n_games > 0 else 0
    
    week_totals.append({
        'week': week,
        'avg_total': avg_total,
        'n_games': n_games
    })
    
    print(f"Week {week:2d}: {n_games:2.0f} games, Avg Total: {avg_total:.1f} points")

df_weeks = pd.DataFrame(week_totals)
season_avg = df_weeks['avg_total'].mean()

print(f"\n🎯 Season Average Total: {season_avg:.1f} points per game")

print("\n" + "=" * 80)
print("COMPARISON TO CURRENT MODEL:")
print("=" * 80)

# Current model predictions
current_model_avg = 66.9  # From earlier analysis
market_avg = 46.4

print(f"\nActual Season Average:  {season_avg:.1f} points")
print(f"Market Average (today): {market_avg:.1f} points")
print(f"Model Average (today):  {current_model_avg:.1f} points")

print(f"\n🚨 Model vs Reality:    {current_model_avg - season_avg:+.1f} points")
print(f"🚨 Model vs Market:     {current_model_avg - market_avg:+.1f} points")

if current_model_avg > season_avg + 10:
    print(f"\n❌ MODEL IS TOO HIGH by {current_model_avg - season_avg:.1f} points!")
    print("   This explains why it always recommends OVER.")
elif current_model_avg < season_avg - 10:
    print(f"\n❌ MODEL IS TOO LOW by {season_avg - current_model_avg:.1f} points!")
    print("   This would recommend UNDER (but we're not seeing that).")
else:
    print(f"\n✅ Model is reasonably calibrated (within 10 points)")

print("\n" + "=" * 80)
print("POSSIBLE FIXES:")
print("=" * 80)
print("""
1. SCALE DOWN PREDICTIONS
   Multiply model totals by calibration factor:
   factor = actual_avg / model_avg = {:.3f}
   Example: 66.9 × {:.3f} = {:.1f}

2. ADD DEFENSIVE WEIGHTING
   Model might be overweighting offense, underweighting defense

3. ADJUST HOME FIELD ADVANTAGE
   Current: +1.5 pts might be contributing to high totals

4. TUNE REGRESSION PARAMETERS
   Ridge alpha might need adjustment

5. RUN FULL BACKTEST
   Test calibration on Weeks 1-7 to find optimal correction
""".format(
    season_avg / current_model_avg if current_model_avg > 0 else 1.0,
    season_avg / current_model_avg if current_model_avg > 0 else 1.0,
    current_model_avg * (season_avg / current_model_avg) if current_model_avg > 0 else season_avg
))

print("\n" + "=" * 80)
print("IMMEDIATE ACTION:")
print("=" * 80)
print(f"""
Add to config.yaml:

  total_calibration_factor: {season_avg / current_model_avg if current_model_avg > 0 else 1.0:.3f}

Then in simulate.py, multiply predicted totals by this factor before Monte Carlo.
""")


