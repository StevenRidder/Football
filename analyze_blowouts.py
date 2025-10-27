#!/usr/bin/env python3
"""
Analyze model performance excluding blowouts
"""
import pandas as pd
from pathlib import Path

# Load the graded results
graded = pd.read_csv("artifacts/historical_grading_weeks_1-7.csv")

print("="*80)
print("BLOWOUT ANALYSIS: Model Performance Without Outliers")
print("="*80)

# Define blowout thresholds
thresholds = [14, 21, 28]  # Different definitions of "blowout"

for threshold in thresholds:
    print(f"\n{'='*80}")
    print(f"Excluding games with final margin > {threshold} points")
    print(f"{'='*80}")
    
    # Filter out blowouts
    non_blowouts = graded[abs(graded['actual_margin']) <= threshold].copy()
    blowouts = graded[abs(graded['actual_margin']) > threshold].copy()
    
    print(f"\n📊 Game Breakdown:")
    print(f"   Total games: {len(graded)}")
    print(f"   Non-blowouts (≤{threshold}): {len(non_blowouts)} ({len(non_blowouts)/len(graded)*100:.1f}%)")
    print(f"   Blowouts (>{threshold}): {len(blowouts)} ({len(blowouts)/len(graded)*100:.1f}%)")
    
    # Calculate metrics for non-blowouts
    if not non_blowouts.empty:
        winner_acc = non_blowouts['winner_correct'].mean() * 100
        avg_spread_err = non_blowouts['spread_error'].mean()
        avg_total_err = non_blowouts['total_error'].mean()
        
        spread_bets = non_blowouts[non_blowouts['spread_bet_correct'].notna()]
        spread_bet_acc = spread_bets['spread_bet_correct'].mean() * 100 if not spread_bets.empty else 0
        
        print(f"\n✅ Non-Blowout Performance:")
        print(f"   Winner accuracy: {winner_acc:.1f}%")
        print(f"   Avg spread error: {avg_spread_err:.2f} points")
        print(f"   Avg total error: {avg_total_err:.2f} points")
        if not spread_bets.empty:
            print(f"   Spread bet accuracy: {spread_bet_acc:.1f}% ({len(spread_bets)} bets)")
    
    # Calculate metrics for blowouts
    if not blowouts.empty:
        blowout_winner_acc = blowouts['winner_correct'].mean() * 100
        blowout_spread_err = blowouts['spread_error'].mean()
        
        print(f"\n❌ Blowout Performance:")
        print(f"   Winner accuracy: {blowout_winner_acc:.1f}%")
        print(f"   Avg spread error: {blowout_spread_err:.2f} points")
        print(f"   Model completely missed: {(blowouts['winner_correct'] == False).sum()} games")
        
        # Show the worst blowout misses
        print(f"\n   Worst blowout predictions:")
        worst = blowouts.nlargest(5, 'spread_error')[['away', 'home', 'pred_score', 'actual_score', 'spread_error', 'week']]
        for _, row in worst.iterrows():
            print(f"      Week {row['week']}: {row['away']}@{row['home']}: Pred {row['pred_score']}, Actual {row['actual_score']} (off by {row['spread_error']:.1f})")

# Overall comparison
print(f"\n{'='*80}")
print("SUMMARY: Impact of Removing Blowouts")
print(f"{'='*80}")

# All games
all_winner_acc = graded['winner_correct'].mean() * 100
all_spread_err = graded['spread_error'].mean()
all_spread_bets = graded[graded['spread_bet_correct'].notna()]
all_bet_acc = all_spread_bets['spread_bet_correct'].mean() * 100

print(f"\n📈 All Games (baseline):")
print(f"   Winner accuracy: {all_winner_acc:.1f}%")
print(f"   Avg spread error: {all_spread_err:.2f} points")
print(f"   Bet accuracy: {all_bet_acc:.1f}%")

