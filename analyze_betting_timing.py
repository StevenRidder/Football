#!/usr/bin/env python3
"""
Analyze optimal betting timing and team-specific performance
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load backtest results
backtest = pd.read_csv('artifacts/definitive_backtest_20251028_162707.csv')

print("=" * 70)
print("🔬 DEEP DIVE ANALYSIS")
print("=" * 70)

# 1. Team-by-team performance
print("\n📊 TEAM-BY-TEAM PERFORMANCE (as underdog):")
print("  (Only showing teams with 5+ games)")

# When we bet the underdog
underdog_bets = backtest[backtest['bet_side'] == 'AWAY'].copy()

for team in sorted(underdog_bets['away'].unique()):
    team_df = underdog_bets[underdog_bets['away'] == team]
    if len(team_df) >= 5:
        wins = (team_df['result'] == 'WIN').sum()
        losses = (team_df['result'] == 'LOSS').sum()
        wr = wins / (wins + losses) if (wins + losses) > 0 else 0
        avg_spread = team_df['spread_home_first'].mean()
        
        status = "🔥" if wr >= 0.60 else "✅" if wr >= 0.52 else "❌"
        print(f"  {team:3s}: {len(team_df):2d} games, {wr:.1%} WR, avg spread: {avg_spread:+.1f} {status}")

# 2. Team-by-team performance as favorite
print("\n📊 TEAM-BY-TEAM PERFORMANCE (as favorite):")
print("  (Only showing teams with 5+ games)")

favorite_bets = backtest[backtest['bet_side'] == 'HOME'].copy()

for team in sorted(favorite_bets['home'].unique()):
    team_df = favorite_bets[favorite_bets['home'] == team]
    if len(team_df) >= 5:
        wins = (team_df['result'] == 'WIN').sum()
        losses = (team_df['result'] == 'LOSS').sum()
        wr = wins / (wins + losses) if (wins + losses) > 0 else 0
        avg_spread = team_df['spread_home_first'].mean()
        
        status = "🔥" if wr >= 0.60 else "✅" if wr >= 0.52 else "❌"
        print(f"  {team:3s}: {len(team_df):2d} games, {wr:.1%} WR, avg spread: {avg_spread:+.1f} {status}")

# 3. Big dog performance by team
print("\n🎯 BIG DOG PERFORMANCE BY TEAM:")
print("  (7+ point underdogs only)")

big_dogs = backtest[backtest['spread_home_first'] <= -7].copy()

for team in sorted(big_dogs['away'].unique()):
    team_df = big_dogs[big_dogs['away'] == team]
    if len(team_df) >= 2:
        wins = (team_df['result'] == 'WIN').sum()
        losses = (team_df['result'] == 'LOSS').sum()
        wr = wins / (wins + losses) if (wins + losses) > 0 else 0
        avg_spread = team_df['spread_home_first'].mean()
        
        status = "🔥" if wr >= 0.70 else "✅" if wr >= 0.60 else "⚠️" if wr >= 0.50 else "❌"
        print(f"  {team:3s}: {len(team_df):2d} games, {wr:.1%} WR, avg spread: {avg_spread:+.1f} {status}")

# 4. OL stress correlation
print("\n🏋️  OL STRESS CORRELATION:")

# High OL stress games (away team has high stress)
high_stress_away = backtest[backtest['ol_pass_stress_away'] > 0.1].copy()
low_stress_away = backtest[backtest['ol_pass_stress_away'] <= 0.1].copy()

if len(high_stress_away) > 0:
    wins = (high_stress_away['result'] == 'WIN').sum()
    losses = (high_stress_away['result'] == 'LOSS').sum()
    wr = wins / (wins + losses) if (wins + losses) > 0 else 0
    print(f"  High away OL stress: {len(high_stress_away)} games, {wr:.1%} WR")

if len(low_stress_away) > 0:
    wins = (low_stress_away['result'] == 'WIN').sum()
    losses = (low_stress_away['result'] == 'LOSS').sum()
    wr = wins / (wins + losses) if (wins + losses) > 0 else 0
    print(f"  Low away OL stress:  {len(low_stress_away)} games, {wr:.1%} WR")

# 5. Best parlay combinations
print("\n🎰 OPTIMAL PARLAY STRATEGY:")

# Big dogs only
big_dogs_only = backtest[backtest['spread_home_first'] <= -7].copy()
wins = (big_dogs_only['result'] == 'WIN').sum()
losses = (big_dogs_only['result'] == 'LOSS').sum()
wr = wins / (wins + losses) if (wins + losses) > 0 else 0

print(f"\n  Strategy 1: Big Dogs Only (7+ pts)")
print(f"    Games: {len(big_dogs_only)}")
print(f"    Win rate: {wr:.1%}")
print(f"    2-team parlay ROI: {((wr**2)*2.64 - (1-wr**2))*100:+.1f}%")
print(f"    3-team parlay ROI: {((wr**3)*6.0 - (1-wr**3))*100:+.1f}%")
print(f"    4-team parlay ROI: {((wr**4)*12.28 - (1-wr**4))*100:+.1f}%")

# Small favs only
small_favs = backtest[(backtest['spread_home_first'] > 0) & (backtest['spread_home_first'] <= 3)].copy()
wins = (small_favs['result'] == 'WIN').sum()
losses = (small_favs['result'] == 'LOSS').sum()
wr = wins / (wins + losses) if (wins + losses) > 0 else 0

print(f"\n  Strategy 2: Small Favs Only (0-3 pts)")
print(f"    Games: {len(small_favs)}")
print(f"    Win rate: {wr:.1%}")
print(f"    2-team parlay ROI: {((wr**2)*2.64 - (1-wr**2))*100:+.1f}%")
print(f"    3-team parlay ROI: {((wr**3)*6.0 - (1-wr**3))*100:+.1f}%")
print(f"    4-team parlay ROI: {((wr**4)*12.28 - (1-wr**4))*100:+.1f}%")

# High confidence only
high_conf = backtest[backtest['confidence'] >= 2.0].copy()
if len(high_conf) > 0:
    wins = (high_conf['result'] == 'WIN').sum()
    losses = (high_conf['result'] == 'LOSS').sum()
    wr = wins / (wins + losses) if (wins + losses) > 0 else 0

    print(f"\n  Strategy 3: High Confidence Only (2+ pt move)")
    print(f"    Games: {len(high_conf)}")
    print(f"    Win rate: {wr:.1%}")
    print(f"    2-team parlay ROI: {((wr**2)*2.64 - (1-wr**2))*100:+.1f}%")
    print(f"    3-team parlay ROI: {((wr**3)*6.0 - (1-wr**3))*100:+.1f}%")

# 6. Week-by-week performance
print("\n📅 PERFORMANCE BY WEEK (2024):")

backtest_2024 = backtest[backtest['season'] == 2024].copy()

for week in sorted(backtest_2024['week'].unique()):
    week_df = backtest_2024[backtest_2024['week'] == week]
    wins = (week_df['result'] == 'WIN').sum()
    losses = (week_df['result'] == 'LOSS').sum()
    wr = wins / (wins + losses) if (wins + losses) > 0 else 0
    
    status = "✅" if wr >= 0.52 else "❌"
    print(f"  Week {week:2d}: {len(week_df):2d} games, {wins:2d}-{losses:2d} ({wr:.1%}) {status}")

print("\n" + "=" * 70)
print("✅ ANALYSIS COMPLETE")
print("=" * 70)

