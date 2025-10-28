"""
Quick update - add situational factors to predictions without slow LLM calls.
"""

import pandas as pd
from pathlib import Path
from edge_hunt.situational_factors_fast import get_all_situational_adjustments_fast
from market_implied_scores import market_to_implied_score, implied_score_to_spread_total
from nfl_edge.adjusted_recommendations import generate_adjusted_recommendations

# Find latest predictions
artifacts = Path("artifacts")
csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
current_week_files = [f for f in csvs if '_week' not in f.name]
latest = current_week_files[-1] if current_week_files else csvs[-1]

print(f"📁 Loading: {latest.name}")
df = pd.read_csv(latest)

print(f"📊 Processing {len(df)} games...")
print()

# Add columns
df['market_implied_away'] = 0.0
df['market_implied_home'] = 0.0
df['adjusted_away'] = 0.0
df['adjusted_home'] = 0.0
df['adjusted_spread'] = 0.0
df['adjusted_total'] = 0.0
df['has_edge_hunt_signal'] = False
df['edge_hunt_signals'] = None

count_with_signals = 0

for idx, row in df.iterrows():
    away = row['away']
    home = row['home']
    market_spread = row['Spread used (home-)']
    market_total = row['Total used']
    
    # Get market-implied scores
    market_away, market_home = market_to_implied_score(market_spread, market_total)
    df.at[idx, 'market_implied_away'] = market_away
    df.at[idx, 'market_implied_home'] = market_home
    
    # Get situational adjustments
    sit = get_all_situational_adjustments_fast(away, home)
    
    # Apply per-team adjustments (not split!)
    adj_away = market_away + sit.get('away_adjustment', 0.0)
    adj_home = market_home + sit.get('home_adjustment', 0.0)
    
    adj_spread, adj_total = implied_score_to_spread_total(adj_away, adj_home)
    
    df.at[idx, 'adjusted_away'] = adj_away
    df.at[idx, 'adjusted_home'] = adj_home
    df.at[idx, 'adjusted_spread'] = adj_spread
    df.at[idx, 'adjusted_total'] = adj_total
    
    if sit['has_adjustment']:
        count_with_signals += 1
        df.at[idx, 'has_edge_hunt_signal'] = True
        df.at[idx, 'edge_hunt_signals'] = [
            {
                'type': 'situational',
                'icon': '📊',
                'badge': 'SITUATIONAL EDGE',
                'badge_color': 'info',
                'edge_pts': abs(sit['spread_adjustment']) + abs(sit['total_adjustment']),
                'explanation': ', '.join(sit['explanations'][:2]),
                'details': sit['explanations']
            }
        ]
        
        print(f"✅ {away} @ {home}: {len(sit['explanations'])} factors")

print()
print(f"📊 {count_with_signals}/{len(df)} games have situational signals")
print()

# Generate betting recommendations
print("🎯 Generating betting recommendations...")
df = generate_adjusted_recommendations(df, min_spread_edge=2.0, min_total_edge=2.0)

# Count recommendations
spread_bets = (df['Rec_spread'] != 'SKIP').sum()
total_bets = (df['Rec_total'] != 'SKIP').sum()
print(f"   Spread bets: {spread_bets}")
print(f"   Total bets: {total_bets}")
print()

# Save
print(f"💾 Saving to {latest.name}...")
df.to_csv(latest, index=False)
print("✅ Done!")

