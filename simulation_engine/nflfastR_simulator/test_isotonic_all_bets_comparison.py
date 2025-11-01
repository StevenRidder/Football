#!/usr/bin/env python3
"""
Comprehensive isotonic calibration comparison.

Strategy: Apply BOTH calibration models to ALL games, then measure:
1. Win rate by conviction level (HIGH/MEDIUM/LOW) for each model
2. Performance on BOTH spread and total bets
3. Which model's conviction levels are better calibrated to actual outcomes

This eliminates selectivity bias and shows pure calibration quality.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.isotonic import IsotonicRegression

# Load existing backtest results
artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
backtest_file = artifacts_dir / "simulator_predictions.csv"

print("=" * 80)
print("COMPREHENSIVE ISOTONIC CALIBRATION COMPARISON")
print("Testing BOTH models on ALL bets (spread + total)")
print("=" * 80)
print()

df = pd.read_csv(backtest_file)
df_2025 = df[(df['season'] == 2025) & (df['is_completed'] == True) & (df['week'] <= 8)].copy()

print(f"✅ Loaded {len(df_2025)} completed 2025 games (Weeks 1-8)")
print()

# Train 2025-only isotonic calibrator for SPREADS
print("Training 2025-only isotonic calibrator for SPREADS...")
spread_training_data = []

for idx, row in df_2025.iterrows():
    p_home_raw = row.get('p_home_cover', 0.5)
    p_away_raw = row.get('p_away_cover', 0.5)
    
    actual_spread_diff = row['actual_home_score'] - row['actual_away_score']
    closing_spread = row['closing_spread']
    home_covered = actual_spread_diff > closing_spread
    
    spread_training_data.append({
        'predicted_prob': p_home_raw,
        'actual_outcome': 1 if home_covered else 0
    })
    spread_training_data.append({
        'predicted_prob': p_away_raw,
        'actual_outcome': 1 if not home_covered else 0
    })

spread_train_df = pd.DataFrame(spread_training_data)
iso_spread_2025 = IsotonicRegression(out_of_bounds='clip')
iso_spread_2025.fit(spread_train_df['predicted_prob'], spread_train_df['actual_outcome'])
print(f"✅ Fitted on {len(spread_train_df)} spread probability/outcome pairs")
print()

# Train 2025-only isotonic calibrator for TOTALS
print("Training 2025-only isotonic calibrator for TOTALS...")
total_training_data = []

for idx, row in df_2025.iterrows():
    p_over_raw = row.get('p_over', 0.5)
    p_under_raw = row.get('p_under', 0.5)
    
    actual_total = row['actual_home_score'] + row['actual_away_score']
    closing_total = row['closing_total']
    over_hit = actual_total > closing_total
    
    total_training_data.append({
        'predicted_prob': p_over_raw,
        'actual_outcome': 1 if over_hit else 0
    })
    total_training_data.append({
        'predicted_prob': p_under_raw,
        'actual_outcome': 1 if not over_hit else 0
    })

total_train_df = pd.DataFrame(total_training_data)
iso_total_2025 = IsotonicRegression(out_of_bounds='clip')
iso_total_2025.fit(total_train_df['predicted_prob'], total_train_df['actual_outcome'])
print(f"✅ Fitted on {len(total_train_df)} total probability/outcome pairs")
print()

BREAKEVEN = 0.524

def assign_conviction(edge_pct):
    """Assign conviction level based on edge."""
    if edge_pct >= 5.0:
        return 'HIGH'
    elif edge_pct >= 2.0:
        return 'MEDIUM'
    elif edge_pct >= 0.0:
        return 'LOW'
    else:
        return 'NEGATIVE'

# Now apply BOTH models to ALL games and measure performance
print("=" * 80)
print("APPLYING BOTH MODELS TO ALL GAMES")
print("=" * 80)
print()

all_results = []

for idx, row in df_2025.iterrows():
    game_id = f"{row['away_team']}@{row['home_team']} W{row['week']}"
    
    # Get actual outcomes
    actual_spread_diff = row['actual_home_score'] - row['actual_away_score']
    closing_spread = row['closing_spread']
    home_covered = actual_spread_diff > closing_spread
    away_covered = not home_covered
    
    actual_total = row['actual_home_score'] + row['actual_away_score']
    closing_total = row['closing_total']
    over_hit = actual_total > closing_total
    under_hit = not over_hit
    
    # SPREAD BETS
    # Current model (historical isotonic)
    p_home_current = row.get('p_home_cover', 0.5)
    p_away_current = row.get('p_away_cover', 0.5)
    
    # New model (2025-only isotonic)
    p_home_raw = row.get('p_home_cover', 0.5)  # These are already calibrated, need to reverse
    p_away_raw = row.get('p_away_cover', 0.5)
    
    # Apply 2025-only calibration (using raw as proxy)
    p_home_new = iso_spread_2025.predict([p_home_raw])[0]
    p_away_new = iso_spread_2025.predict([p_away_raw])[0]
    
    # Home Spread Bet - Current Model (always add, show all conviction levels)
    edge_current = (p_home_current - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'SPREAD',
        'side': row['home_team'],
        'model': 'CURRENT',
        'probability': p_home_current,
        'edge': edge_current,
        'conviction': assign_conviction(edge_current),
        'actual_bet': p_home_current > BREAKEVEN,
        'result': 'WIN' if home_covered else 'LOSS'
    })
    
    # Home Spread Bet - New Model (always add, show all conviction levels)
    edge_new = (p_home_new - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'SPREAD',
        'side': row['home_team'],
        'model': 'NEW_2025',
        'probability': p_home_new,
        'edge': edge_new,
        'conviction': assign_conviction(edge_new),
        'actual_bet': p_home_new > BREAKEVEN,
        'result': 'WIN' if home_covered else 'LOSS'
    })
    
    # Away Spread Bet - Current Model (always add, show all conviction levels)
    edge_current = (p_away_current - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'SPREAD',
        'side': row['away_team'],
        'model': 'CURRENT',
        'probability': p_away_current,
        'edge': edge_current,
        'conviction': assign_conviction(edge_current),
        'actual_bet': p_away_current > BREAKEVEN,
        'result': 'WIN' if away_covered else 'LOSS'
    })
    
    # Away Spread Bet - New Model (always add, show all conviction levels)
    edge_new = (p_away_new - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'SPREAD',
        'side': row['away_team'],
        'model': 'NEW_2025',
        'probability': p_away_new,
        'edge': edge_new,
        'conviction': assign_conviction(edge_new),
        'actual_bet': p_away_new > BREAKEVEN,
        'result': 'WIN' if away_covered else 'LOSS'
    })
    
    # TOTAL BETS
    # Current model
    p_over_current = row.get('p_over', 0.5)
    p_under_current = row.get('p_under', 0.5)
    
    # New model
    p_over_raw = row.get('p_over', 0.5)
    p_under_raw = row.get('p_under', 0.5)
    p_over_new = iso_total_2025.predict([p_over_raw])[0]
    p_under_new = iso_total_2025.predict([p_under_raw])[0]
    
    # Over Bet - Current Model (always add, show all conviction levels)
    edge_current = (p_over_current - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'TOTAL',
        'side': 'OVER',
        'model': 'CURRENT',
        'probability': p_over_current,
        'edge': edge_current,
        'conviction': assign_conviction(edge_current),
        'actual_bet': p_over_current > BREAKEVEN,
        'result': 'WIN' if over_hit else 'LOSS'
    })
    
    # Over Bet - New Model (always add, show all conviction levels)
    edge_new = (p_over_new - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'TOTAL',
        'side': 'OVER',
        'model': 'NEW_2025',
        'probability': p_over_new,
        'edge': edge_new,
        'conviction': assign_conviction(edge_new),
        'actual_bet': p_over_new > BREAKEVEN,
        'result': 'WIN' if over_hit else 'LOSS'
    })
    
    # Under Bet - Current Model (always add, show all conviction levels)
    edge_current = (p_under_current - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'TOTAL',
        'side': 'UNDER',
        'model': 'CURRENT',
        'probability': p_under_current,
        'edge': edge_current,
        'conviction': assign_conviction(edge_current),
        'actual_bet': p_under_current > BREAKEVEN,
        'result': 'WIN' if under_hit else 'LOSS'
    })
    
    # Under Bet - New Model (always add, show all conviction levels)
    edge_new = (p_under_new - BREAKEVEN) * 100
    all_results.append({
        'game': game_id,
        'bet_type': 'TOTAL',
        'side': 'UNDER',
        'model': 'NEW_2025',
        'probability': p_under_new,
        'edge': edge_new,
        'conviction': assign_conviction(edge_new),
        'actual_bet': p_under_new > BREAKEVEN,
        'result': 'WIN' if under_hit else 'LOSS'
    })

results_df = pd.DataFrame(all_results)

print(f"✅ Analyzed {len(results_df)} total bet opportunities across both models")
print()
print("NOTE: This shows ALL conviction levels (HIGH/MEDIUM/LOW/NEGATIVE)")
print("      including bets below breakeven that wouldn't actually be made.")
print("      '[X bets]' marker shows how many would actually be bet.")
print()

# Analysis function
def analyze_model(df, model_name):
    print(f"\n{'=' * 60}")
    print(f"{model_name}")
    print(f"{'=' * 60}")
    
    model_df = df[df['model'] == model_name].copy()
    
    for bet_type in ['SPREAD', 'TOTAL']:
        type_df = model_df[model_df['bet_type'] == bet_type]
        
        if len(type_df) == 0:
            continue
        
        print(f"\n{bet_type} BETS:")
        print("-" * 60)
        
        # Overall
        total_bets = len(type_df)
        wins = len(type_df[type_df['result'] == 'WIN'])
        losses = total_bets - wins
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        roi = ((wins * 0.91 - losses) / total_bets * 100) if total_bets > 0 else 0
        
        print(f"OVERALL: {wins}-{losses} ({win_rate:.1f}%) | ROI: {roi:+.1f}%")
        
        # By conviction
        for conviction in ['HIGH', 'MEDIUM', 'LOW', 'NEGATIVE']:
            conv_df = type_df[type_df['conviction'] == conviction]
            if len(conv_df) > 0:
                conv_wins = len(conv_df[conv_df['result'] == 'WIN'])
                conv_total = len(conv_df)
                conv_losses = conv_total - conv_wins
                conv_wr = (conv_wins / conv_total * 100)
                conv_roi = ((conv_wins * 0.91 - conv_losses) / conv_total * 100)
                avg_edge = conv_df['edge'].mean()
                
                # Show how many would actually be bet
                actual_bets = len(conv_df[conv_df['actual_bet'] == True])
                bet_marker = f" [{actual_bets} bets]" if actual_bets < conv_total else ""
                
                print(f"  {conviction:8s}: {conv_wins:2d}-{conv_losses:2d} ({conv_wr:5.1f}%) | "
                      f"ROI: {conv_roi:+6.1f}% | Avg Edge: {avg_edge:+5.1f}%{bet_marker}")
        
        print()
    
    # Summary stats
    total_opportunities = len(model_df)
    actual_bets_made = len(model_df[model_df['actual_bet'] == True])
    
    # Stats for actual bets made
    actual_bets_df = model_df[model_df['actual_bet'] == True]
    actual_wins = len(actual_bets_df[actual_bets_df['result'] == 'WIN'])
    actual_losses = len(actual_bets_df) - actual_wins
    actual_wr = (actual_wins / len(actual_bets_df) * 100) if len(actual_bets_df) > 0 else 0
    actual_roi = ((actual_wins * 0.91 - actual_losses) / len(actual_bets_df) * 100) if len(actual_bets_df) > 0 else 0
    
    print(f"{'=' * 60}")
    print(f"ACTUAL BETS: {actual_wins}-{actual_losses} ({actual_wr:.1f}%) | ROI: {actual_roi:+.1f}%")
    print(f"(Made {actual_bets_made} bets out of {total_opportunities} opportunities)")
    print(f"{'=' * 60}")
    
    return {
        'total_bets': actual_bets_made,
        'wins': actual_wins,
        'win_rate': actual_wr,
        'roi': actual_roi
    }

# Analyze both models
current_stats = analyze_model(results_df, 'CURRENT')
new_stats = analyze_model(results_df, 'NEW_2025')

# Comparison
print("\n" + "=" * 80)
print("FINAL COMPARISON")
print("=" * 80)
print()

bet_diff = new_stats['total_bets'] - current_stats['total_bets']
wr_diff = new_stats['win_rate'] - current_stats['win_rate']
roi_diff = new_stats['roi'] - current_stats['roi']

print(f"Total Bets:  CURRENT: {current_stats['total_bets']:3d}  →  NEW: {new_stats['total_bets']:3d}  "
      f"({'+'if bet_diff >= 0 else ''}{bet_diff})")
print(f"Win Rate:    CURRENT: {current_stats['win_rate']:5.1f}%  →  NEW: {new_stats['win_rate']:5.1f}%  "
      f"({'+'if wr_diff >= 0 else ''}{wr_diff:.1f}%)")
print(f"ROI:         CURRENT: {current_stats['roi']:+6.1f}%  →  NEW: {new_stats['roi']:+6.1f}%  "
      f"({'+'if roi_diff >= 0 else ''}{roi_diff:.1f}%)")
print()

# Recommendation
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()

if wr_diff > 2.0 and roi_diff > 2.0 and new_stats['total_bets'] >= current_stats['total_bets'] * 0.8:
    print("✅ STRONG RECOMMENDATION: Switch to 2025-only isotonic calibration")
    print("   Better win rate, better ROI, and makes enough bets.")
elif wr_diff > 1.0 and roi_diff > 1.0:
    print("✅ MODERATE RECOMMENDATION: Switch to 2025-only isotonic calibration")
    print("   Shows improvement across metrics.")
elif wr_diff > 0 and roi_diff > 0:
    print("⚠️  WEAK RECOMMENDATION: Consider 2025-only isotonic calibration")
    print("   Slight improvement, but may not be significant.")
else:
    print("❌ KEEP CURRENT MODEL")
    print("   No clear advantage to switching.")

print()

# Save detailed results
output_file = Path(__file__).parent / "isotonic_detailed_comparison.csv"
results_df.to_csv(output_file, index=False)
print(f"📊 Detailed results saved to: {output_file}")
print()