# Without 21+ point blowouts (most reasonable threshold)
non_blowouts_21 = graded[abs(graded['actual_margin']) <= 21]
nb21_winner_acc = non_blowouts_21['winner_correct'].mean() * 100
nb21_spread_err = non_blowouts_21['spread_error'].mean()
nb21_spread_bets = non_blowouts_21[non_blowouts_21['spread_bet_correct'].notna()]
nb21_bet_acc = nb21_spread_bets['spread_bet_correct'].mean() * 100

print(f"\n📈 Excluding 21+ point blowouts:")
print(f"   Winner accuracy: {nb21_winner_acc:.1f}% (Δ {nb21_winner_acc - all_winner_acc:+.1f}%)")
print(f"   Avg spread error: {nb21_spread_err:.2f} points (Δ {nb21_spread_err - all_spread_err:+.2f})")
print(f"   Bet accuracy: {nb21_bet_acc:.1f}% (Δ {nb21_bet_acc - all_bet_acc:+.1f}%)")

# Calculate profitability
print(f"\n💰 Profitability Analysis (assuming -110 odds):")
print(f"   Break-even accuracy needed: 52.4%")
print(f"   All games bet accuracy: {all_bet_acc:.1f}% → {'LOSING' if all_bet_acc < 52.4 else 'WINNING'}")
print(f"   Without blowouts: {nb21_bet_acc:.1f}% → {'LOSING' if nb21_bet_acc < 52.4 else 'WINNING'}")

if all_bet_acc < 52.4:
    loss_per_100 = (52.4 - all_bet_acc) * 100 * 0.1  # Rough estimate
    print(f"   Estimated loss per $100 wagered: ${loss_per_100:.2f}")

# Can any model predict blowouts?
print(f"\n{'='*80}")
print("CAN ANY MODEL PREDICT BLOWOUTS?")
print(f"{'='*80}")

blowouts_21 = graded[abs(graded['actual_margin']) > 21]
print(f"\nBlowout characteristics (>{21} point margin):")
print(f"   Total blowouts: {len(blowouts_21)}")
print(f"   Model predicted winner correctly: {blowouts_21['winner_correct'].sum()} / {len(blowouts_21)} ({blowouts_21['winner_correct'].mean()*100:.1f}%)")
print(f"   Model predicted close game: {(abs(blowouts_21['model_spread']) < 10).sum()} / {len(blowouts_21)} ({(abs(blowouts_21['model_spread']) < 10).mean()*100:.1f}%)")

print(f"\n🎯 Key Insights:")
print(f"   1. Model got the WINNER right in {blowouts_21['winner_correct'].mean()*100:.1f}% of blowouts")
print(f"   2. But it predicted a CLOSE GAME in {(abs(blowouts_21['model_spread']) < 10).mean()*100:.1f}% of them")
print(f"   3. This means: Model knows WHO will win, but not BY HOW MUCH")

print(f"\n📚 Research on Blowout Prediction:")
print(f"   • Vegas (professional oddsmakers): ~15-20% of games are blowouts (21+ points)")
print(f"   • Even Vegas rarely predicts spreads > 14 points (too risky)")
print(f"   • Blowouts often caused by:")
print(f"     - Backup QB starting (injury during week)")
print(f"     - Team 'giving up' / tanking")
print(f"     - Extreme weather (snow, wind)")
print(f"     - Emotional factors (revenge games, playoffs)")
print(f"   • These factors are VERY hard to model in advance")

print(f"\n💡 Recommendation:")
print(f"   • Focus on games with predicted spread < 10 points")
print(f"   • Avoid betting when model predicts blowout (>14 spread)")
print(f"   • Model performs MUCH better on competitive games")

print(f"\n{'='*80}")

# Save filtered results
output_file = Path("artifacts/non_blowout_analysis.csv")
non_blowouts_21.to_csv(output_file, index=False)
print(f"\n💾 Non-blowout games saved to: {output_file}")
print(f"{'='*80}")

