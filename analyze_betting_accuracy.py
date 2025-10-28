#!/usr/bin/env python3
"""
Analyze what makes betting accuracy good vs bad
"""
import pandas as pd

# Load detailed results
graded = pd.read_csv("artifacts/historical_grading_weeks_1-7.csv")

print("="*80)
print("BETTING ACCURACY ANALYSIS: What Makes Good Bets?")
print("="*80)

# Separate winning and losing bets
winning_bets = graded[graded['spread_bet_correct'] == True].copy()
losing_bets = graded[graded['spread_bet_correct'] == False].copy()

print("\n📊 Overall Betting Record:")
print(f"   Winning bets: {len(winning_bets)} ({len(winning_bets)/len(graded)*100:.1f}%)")
print(f"   Losing bets: {len(losing_bets)} ({len(losing_bets)/len(graded)*100:.1f}%)")

# Analyze characteristics of winning vs losing bets
print(f"\n{'='*80}")
print("WINNING BETS vs LOSING BETS: Key Differences")
print(f"{'='*80}")

print("\n📈 Spread Error:")
print(f"   Winning bets avg error: {winning_bets['spread_error'].mean():.2f} points")
print(f"   Losing bets avg error: {losing_bets['spread_error'].mean():.2f} points")
print(f"   Difference: {losing_bets['spread_error'].mean() - winning_bets['spread_error'].mean():.2f} points")

print("\n🎯 Model Confidence (predicted margin):")
winning_bets['pred_margin'] = winning_bets.apply(
    lambda r: abs(float(r['pred_score'].split('-')[0]) - float(r['pred_score'].split('-')[1])), axis=1
)
losing_bets['pred_margin'] = losing_bets.apply(
    lambda r: abs(float(r['pred_score'].split('-')[0]) - float(r['pred_score'].split('-')[1])), axis=1
)

print(f"   Winning bets avg predicted margin: {winning_bets['pred_margin'].mean():.2f} points")
print(f"   Losing bets avg predicted margin: {losing_bets['pred_margin'].mean():.2f} points")

print("\n🏆 Winner Prediction:")
print(f"   Winning bets - got winner right: {winning_bets['winner_correct'].sum()}/{len(winning_bets)} ({winning_bets['winner_correct'].mean()*100:.1f}%)")
print(f"   Losing bets - got winner right: {losing_bets['winner_correct'].sum()}/{len(losing_bets)} ({losing_bets['winner_correct'].mean()*100:.1f}%)")

# Analyze by predicted margin buckets
print(f"\n{'='*80}")
print("BETTING ACCURACY BY PREDICTED MARGIN")
print(f"{'='*80}")

graded['pred_margin'] = graded.apply(
    lambda r: abs(float(r['pred_score'].split('-')[0]) - float(r['pred_score'].split('-')[1])) if '-' in str(r['pred_score']) else 0, axis=1
)

margin_buckets = [
    (0, 3, "Very Close (0-3 pts)"),
    (3, 7, "Close (3-7 pts)"),
    (7, 10, "Moderate (7-10 pts)"),
    (10, 14, "Large (10-14 pts)"),
    (14, 100, "Blowout (14+ pts)")
]

print("\n📊 Bet Accuracy by Predicted Margin:")
for min_m, max_m, label in margin_buckets:
    bucket = graded[(graded['pred_margin'] >= min_m) & (graded['pred_margin'] < max_m)]
    if len(bucket) > 0:
        bet_acc = bucket['spread_bet_correct'].mean() * 100
        print(f"   {label:25s}: {bet_acc:5.1f}% ({len(bucket):3d} bets)")

# Analyze by actual margin (game closeness)
print(f"\n{'='*80}")
print("BETTING ACCURACY BY ACTUAL GAME CLOSENESS")
print(f"{'='*80}")

graded['actual_margin_abs'] = graded['actual_margin'].abs()

