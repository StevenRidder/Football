#!/usr/bin/env python3
"""
Week-over-week improvement analysis
"""
import pandas as pd

# Load the summary data
summary = pd.read_csv("artifacts/historical_summary_weeks_1-7.csv")

print("="*80)
print("WEEK-OVER-WEEK IMPROVEMENT ANALYSIS")
print("="*80)

# Calculate week-over-week changes
summary['winner_acc_change'] = summary['winner_accuracy'].diff()
summary['spread_err_change'] = summary['avg_spread_error'].diff()
summary['bet_acc_change'] = summary['spread_bet_accuracy'].diff()

print("\n📈 RAW DATA:")
print(summary[['week', 'winner_accuracy', 'avg_spread_error', 'spread_bet_accuracy']].to_string(index=False))

print("\n" + "="*80)
print("WEEK-OVER-WEEK CHANGES")
print("="*80)

for i, row in summary.iterrows():
    if i == 0:
        continue  # Skip first week (no previous week to compare)
    
    week = int(row['week'])
    winner_change = row['winner_acc_change']
    spread_change = row['spread_err_change']
    bet_change = row['bet_acc_change']
    
    print(f"\n📊 Week {week-1} → Week {week}:")
    
    # Winner accuracy
    if winner_change > 0:
        print(f"   Winner Accuracy: {summary.iloc[i-1]['winner_accuracy']:.1f}% → {row['winner_accuracy']:.1f}% ({winner_change:+.1f}%) ✅")
    else:
        print(f"   Winner Accuracy: {summary.iloc[i-1]['winner_accuracy']:.1f}% → {row['winner_accuracy']:.1f}% ({winner_change:+.1f}%) 🔴")
    
    # Spread error (lower is better)
    if spread_change < 0:
        print(f"   Spread Error: {summary.iloc[i-1]['avg_spread_error']:.2f} → {row['avg_spread_error']:.2f} ({spread_change:+.2f}) ✅")
    else:
        print(f"   Spread Error: {summary.iloc[i-1]['avg_spread_error']:.2f} → {row['avg_spread_error']:.2f} ({spread_change:+.2f}) 🔴")
    
    # Bet accuracy
    if bet_change > 0:
        print(f"   Bet Accuracy: {summary.iloc[i-1]['spread_bet_accuracy']:.1f}% → {row['spread_bet_accuracy']:.1f}% ({bet_change:+.1f}%) ✅")
    else:
        print(f"   Bet Accuracy: {summary.iloc[i-1]['spread_bet_accuracy']:.1f}% → {row['spread_bet_accuracy']:.1f}% ({bet_change:+.1f}%) 🔴")

print("\n" + "="*80)
print("TREND ANALYSIS")
print("="*80)

# Calculate trends
weeks = summary['week'].values
winner_acc = summary['winner_accuracy'].values
spread_err = summary['avg_spread_error'].values
bet_acc = summary['spread_bet_accuracy'].values

# Linear regression for trends
from numpy.polynomial import Polynomial

# Winner accuracy trend
p_winner = Polynomial.fit(weeks, winner_acc, 1)
winner_slope = p_winner.convert().coef[1]

# Spread error trend
p_spread = Polynomial.fit(weeks, spread_err, 1)
spread_slope = p_spread.convert().coef[1]

# Bet accuracy trend
p_bet = Polynomial.fit(weeks, bet_acc, 1)
bet_slope = p_bet.convert().coef[1]

print("\n📈 Linear Trends (per week):")
print(f"   Winner Accuracy: {winner_slope:+.2f}% per week {'✅ IMPROVING' if winner_slope > 0 else '🔴 DECLINING'}")
print(f"   Spread Error: {spread_slope:+.2f} pts per week {'✅ IMPROVING' if spread_slope < 0 else '🔴 DECLINING'}")
print(f"   Bet Accuracy: {bet_slope:+.2f}% per week {'✅ IMPROVING' if bet_slope > 0 else '🔴 DECLINING'}")

# Projected Week 8 performance
week_8_winner = p_winner(8)
week_8_spread = p_spread(8)
week_8_bet = p_bet(8)

print("\n🔮 Projected Week 8 Performance (based on trend):")
print(f"   Winner Accuracy: {week_8_winner:.1f}%")
print(f"   Spread Error: {week_8_spread:.2f} points")
print(f"   Bet Accuracy: {week_8_bet:.1f}%")

if week_8_bet >= 52.4:
    print(f"   💰 PROJECTED PROFITABLE! ({week_8_bet:.1f}% > 52.4% break-even)")
