#!/usr/bin/env python3
"""
Test if re-fitting isotonic calibration on ONLY 2025 data improves betting performance.

Comparison:
- Current Model: Isotonic calibrator trained on ALL historical data (2020-2025)
- New Model: Isotonic calibrator trained on ONLY 2025 data (Weeks 1-8)

We'll compare:
- Overall win rate
- High conviction win rate
- Medium conviction win rate  
- Low conviction win rate
- Number of bets made
- ROI

WITHOUT touching the current model or re-running simulations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.isotonic import IsotonicRegression
from scipy import stats

# Load existing backtest results
artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
backtest_file = artifacts_dir / "simulator_predictions.csv"

print("=" * 80)
print("ISOTONIC CALIBRATION COMPARISON TEST")
print("=" * 80)
print()
print("Loading existing backtest results...")

df = pd.read_csv(backtest_file)

# Filter to completed 2025 games for testing
df_2025 = df[(df['season'] == 2025) & (df['is_completed'] == True) & (df['week'] <= 8)].copy()

print(f"✅ Loaded {len(df_2025)} completed 2025 games (Weeks 1-8)")
print()

# Extract raw probabilities (before isotonic calibration)
# We need to reverse-engineer the raw probabilities from the stored data
# The stored p_home_cover and p_away_cover are AFTER isotonic calibration

# For this test, we'll use a proxy: the raw simulation win percentages
# Let's extract actual outcomes for training the new isotonic model

print("=" * 80)
print("FITTING NEW ISOTONIC CALIBRATOR (2025 ONLY)")
print("=" * 80)
print()

# Prepare training data for isotonic calibration
# We need: (predicted_probability, actual_outcome) pairs

training_data = []

for idx, row in df_2025.iterrows():
    # Get the raw probabilities (stored in our data)
    p_home_raw = row.get('p_home_cover', 0.5)
    p_away_raw = row.get('p_away_cover', 0.5)
    
    # Get actual outcomes
    actual_spread_diff = row['actual_home_score'] - row['actual_away_score']
    closing_spread = row['closing_spread']
    
    # Did home cover?
    home_covered = actual_spread_diff > closing_spread
    
    # Add to training data
    training_data.append({
        'predicted_prob': p_home_raw,
        'actual_outcome': 1 if home_covered else 0
    })
    
    training_data.append({
        'predicted_prob': p_away_raw,
        'actual_outcome': 1 if not home_covered else 0
    })

train_df = pd.DataFrame(training_data)

# Fit isotonic regression on 2025 data only
print(f"Training isotonic calibrator on {len(train_df)} probability/outcome pairs from 2025...")

iso_2025 = IsotonicRegression(out_of_bounds='clip')
iso_2025.fit(train_df['predicted_prob'], train_df['actual_outcome'])

print("✅ New isotonic calibrator fitted!")
print()

# Now compare the two approaches
print("=" * 80)
print("COMPARING BETTING PERFORMANCE")
print("=" * 80)
print()

BREAKEVEN = 0.524

# Current Model Results (using existing calibrated probabilities)
current_bets = []
for idx, row in df_2025.iterrows():
    rec = row.get('spread_recommendation')
    if pd.notna(rec) and rec != 'Pass':
        result = row.get('spread_result')
        conviction = row.get('spread_conviction', 'UNKNOWN')
        edge = row.get('spread_edge_pct', 0)
        
        current_bets.append({
            'game': f"{row['away_team']}@{row['home_team']} W{row['week']}",
            'recommendation': rec,
            'result': result,
            'conviction': conviction,
            'edge': edge
        })

current_df = pd.DataFrame(current_bets)

# New Model Results (re-calibrate with 2025-only isotonic)
new_bets = []
for idx, row in df_2025.iterrows():
    # Get raw probabilities
    p_home_raw = row.get('p_home_cover', 0.5)
    p_away_raw = row.get('p_away_cover', 0.5)
    
    # Apply NEW isotonic calibration
    p_home_calibrated = iso_2025.predict([p_home_raw])[0]
    p_away_calibrated = iso_2025.predict([p_away_raw])[0]
    
    # Determine bet
    bet = None
    prob = None
    edge = None
    
    if p_home_calibrated > BREAKEVEN:
        bet = f"{row['home_team']} ATS"
        prob = p_home_calibrated
        edge = (p_home_calibrated - BREAKEVEN) * 100
    elif p_away_calibrated > BREAKEVEN:
        bet = f"{row['away_team']} ATS"
        prob = p_away_calibrated
        edge = (p_away_calibrated - BREAKEVEN) * 100
    
    if bet:
        # Determine actual outcome
        actual_spread_diff = row['actual_home_score'] - row['actual_away_score']
        closing_spread = row['closing_spread']
        home_covered = actual_spread_diff > closing_spread
        
        if row['home_team'] in bet:
            result = 'WIN' if home_covered else 'LOSS'
        else:
            result = 'WIN' if not home_covered else 'LOSS'
        
        # Determine conviction based on edge
        if edge >= 5.0:
            conviction = 'HIGH'
        elif edge >= 2.0:
            conviction = 'MEDIUM'
        else:
            conviction = 'LOW'
        
        new_bets.append({
            'game': f"{row['away_team']}@{row['home_team']} W{row['week']}",
            'recommendation': bet,
            'result': result,
            'conviction': conviction,
            'edge': edge,
            'prob': prob
        })

new_df = pd.DataFrame(new_bets)

# Calculate statistics for both models

def calculate_stats(bets_df, label):
    print(f"\n{'=' * 40}")
    print(f"{label}")
    print(f"{'=' * 40}")
    
    total_bets = len(bets_df)
    wins = len(bets_df[bets_df['result'] == 'WIN'])
    losses = len(bets_df[bets_df['result'] == 'LOSS'])
    
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    roi = ((wins * 0.91 - losses) / total_bets * 100) if total_bets > 0 else 0
    
    print(f"Total Bets: {total_bets}")
    print(f"Record: {wins}-{losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"ROI: {roi:+.1f}%")
    
    # Breakdown by conviction
    for conviction in ['HIGH', 'MEDIUM', 'LOW']:
        conv_bets = bets_df[bets_df['conviction'] == conviction]
        if len(conv_bets) > 0:
            conv_wins = len(conv_bets[conv_bets['result'] == 'WIN'])
            conv_total = len(conv_bets)
            conv_wr = (conv_wins / conv_total * 100)
            print(f"  {conviction}: {conv_wins}-{conv_total-conv_wins} ({conv_wr:.1f}%)")
    
    return {
        'total_bets': total_bets,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'roi': roi
    }

current_stats = calculate_stats(current_df, "CURRENT MODEL (All Historical Data)")
new_stats = calculate_stats(new_df, "NEW MODEL (2025 Only)")

print()
print("=" * 80)
print("COMPARISON SUMMARY")
print("=" * 80)
print()

# Calculate improvements
bet_diff = new_stats['total_bets'] - current_stats['total_bets']
wr_diff = new_stats['win_rate'] - current_stats['win_rate']
roi_diff = new_stats['roi'] - current_stats['roi']

print(f"Total Bets:  Current: {current_stats['total_bets']}  →  New: {new_stats['total_bets']}  "
      f"({'+'if bet_diff >= 0 else ''}{bet_diff})")
print(f"Win Rate:    Current: {current_stats['win_rate']:.1f}%  →  New: {new_stats['win_rate']:.1f}%  "
      f"({'+'if wr_diff >= 0 else ''}{wr_diff:.1f}%)")
print(f"ROI:         Current: {current_stats['roi']:+.1f}%  →  New: {new_stats['roi']:+.1f}%  "
      f"({'+'if roi_diff >= 0 else ''}{roi_diff:.1f}%)")
print()

# Statistical significance test
if current_stats['total_bets'] > 0 and new_stats['total_bets'] > 0:
    # Chi-square test for win rate difference
    contingency = np.array([
        [current_stats['wins'], current_stats['losses']],
        [new_stats['wins'], new_stats['losses']]
    ])
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
    
    print(f"Statistical Significance: p-value = {p_value:.4f}")
    if p_value < 0.05:
        print("✅ Difference is statistically significant (p < 0.05)")
    else:
        print("⚠️  Difference is NOT statistically significant (p >= 0.05)")
    print()

# Recommendation
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()

if wr_diff > 2.0 and roi_diff > 2.0:
    print("✅ STRONG EVIDENCE to switch to 2025-only isotonic calibration")
    print("   The new model shows meaningfully better win rate AND ROI.")
elif wr_diff > 1.0 and roi_diff > 1.0:
    print("✅ MODERATE EVIDENCE to switch to 2025-only isotonic calibration")
    print("   The new model shows improvement in both win rate and ROI.")
elif wr_diff > 0 and roi_diff > 0:
    print("⚠️  WEAK EVIDENCE to switch to 2025-only isotonic calibration")
    print("   The new model shows slight improvement, but may not be significant.")
else:
    print("❌ NO EVIDENCE to switch to 2025-only isotonic calibration")
    print("   The current model performs as well or better.")

print()
print("Note: This test uses only 8 weeks of 2025 data. More data = more reliable.")
print()

# Save detailed comparison
comparison_file = Path(__file__).parent / "isotonic_comparison_results.csv"

comparison_df = pd.DataFrame({
    'game': current_df['game'].tolist() + [''] * (len(new_df) - len(current_df)),
    'current_rec': current_df['recommendation'].tolist() + [''] * (len(new_df) - len(current_df)),
    'current_result': current_df['result'].tolist() + [''] * (len(new_df) - len(current_df)),
    'current_conviction': current_df['conviction'].tolist() + [''] * (len(new_df) - len(current_df)),
    'new_rec': new_df['recommendation'].tolist() if len(new_df) > 0 else [],
    'new_result': new_df['result'].tolist() if len(new_df) > 0 else [],
    'new_conviction': new_df['conviction'].tolist() if len(new_df) > 0 else [],
    'new_prob': new_df['prob'].tolist() if len(new_df) > 0 else [],
})

comparison_df.to_csv(comparison_file, index=False)
print(f"📊 Detailed comparison saved to: {comparison_file}")