print("\n📊 Bet Accuracy by Actual Margin:")
for min_m, max_m, label in margin_buckets:
    bucket = graded[(graded['actual_margin_abs'] >= min_m) & (graded['actual_margin_abs'] < max_m)]
    if len(bucket) > 0:
        bet_acc = bucket['spread_bet_correct'].mean() * 100
        print(f"   {label:25s}: {bet_acc:5.1f}% ({len(bucket):3d} games)")

# Analyze spread error threshold
print(f"\n{'='*80}")
print("BETTING ACCURACY BY MODEL ACCURACY")
print(f"{'='*80}")

error_buckets = [
    (0, 5, "Very Accurate (<5 pts error)"),
    (5, 10, "Accurate (5-10 pts error)"),
    (10, 15, "Moderate (10-15 pts error)"),
    (15, 100, "Inaccurate (15+ pts error)")
]

print("\n📊 Bet Accuracy by Spread Error:")
for min_e, max_e, label in error_buckets:
    bucket = graded[(graded['spread_error'] >= min_e) & (graded['spread_error'] < max_e)]
    if len(bucket) > 0:
        bet_acc = bucket['spread_bet_correct'].mean() * 100
        print(f"   {label:30s}: {bet_acc:5.1f}% ({len(bucket):3d} bets)")

# Find optimal betting strategy
print(f"\n{'='*80}")
print("OPTIMAL BETTING STRATEGY")
print(f"{'='*80}")

print("\n🎯 Strategy 1: Only bet on close games (predicted margin < 7 pts)")
close_games = graded[graded['pred_margin'] < 7]
close_bet_acc = close_games['spread_bet_correct'].mean() * 100
print(f"   Bet accuracy: {close_bet_acc:.1f}% ({len(close_games)} bets)")
print(f"   Result: {'✅ PROFITABLE' if close_bet_acc >= 52.4 else '🔴 UNPROFITABLE'}")

print("\n🎯 Strategy 2: Only bet on moderate confidence (7-14 pts margin)")
moderate_games = graded[(graded['pred_margin'] >= 7) & (graded['pred_margin'] < 14)]
moderate_bet_acc = moderate_games['spread_bet_correct'].mean() * 100
print(f"   Bet accuracy: {moderate_bet_acc:.1f}% ({len(moderate_games)} bets)")
print(f"   Result: {'✅ PROFITABLE' if moderate_bet_acc >= 52.4 else '🔴 UNPROFITABLE'}")

print("\n🎯 Strategy 3: Avoid blowouts (predicted margin > 14 pts)")
no_blowouts = graded[graded['pred_margin'] <= 14]
no_blowout_acc = no_blowouts['spread_bet_correct'].mean() * 100
print(f"   Bet accuracy: {no_blowout_acc:.1f}% ({len(no_blowouts)} bets)")
print(f"   Result: {'✅ PROFITABLE' if no_blowout_acc >= 52.4 else '🔴 UNPROFITABLE'}")

print("\n🎯 Strategy 4: Only bet when model is confident (spread error < 10 pts historically)")
# This would require knowing error in advance, so use predicted margin as proxy
confident_games = graded[(graded['pred_margin'] >= 5) & (graded['pred_margin'] <= 12)]
confident_acc = confident_games['spread_bet_correct'].mean() * 100
print(f"   Bet accuracy: {confident_acc:.1f}% ({len(confident_games)} bets)")
print(f"   Result: {'✅ PROFITABLE' if confident_acc >= 52.4 else '🔴 UNPROFITABLE'}")

print("\n🎯 Strategy 5: Bet on good weeks only (skip weeks 4-5)")
good_weeks = graded[~graded['week'].isin([4, 5])]
good_week_acc = good_weeks['spread_bet_correct'].mean() * 100
print(f"   Bet accuracy: {good_week_acc:.1f}% ({len(good_weeks)} bets)")
print(f"   Result: {'✅ PROFITABLE' if good_week_acc >= 52.4 else '🔴 UNPROFITABLE'}")

