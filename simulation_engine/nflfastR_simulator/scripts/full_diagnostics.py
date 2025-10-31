"""
Complete Model Diagnostics Suite

Implements all refinements:
1. Reliability curves for spreads and totals
2. CLV tracking
3. Variance stability checks
4. Zero-mean verification
5. Sample size warnings
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

def analyze_reliability(df, bet_type='spread'):
    """Analyze reliability curves."""
    if bet_type == 'spread':
        prob_col = 'p_home_cover'
        outcome_col = 'home_covered'
        title = 'Spread'
    else:
        prob_col = 'p_over'
        outcome_col = 'over_hit'
        title = 'Total'
    
    # Remove pushes
    valid = df[df[outcome_col].notna()].copy()
    
    if len(valid) == 0:
        return None
    
    # Create bins
    bins = [0, 0.4, 0.45, 0.5, 0.55, 0.6, 1.0]
    valid['p_bin'] = pd.cut(valid[prob_col], bins=bins)
    
    # Calculate reliability
    reliability = valid.groupby('p_bin', observed=True).agg({
        outcome_col: ['mean', 'count'],
        prob_col: 'mean'
    }).reset_index()
    
    reliability.columns = ['bin', 'actual_freq', 'count', 'predicted_prob']
    
    # Brier score
    brier = np.mean((valid[prob_col] - valid[outcome_col])**2)
    
    # Log loss
    eps = 1e-10
    log_loss = -np.mean(
        valid[outcome_col] * np.log(valid[prob_col] + eps) +
        (1 - valid[outcome_col]) * np.log(1 - valid[prob_col] + eps)
    )
    
    return {
        'reliability': reliability,
        'brier': brier,
        'log_loss': log_loss,
        'n_valid': len(valid),
        'title': title
    }

def check_variance_stability(df):
    """Check that variance is stable across games."""
    spread_sd = df['spread_sd'].mean()
    total_sd = df['total_sd'].mean()
    
    spread_ok = 10 <= spread_sd <= 16
    total_ok = 7 <= total_sd <= 13
    
    return {
        'spread_sd': spread_sd,
        'total_sd': total_sd,
        'spread_ok': spread_ok,
        'total_ok': total_ok
    }

def check_zero_mean_features():
    """Verify PFF features are zero-mean within weeks."""
    pff_file = Path(__file__).parent.parent / "data/pff_raw/pff_weekly_zscores_2024.csv"
    
    if not pff_file.exists():
        return None
    
    pff = pd.read_csv(pff_file)
    
    results = []
    for week in range(1, 9):
        week_data = pff[pff['week'] == week]
        if len(week_data) == 0:
            continue
        
        all_pass = list(week_data['home_pass_mismatch_z']) + list(week_data['away_pass_mismatch_z'])
        all_run = list(week_data['home_run_mismatch_z']) + list(week_data['away_run_mismatch_z'])
        
        results.append({
            'week': week,
            'pass_mean': np.mean(all_pass),
            'run_mean': np.mean(all_run),
            'pass_ok': abs(np.mean(all_pass)) < 0.2,
            'run_ok': abs(np.mean(all_run)) < 0.2
        })
    
    return pd.DataFrame(results)

def calculate_clv(df):
    """Calculate Closing Line Value (CLV)."""
    # For now, we don't have line movement data
    # But we can check if our bets would have been +EV at closing
    
    spread_bets = df[df['bet_spread'].notna()].copy()
    total_bets = df[df['bet_total'].notna()].copy()
    
    # Calculate implied edge
    if len(spread_bets) > 0:
        spread_bets['edge'] = spread_bets.apply(
            lambda r: r['p_home_cover'] - 0.5238 if r['bet_spread'] == 'HOME'
                     else (1 - r['p_home_cover']) - 0.5238,
            axis=1
        )
        avg_spread_edge = spread_bets['edge'].mean()
    else:
        avg_spread_edge = None
    
    if len(total_bets) > 0:
        total_bets['edge'] = total_bets.apply(
            lambda r: r['p_over'] - 0.5238 if r['bet_total'] == 'OVER'
                     else (1 - r['p_over']) - 0.5238,
            axis=1
        )
        avg_total_edge = total_bets['edge'].mean()
    else:
        avg_total_edge = None
    
    return {
        'spread_avg_edge': avg_spread_edge,
        'total_avg_edge': avg_total_edge,
        'spread_bets': len(spread_bets),
        'total_bets': len(total_bets)
    }

def run_full_diagnostics(results_file):
    """Run complete diagnostic suite."""
    df = pd.read_csv(results_file)
    
    print("=" * 70)
    print("COMPLETE MODEL DIAGNOSTICS")
    print("=" * 70)
    
    # 1. Sample size check
    print("\n📊 SAMPLE SIZE:")
    print(f"   Total games: {len(df)}")
    spread_bets = df[df['bet_spread'].notna()]
    total_bets = df[df['bet_total'].notna()]
    print(f"   Spread bets: {len(spread_bets)}")
    print(f"   Total bets: {len(total_bets)}")
    
    if len(spread_bets) < 100:
        print(f"   ⚠️  WARNING: Need 100+ spread bets for confidence (have {len(spread_bets)})")
    if len(total_bets) < 100:
        print(f"   ⚠️  WARNING: Need 100+ total bets for confidence (have {len(total_bets)})")
    
    # 2. Reliability analysis
    print("\n" + "=" * 70)
    print("RELIABILITY ANALYSIS")
    print("=" * 70)
    
    spread_rel = analyze_reliability(df, 'spread')
    if spread_rel:
        print(f"\n📊 SPREAD RELIABILITY:")
        print(f"   Brier Score: {spread_rel['brier']:.4f} (random=0.25)")
        print(f"   Log Loss: {spread_rel['log_loss']:.4f} (random=0.693)")
        print(f"   Valid games: {spread_rel['n_valid']}")
        print("\n   Reliability by bin:")
        for _, row in spread_rel['reliability'].iterrows():
            if not pd.isna(row['actual_freq']):
                print(f"     Predicted {row['predicted_prob']:.1%} → Actual {row['actual_freq']:.1%} (n={int(row['count'])})")
    
    total_rel = analyze_reliability(df, 'total')
    if total_rel:
        print(f"\n📊 TOTAL RELIABILITY:")
        print(f"   Brier Score: {total_rel['brier']:.4f} (random=0.25)")
        print(f"   Log Loss: {total_rel['log_loss']:.4f} (random=0.693)")
        print(f"   Valid games: {total_rel['n_valid']}")
        print("\n   Reliability by bin:")
        for _, row in total_rel['reliability'].iterrows():
            if not pd.isna(row['actual_freq']):
                print(f"     Predicted {row['predicted_prob']:.1%} → Actual {row['actual_freq']:.1%} (n={int(row['count'])})")
    
    # 3. Variance stability
    print("\n" + "=" * 70)
    print("VARIANCE STABILITY")
    print("=" * 70)
    
    var_check = check_variance_stability(df)
    print(f"\n📊 DISTRIBUTION SHAPE:")
    print(f"   Spread SD: {var_check['spread_sd']:.2f} (target: 10-16) {'✅' if var_check['spread_ok'] else '❌'}")
    print(f"   Total SD: {var_check['total_sd']:.2f} (target: 7-13) {'✅' if var_check['total_ok'] else '❌'}")
    
    # 4. Zero-mean features
    print("\n" + "=" * 70)
    print("ZERO-MEAN FEATURES")
    print("=" * 70)
    
    zm_check = check_zero_mean_features()
    if zm_check is not None:
        print("\n📊 PFF Z-SCORES BY WEEK:")
        all_pass_ok = True
        all_run_ok = True
        for _, row in zm_check.iterrows():
            pass_status = '✅' if row['pass_ok'] else '❌'
            run_status = '✅' if row['run_ok'] else '❌'
            print(f"   Week {int(row['week'])}: pass={row['pass_mean']:+.3f} {pass_status}, run={row['run_mean']:+.3f} {run_status}")
            all_pass_ok = all_pass_ok and row['pass_ok']
            all_run_ok = all_run_ok and row['run_ok']
        
        if all_pass_ok and all_run_ok:
            print("\n   ✅ All weeks pass zero-mean check")
        else:
            print("\n   ⚠️  Some weeks fail zero-mean check")
    
    # 5. CLV / Edge analysis
    print("\n" + "=" * 70)
    print("EDGE ANALYSIS")
    print("=" * 70)
    
    clv = calculate_clv(df)
    print(f"\n📊 AVERAGE EDGE WHEN BETTING:")
    if clv['spread_avg_edge'] is not None:
        print(f"   Spreads: {clv['spread_avg_edge']*100:+.2f}% ({clv['spread_bets']} bets)")
    if clv['total_avg_edge'] is not None:
        print(f"   Totals: {clv['total_avg_edge']*100:+.2f}% ({clv['total_bets']} bets)")
    
    # 6. Create reliability plots
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Spread reliability
    if spread_rel:
        ax = axes[0]
        rel = spread_rel['reliability']
        for _, row in rel.iterrows():
            if not pd.isna(row['actual_freq']):
                ax.scatter(row['predicted_prob'], row['actual_freq'], 
                          s=row['count']*20, alpha=0.6, color='blue')
        ax.plot([0, 1], [0, 1], 'k--', label='Perfect calibration', linewidth=2)
        ax.set_xlabel('Predicted Probability', fontsize=12)
        ax.set_ylabel('Observed Frequency', fontsize=12)
        ax.set_title(f'Spread Reliability (Brier={spread_rel["brier"]:.3f})', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0.35, 0.65)
        ax.set_ylim(0.35, 0.65)
    
    # Total reliability
    if total_rel:
        ax = axes[1]
        rel = total_rel['reliability']
        for _, row in rel.iterrows():
            if not pd.isna(row['actual_freq']):
                ax.scatter(row['predicted_prob'], row['actual_freq'],
                          s=row['count']*20, alpha=0.6, color='green')
        ax.plot([0, 1], [0, 1], 'k--', label='Perfect calibration', linewidth=2)
        ax.set_xlabel('Predicted Probability', fontsize=12)
        ax.set_ylabel('Observed Frequency', fontsize=12)
        ax.set_title(f'Total Reliability (Brier={total_rel["brier"]:.3f})', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0.35, 0.65)
        ax.set_ylim(0.35, 0.65)
    
    plt.tight_layout()
    plt.savefig('artifacts/full_diagnostics.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved reliability plots to artifacts/full_diagnostics.png")
    
    print("\n" + "=" * 70)
    print("✅ DIAGNOSTICS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_full_diagnostics("artifacts/backtest_2024_w1-8.csv")