else:
    print(f"   ⚠️  Still below break-even ({week_8_bet:.1f}% < 52.4%)")

# Best and worst weeks
print("\n" + "="*80)
print("BEST & WORST WEEKS")
print("="*80)

best_winner_week = summary.loc[summary['winner_accuracy'].idxmax()]
worst_winner_week = summary.loc[summary['winner_accuracy'].idxmin()]

best_bet_week = summary.loc[summary['spread_bet_accuracy'].idxmax()]
worst_bet_week = summary.loc[summary['spread_bet_accuracy'].idxmin()]

best_spread_week = summary.loc[summary['avg_spread_error'].idxmin()]
worst_spread_week = summary.loc[summary['avg_spread_error'].idxmax()]

print(f"\n🏆 Best Winner Accuracy: Week {int(best_winner_week['week'])} ({best_winner_week['winner_accuracy']:.1f}%)")
print(f"😞 Worst Winner Accuracy: Week {int(worst_winner_week['week'])} ({worst_winner_week['winner_accuracy']:.1f}%)")

print(f"\n🏆 Best Bet Accuracy: Week {int(best_bet_week['week'])} ({best_bet_week['spread_bet_accuracy']:.1f}%)")
print(f"😞 Worst Bet Accuracy: Week {int(worst_bet_week['week'])} ({worst_bet_week['spread_bet_accuracy']:.1f}%)")

print(f"\n🏆 Best Spread Error: Week {int(best_spread_week['week'])} ({best_spread_week['avg_spread_error']:.2f} pts)")
print(f"😞 Worst Spread Error: Week {int(worst_spread_week['week'])} ({worst_spread_week['avg_spread_error']:.2f} pts)")

# Overall improvement
print("\n" + "="*80)
print("OVERALL IMPROVEMENT (Week 1 → Week 7)")
print("="*80)

week1 = summary.iloc[0]
week7 = summary.iloc[-1]

winner_improvement = week7['winner_accuracy'] - week1['winner_accuracy']
spread_improvement = week7['avg_spread_error'] - week1['avg_spread_error']
bet_improvement = week7['spread_bet_accuracy'] - week1['spread_bet_accuracy']

print("\n📊 Total Change:")
print(f"   Winner Accuracy: {week1['winner_accuracy']:.1f}% → {week7['winner_accuracy']:.1f}% ({winner_improvement:+.1f}%)")
print(f"   Spread Error: {week1['avg_spread_error']:.2f} → {week7['avg_spread_error']:.2f} ({spread_improvement:+.2f} pts)")
print(f"   Bet Accuracy: {week1['spread_bet_accuracy']:.1f}% → {week7['spread_bet_accuracy']:.1f}% ({bet_improvement:+.1f}%)")

print("\n💡 Key Insights:")
if winner_improvement > 0:
    print(f"   ✅ Winner accuracy improved by {winner_improvement:.1f}% over 7 weeks")
else:
    print(f"   🔴 Winner accuracy declined by {abs(winner_improvement):.1f}% over 7 weeks")

if spread_improvement < 0:
    print(f"   ✅ Spread error improved by {abs(spread_improvement):.2f} points over 7 weeks")
else:
    print(f"   🔴 Spread error worsened by {spread_improvement:.2f} points over 7 weeks")

if bet_improvement > 0:
    print(f"   ✅ Bet accuracy improved by {bet_improvement:.1f}% over 7 weeks")
else:
    print(f"   🔴 Bet accuracy declined by {abs(bet_improvement):.1f}% over 7 weeks")

# Volatility analysis
print("\n" + "="*80)
print("CONSISTENCY ANALYSIS")
print("="*80)

winner_std = summary['winner_accuracy'].std()
spread_std = summary['avg_spread_error'].std()
bet_std = summary['spread_bet_accuracy'].std()

print("\n📊 Week-to-Week Volatility (Standard Deviation):")
print(f"   Winner Accuracy: ±{winner_std:.1f}%")
print(f"   Spread Error: ±{spread_std:.2f} points")
print(f"   Bet Accuracy: ±{bet_std:.1f}%")

if bet_std > 15:
    print(f"\n⚠️  High bet accuracy volatility (±{bet_std:.1f}%) - model is inconsistent")
elif bet_std > 10:
    print(f"\n⚠️  Moderate bet accuracy volatility (±{bet_std:.1f}%) - some inconsistency")
else:
    print(f"\n✅ Low bet accuracy volatility (±{bet_std:.1f}%) - model is consistent")

print(f"\n{'='*80}")