# Analyze what made Week 1 and 3 so good
print(f"\n{'='*80}")
print("WHAT MADE WEEK 1 & 3 SO GOOD? (68.8% bet accuracy)")
print(f"{'='*80}")

week1_3 = graded[graded['week'].isin([1, 3])]
other_weeks = graded[~graded['week'].isin([1, 3])]

print("\nWeek 1 & 3 characteristics:")
print(f"   Avg predicted margin: {week1_3['pred_margin'].mean():.2f} pts")
print(f"   Avg spread error: {week1_3['spread_error'].mean():.2f} pts")
print(f"   Winner accuracy: {week1_3['winner_correct'].mean()*100:.1f}%")

print("\nOther weeks characteristics:")
print(f"   Avg predicted margin: {other_weeks['pred_margin'].mean():.2f} pts")
print(f"   Avg spread error: {other_weeks['spread_error'].mean():.2f} pts")
print(f"   Winner accuracy: {other_weeks['winner_correct'].mean()*100:.1f}%")

# Recommendations
print(f"\n{'='*80}")
print("🎯 RECOMMENDATIONS TO IMPROVE BETTING ACCURACY")
print(f"{'='*80}")

print(f"""
1. **Bet Selectively - Don't Bet Every Game**
   Current: Betting on all 108 games (51.9% accuracy)
   Better: Bet on 50-60 best opportunities (could hit 55%+)

2. **Avoid Predicted Blowouts (>14 pts)**
   - Blowouts are unpredictable
   - Model is good at picking winner, bad at margin
   - Skip these games entirely

3. **Focus on 5-12 Point Predicted Margins**
   - These have best bet accuracy: {confident_acc:.1f}%
   - Model has enough edge but not overconfident
   - Sweet spot for value betting

4. **Increase Minimum EV Threshold**
   Current: min_ev = 0.02 (2%)
   Better: min_ev = 0.05 (5%) - be more selective
   
5. **Add Confidence Score**
   - Track model's historical accuracy by game type
   - Only bet when confidence score > 60%
   - Use spread error history as confidence metric

6. **Skip Early Season Weeks**
   - Weeks 1-2 have less data, more variance
   - Consider starting bets from Week 3+
   - Or reduce bet size in early weeks

7. **Implement Kelly Criterion Properly**
   - Current: Fixed 25% Kelly
   - Better: Scale by confidence (10-25% Kelly)
   - Reduce size on uncertain bets

8. **Track Vegas Line Movement**
   - If line moves toward your prediction, skip it
   - If line moves away, bet is stronger
   - Market is telling you something

9. **Add Game Context Features**
   - Primetime games (different dynamics)
   - Weather games (lower scoring)
   - Rivalry games (more unpredictable)
   - Playoff implications (higher motivation)

10. **Use Ensemble Approach**
    - Don't rely on single model prediction
    - Compare to Vegas consensus
    - Only bet when model disagrees by 3+ points
""")

print(f"\n{'='*80}")
print("💡 QUICK WIN: Implement Strategy 3 + 4")
print(f"{'='*80}")

optimal = graded[(graded['pred_margin'] >= 5) & (graded['pred_margin'] <= 14)]
optimal_acc = optimal['spread_bet_correct'].mean() * 100
print("\nBet only on games with 5-14 point predicted margin:")
print(f"   Bet accuracy: {optimal_acc:.1f}% ({len(optimal)}/{len(graded)} games)")
print(f"   Result: {'✅ PROFITABLE!' if optimal_acc >= 52.4 else '🔴 Still need work'}")
print(f"   Improvement: {optimal_acc - 51.9:+.1f}% vs betting all games")

if optimal_acc >= 52.4:
    profit_per_100 = (optimal_acc - 52.4) * 100 * 0.1
    print(f"   💰 Estimated profit per $100 wagered: ${profit_per_100:.2f}")

print(f"\n{'='*80}")

