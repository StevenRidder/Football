"""
Full update - add ALL adjustments (situational + injuries) to predictions.
"""

import pandas as pd
from pathlib import Path
from edge_hunt.integrate_signals import enrich_predictions_with_signals

# Find latest predictions
artifacts = Path("artifacts")
csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
current_week_files = [f for f in csvs if '_week' not in f.name]
latest = current_week_files[-1] if current_week_files else csvs[-1]

print(f"📁 Loading: {latest.name}")
df = pd.read_csv(latest)

# Get week and season
week = int(df['week'].iloc[0]) if 'week' in df.columns else 9
season = int(df['season'].iloc[0]) if 'season' in df.columns else 2025

print(f"📊 Processing Week {week}, {season} - {len(df)} games...")
print("⚠️  This will take ~2-3 minutes due to LLM injury detection...")
print()

# Enrich with ALL signals (situational + injuries)
df = enrich_predictions_with_signals(df, week=week, season=season)

# Count signals
has_signals = df['has_edge_hunt_signal'].sum()
spread_bets = (df['Rec_spread'] != 'SKIP').sum() if 'Rec_spread' in df.columns else 0
total_bets = (df['Rec_total'] != 'SKIP').sum() if 'Rec_total' in df.columns else 0

print()
print(f"✅ {has_signals}/{len(df)} games have signals")
print(f"🎯 Betting recommendations:")
print(f"   Spread bets: {spread_bets}")
print(f"   Total bets: {total_bets}")
print()

# Save
print(f"💾 Saving to {latest.name}...")
df.to_csv(latest, index=False)
print("✅ Done!")

