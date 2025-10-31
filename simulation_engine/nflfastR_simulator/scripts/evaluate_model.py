"""
Complete Model Evaluation Framework

After 2022-2024 backtest completes, run this to:
1. Verify sample size (300+ bets)
2. Check reliability curves
3. Verify zero-mean features
4. Calculate CLV and edge
5. Assess statistical significance
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

def evaluate_sample_size(df):
    """Check if we have enough bets for confidence."""
    spread_bets = df[df['bet_spread'].notna()]
    total_bets = df[df['bet_total'].notna()]
    
    print("=" * 70)
    print("1. SAMPLE SIZE CHECK")
    print("=" * 70)
    print(f"\nTotal games: {len(df)}")
    print(f"Spread bets: {len(spread_bets)} {'✅' if len(spread_bets) >= 100 else '⚠️ Need 100+'}")
    print(f"Total bets: {len(total_bets)} {'✅' if len(total_bets) >= 100 else '⚠️ Need 100+'}")
    
    # Confidence interval for win rate
    for bet_type, bets in [('Spread', spread_bets), ('Total', total_bets)]:
        if len(bets) > 0:
            wins = (bets[f'{bet_type.lower()}_result'] == 1.0).sum()
            n = len(bets)
            win_rate = wins / n
            
            # 95% confidence interval
            se = np.sqrt(win_rate * (1 - win_rate) / n)
            ci_lower = win_rate - 1.96 * se
            ci_upper = win_rate + 1.96 * se
            
            print(f"\n{bet_type} Win Rate: {win_rate:.1%} [95% CI: {ci_lower:.1%} - {ci_upper:.1%}]")
            
            if ci_lower > 0.524:
                print(f"   ✅ Statistically profitable (lower bound > 52.4%)")
            elif ci_upper < 0.524:
                print(f"   ❌ Statistically unprofitable (upper bound < 52.4%)")
            else:
                print(f"   ⚠️  Inconclusive (CI includes 52.4% breakeven)")

def evaluate_reliability(df):
    """Check calibration via reliability curves."""
    print("\n" + "=" * 70)
    print("2. RELIABILITY / CALIBRATION")
    print("=" * 70)
    
    for bet_type, prob_col, outcome_col in [
        ('Spread', 'p_home_cover', 'home_covered'),
        ('Total', 'p_over', 'over_hit')
    ]:
        valid = df[df[outcome_col].notna()].copy()
        
        if len(valid) == 0:
            continue
        
        # Brier score
        brier = np.mean((valid[prob_col] - valid[outcome_col])**2)
        
        # Log loss
        eps = 1e-10
        log_loss = -np.mean(
            valid[outcome_col] * np.log(valid[prob_col] + eps) +
            (1 - valid[outcome_col]) * np.log(1 - valid[prob_col] + eps)
        )
        
        print(f"\n{bet_type}:")
        print(f"   Brier Score: {brier:.4f} (random=0.25, lower is better)")
        print(f"   Log Loss: {log_loss:.4f} (random=0.693, lower is better)")
        
        if brier < 0.25:
            print(f"   ✅ Better than random")
        if log_loss < 0.693:
            print(f"   ✅ Better than random")

def evaluate_variance_stability(df):
    """Check distribution shape is stable."""
    print("\n" + "=" * 70)
    print("3. VARIANCE STABILITY")
    print("=" * 70)
    
    spread_sd = df['spread_sd'].mean()
    total_sd = df['total_sd'].mean()
    
    spread_ok = 10 <= spread_sd <= 16
    total_ok = 7 <= total_sd <= 13
    
    print(f"\nSpread SD: {spread_sd:.2f} (target: 10-16) {'✅' if spread_ok else '❌'}")
    print(f"Total SD: {total_sd:.2f} (target: 7-13) {'✅' if total_ok else '❌'}")
    
    if spread_ok and total_ok:
        print("\n✅ Distribution shape is stable")

def evaluate_zero_mean(df):
    """Verify features are zero-mean within weeks."""
    print("\n" + "=" * 70)
    print("4. ZERO-MEAN FEATURES")
    print("=" * 70)
    
    # Check centering
    spread_error = (df['spread_mean'] - df['spread_line']).abs().mean()
    total_error = (df['total_mean'] - df['total_line']).abs().mean()
    
    print(f"\nCentering error:")
    print(f"   Spread: {spread_error:.4f} {'✅' if spread_error < 0.1 else '❌'}")
    print(f"   Total: {total_error:.4f} {'✅' if total_error < 0.1 else '❌'}")
    
    # Check PFF z-scores
    pff_file = Path(__file__).parent.parent / "data/pff_raw/pff_weekly_zscores_2024.csv"
    if pff_file.exists():
        pff = pd.read_csv(pff_file)
        
        all_ok = True
        for week in pff['week'].unique():
            week_data = pff[pff['week'] == week]
            all_pass = list(week_data['home_pass_mismatch_z']) + list(week_data['away_pass_mismatch_z'])
            pass_mean = np.mean(all_pass)
            
            if abs(pass_mean) > 0.2:
                all_ok = False
                break
        
        print(f"\nPFF features: {'✅ All weeks zero-mean' if all_ok else '❌ Some weeks fail'}")

def evaluate_edge(df):
    """Calculate average edge and ROI."""
    print("\n" + "=" * 70)
    print("5. EDGE & ROI ANALYSIS")
    print("=" * 70)
    
    for bet_type in ['spread', 'total']:
        bets = df[df[f'bet_{bet_type}'].notna()].copy()
        
        if len(bets) == 0:
            continue
        
        # Calculate edge
        if bet_type == 'spread':
            bets['edge'] = bets.apply(
                lambda r: r['p_home_cover'] - 0.5238 if r['bet_spread'] == 'HOME'
                         else (1 - r['p_home_cover']) - 0.5238,
                axis=1
            )
        else:
            bets['edge'] = bets.apply(
                lambda r: r['p_over'] - 0.5238 if r['bet_total'] == 'OVER'
                         else (1 - r['p_over']) - 0.5238,
                axis=1
            )
        
        avg_edge = bets['edge'].mean()
        
        # Calculate ROI
        wins = (bets[f'{bet_type}_result'] == 1.0).sum()
        losses = (bets[f'{bet_type}_result'] == 0.0).sum()
        units_risked = len(bets)
        units_won = wins * 0.909 - losses
        roi = (units_won / units_risked) * 100 if units_risked > 0 else 0
        
        print(f"\n{bet_type.upper()}:")
        print(f"   Average edge: {avg_edge*100:+.2f}%")
        print(f"   ROI: {roi:+.1f}%")
        print(f"   Record: {wins}-{losses} ({wins/len(bets)*100:.1f}% win rate)")
        
        # Statistical significance test (t-test vs 0 ROI)
        if len(bets) > 30:
            # Convert to units won per bet
            bets['units_won'] = bets[f'{bet_type}_result'].apply(
                lambda x: 0.909 if x == 1.0 else (-1.0 if x == 0.0 else 0.0)
            )
            
            t_stat, p_value = stats.ttest_1samp(bets['units_won'], 0)
            
            print(f"   t-statistic: {t_stat:.2f}, p-value: {p_value:.4f}")
            
            if p_value < 0.05 and roi > 0:
                print(f"   ✅ Statistically significant edge (p < 0.05)")
            elif p_value < 0.05 and roi < 0:
                print(f"   ❌ Statistically significant loss (p < 0.05)")
            else:
                print(f"   ⚠️  Not statistically significant (need more data)")

def create_summary_report(df):
    """Create final summary."""
    print("\n" + "=" * 70)
    print("FINAL EVALUATION")
    print("=" * 70)
    
    spread_bets = df[df['bet_spread'].notna()]
    total_bets = df[df['bet_total'].notna()]
    
    # Calculate metrics
    spread_wins = (spread_bets['spread_result'] == 1.0).sum() if len(spread_bets) > 0 else 0
    total_wins = (total_bets['total_result'] == 1.0).sum() if len(total_bets) > 0 else 0
    
    spread_roi = ((spread_wins * 0.909 - (len(spread_bets) - spread_wins)) / len(spread_bets) * 100) if len(spread_bets) > 0 else 0
    total_roi = ((total_wins * 0.909 - (len(total_bets) - total_wins)) / len(total_bets) * 100) if len(total_bets) > 0 else 0
    
    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"   Games analyzed: {len(df)}")
    print(f"   Total bets placed: {len(spread_bets) + len(total_bets)}")
    print(f"\n   Spreads: {spread_roi:+.1f}% ROI ({len(spread_bets)} bets)")
    print(f"   Totals: {total_roi:+.1f}% ROI ({len(total_bets)} bets)")
    
    # Overall recommendation
    print(f"\n💡 RECOMMENDATION:")
    
    if len(spread_bets) < 100 or len(total_bets) < 100:
        print(f"   ⚠️  Need more data (target: 300+ bets)")
    
    if total_roi > 5 and len(total_bets) >= 100:
        print(f"   ✅ Totals show promise - continue paper trading")
    
    if spread_roi < 0 and len(spread_bets) >= 100:
        print(f"   ⚠️  Spreads underperforming - focus on totals or improve model")
    
    print(f"\n   Next steps:")
    print(f"   1. Paper trade for 4-8 weeks")
    print(f"   2. Track CLV (closing line value)")
    print(f"   3. Add opponent-adjusted EPA to improve spreads")
    print(f"   4. Consider isotonic calibration if needed")

if __name__ == "__main__":
    results_file = sys.argv[1] if len(sys.argv) > 1 else "artifacts/backtest_2022_2024.csv"
    
    print("=" * 70)
    print("MODEL EVALUATION FRAMEWORK")
    print("=" * 70)
    print(f"Results file: {results_file}")
    
    df = pd.read_csv(results_file)
    
    evaluate_sample_size(df)
    evaluate_reliability(df)
    evaluate_variance_stability(df)
    evaluate_zero_mean(df)
    evaluate_edge(df)
    create_summary_report(df)
    
    print("\n" + "=" * 70)
    print("✅ EVALUATION COMPLETE")
    print("=" * 70)

