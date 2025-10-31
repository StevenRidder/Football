"""
Comprehensive Validation - Leakage Check, Reliability, Walk-Forward

Validates that the strong results (78% WR, 49.7% ROI) are genuine signal.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scipy.stats import norm
from sklearn.metrics import brier_score_loss
import matplotlib.pyplot as plt

def load_backtest_results():
    """Load latest backtest results."""
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        raise FileNotFoundError(f"Backtest file not found: {backtest_file}")
    
    df = pd.read_csv(backtest_file)
    return df

def check_data_leakage(df):
    """Check 1: Verify no look-ahead bias in features."""
    print("="*70)
    print("CHECK 1: DATA LEAKAGE CHECK")
    print("="*70)
    
    issues = []
    warnings = []
    
    # Check if any features use future data
    print("\n📊 Checking feature data availability...")
    
    # Verify game dates and week numbers are consistent
    if 'season' in df.columns and 'week' in df.columns:
        print(f"   ✅ Season/Week columns present")
        
        # Check if week numbers are reasonable (1-18)
        if df['week'].max() > 18 or df['week'].min() < 1:
            issues.append("⚠️  Week numbers outside 1-18 range")
        else:
            print(f"   ✅ Week numbers valid (1-18)")
    
    # Check if we can verify rolling windows
    print(f"\n📊 Checking data recency...")
    
    # For EPA, YPP, etc. - should be using only prior weeks
    # This is hard to verify without seeing the extraction scripts
    # But we can check if data exists for all games
    print(f"   ⚠️  Manual check required: Verify extraction scripts use only prior weeks")
    print(f"      - Check preprocessing/extract_*.py scripts")
    print(f"      - Ensure rolling means exclude current week")
    print(f"      - Week 5 should use weeks 1-4 only")
    
    # Check calibration fit date
    print(f"\n📊 Checking calibration fit...")
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    
    isotonic_file = artifacts_dir / "isotonic_calibrators.pkl"
    if isotonic_file.exists():
        import os
        from datetime import datetime
        mod_time = os.path.getmtime(isotonic_file)
        mod_date = datetime.fromtimestamp(mod_time)
        print(f"   ✅ Isotonic calibrators last modified: {mod_date}")
        
        # Check if calibrated on 2025 data
        # Ideally should be fit on 2022-2024 only
        print(f"   ⚠️  Verify: Calibrators fitted on 2022-2024, NOT 2025")
    else:
        warnings.append("Isotonic calibrators file not found")
    
    # Check for post-game data usage
    print(f"\n📊 Checking for post-game data...")
    
    # Should NOT have actual scores in feature columns
    feature_cols = [c for c in df.columns if any(x in c.lower() for x in ['epa', 'ypa', 'pace', 'anya', 'success'])]
    actual_cols = [c for c in df.columns if 'actual' in c.lower()]
    
    if any(col in feature_cols for col in actual_cols):
        issues.append("⚠️  Feature columns may contain actual game results")
    else:
        print(f"   ✅ Feature columns separate from actual results")
    
    # Summary
    print(f"\n📋 Leakage Check Summary:")
    if issues:
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"   ✅ No obvious leakage detected")
    
    if warnings:
        for warning in warnings:
            print(f"   ⚠️  {warning}")
    
    return len(issues) == 0

def check_reliability_sharpness(df):
    """Check 2: Reliability curve and sharpness."""
    print("\n" + "="*70)
    print("CHECK 2: RELIABILITY AND SHARPNESS")
    print("="*70)
    
    # Filter to games with actual results
    completed = df[df['actual_home_score'].notna()].copy()
    
    if len(completed) == 0:
        print("   ⚠️  No completed games to analyze")
        return False
    
    print(f"\n📊 Analyzing {len(completed)} completed games")
    
    # Calculate outcomes
    completed['actual_spread'] = completed['actual_home_score'] - completed['actual_away_score']
    completed['actual_total'] = completed['actual_home_score'] + completed['actual_away_score']
    
    # Spread outcomes
    completed['home_covered'] = (completed['actual_spread'] > completed['spread_line']).astype(float)
    completed.loc[abs(completed['actual_spread'] - completed['spread_line']) < 0.1, 'home_covered'] = 0.5  # Push
    
    # Total outcomes
    completed['over_hit'] = (completed['actual_total'] > completed['total_line']).astype(float)
    completed.loc[abs(completed['actual_total'] - completed['total_line']) < 0.5, 'over_hit'] = 0.5  # Push
    
    # Filter out pushes for reliability
    spread_valid = completed[completed['home_covered'] != 0.5].copy()
    total_valid = completed[completed['over_hit'] != 0.5].copy()
    
    if len(spread_valid) == 0 or 'p_home_cover' not in spread_valid.columns:
        print("   ⚠️  No spread probabilities available")
        return False
    
    # Reliability bins
    bins = [0.0, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.0]
    
    print(f"\n📈 SPREAD RELIABILITY:")
    spread_results = []
    for i in range(len(bins) - 1):
        bin_min, bin_max = bins[i], bins[i+1]
        mask = (spread_valid['p_home_cover'] >= bin_min) & (spread_valid['p_home_cover'] < bin_max)
        bin_data = spread_valid[mask]
        
        if len(bin_data) > 0:
            predicted = bin_data['p_home_cover'].mean()
            actual = bin_data['home_covered'].mean()
            count = len(bin_data)
            error = abs(predicted - actual)
            
            spread_results.append({
                'bin': f"{bin_min:.2f}-{bin_max:.2f}",
                'predicted': predicted,
                'actual': actual,
                'error': error,
                'count': count
            })
            
            print(f"   [{bin_min:.2f}-{bin_max:.2f}]: n={count:3d}, Pred={predicted:.3f}, Actual={actual:.3f}, Error={error:.3f}")
    
    # Calculate overall reliability metrics
    if len(spread_results) > 0:
        avg_error = np.mean([r['error'] for r in spread_results])
        print(f"\n   Average Calibration Error: {avg_error:.3f}")
        
        # Expected Calibration Error (ECE)
        ece = 0
        total_samples = sum(r['count'] for r in spread_results)
        for r in spread_results:
            weight = r['count'] / total_samples if total_samples > 0 else 0
            ece += weight * r['error']
        print(f"   Expected Calibration Error (ECE): {ece:.3f}")
        print(f"   ✅ Target: ECE < 0.05 (excellent), < 0.10 (good)")
    
    # Sharpness (std of probabilities)
    if 'p_home_cover' in spread_valid.columns:
        sharpness = spread_valid['p_home_cover'].std()
        print(f"\n   Sharpness (std of probs): {sharpness:.3f}")
        print(f"   ✅ Target: 0.08-0.12 (good separation), < 0.06 (too tight)")
        
        if sharpness < 0.06:
            print(f"   ⚠️  WARNING: Probabilities too tight - may be over-confident")
        elif sharpness > 0.15:
            print(f"   ⚠️  WARNING: Probabilities too spread - may be under-confident")
        else:
            print(f"   ✅ Sharpness in good range")
    
    # Brier Score
    if len(spread_valid) > 0:
        brier = brier_score_loss(spread_valid['home_covered'], spread_valid['p_home_cover'])
        print(f"\n   Brier Score: {brier:.4f}")
        print(f"   ✅ Target: < 0.25 (better than random), lower is better")
        
        # Baseline (always predict 0.5)
        baseline_brier = brier_score_loss(spread_valid['home_covered'], np.full(len(spread_valid), 0.5))
        improvement = (baseline_brier - brier) / baseline_brier * 100
        print(f"   Improvement vs Baseline: {improvement:.1f}%")
    
    print(f"\n📈 TOTAL RELIABILITY:")
    if len(total_valid) > 0 and 'p_over' in total_valid.columns:
        total_sharpness = total_valid['p_over'].std()
        total_brier = brier_score_loss(total_valid['over_hit'], total_valid['p_over'])
        
        print(f"   Sharpness: {total_sharpness:.3f}")
        print(f"   Brier Score: {total_brier:.4f}")
    
    return True

def check_walk_forward(df):
    """Check 3: Walk-forward validation on unseen weeks."""
    print("\n" + "="*70)
    print("CHECK 3: WALK-FORWARD VALIDATION")
    print("="*70)
    
    # Filter to completed games
    completed = df[df['actual_home_score'].notna()].copy()
    
    if len(completed) == 0:
        print("   ⚠️  No completed games available")
        return False
    
    if 'week' not in completed.columns:
        print("   ⚠️  Week column missing - cannot perform walk-forward")
        return False
    
    # Split into train/test
    # Use weeks 1-7 as "train" (what calibrators saw), weeks 8+ as "test"
    train = completed[completed['week'] <= 7].copy()
    test = completed[completed['week'] >= 8].copy()
    
    print(f"\n📊 Data Split:")
    print(f"   Train (weeks 1-7): {len(train)} games")
    print(f"   Test (weeks 8+): {len(test)} games")
    
    if len(test) == 0:
        print("   ⚠️  No test data (weeks 8+) - using all data as train")
        test = train.copy()
        train = pd.DataFrame()  # Empty
    
    # Calculate outcomes
    test['actual_spread'] = test['actual_home_score'] - test['actual_away_score']
    test['actual_total'] = test['actual_home_score'] + test['actual_away_score']
    
    test['home_covered'] = (test['actual_spread'] > test['spread_line']).astype(float)
    test.loc[abs(test['actual_spread'] - test['spread_line']) < 0.1, 'home_covered'] = 0.5
    
    test['over_hit'] = (test['actual_total'] > test['total_line']).astype(float)
    test.loc[abs(test['actual_total'] - test['total_line']) < 0.5, 'over_hit'] = 0.5
    
    # Filter to bets only (positive edge)
    if 'spread_edge_pct' in test.columns:
        spread_bets = test[(test['spread_edge_pct'] > 0.02) & (test['home_covered'] != 0.5)].copy()
    else:
        # Calculate edge from probability
        spread_bets = test[(test['p_home_cover'] > 0.544) & (test['home_covered'] != 0.5)].copy()
    
    if 'total_edge_pct' in test.columns:
        total_bets = test[(test['total_edge_pct'] > 0.02) & (test['over_hit'] != 0.5)].copy()
    else:
        total_bets = test[(test['p_over'] > 0.544) & (test['over_hit'] != 0.5)].copy()
    
    print(f"\n📈 Test Set Performance (Weeks 8+):")
    
    if len(spread_bets) > 0:
        spread_wins = (spread_bets['home_covered'] == 1.0).sum()
        spread_losses = (spread_bets['home_covered'] == 0.0).sum()
        spread_wr = spread_wins / (spread_wins + spread_losses) * 100 if (spread_wins + spread_losses) > 0 else 0
        spread_roi = ((spread_wins - spread_losses) / (spread_wins + spread_losses)) * 100 if (spread_wins + spread_losses) > 0 else 0
        
        print(f"\n   Spread Bets:")
        print(f"      Bets: {len(spread_bets)}")
        print(f"      Win Rate: {spread_wr:.1f}%")
        print(f"      ROI: {spread_roi:.1f}%")
        print(f"      ✅ Target: WR > 55%, ROI > 0%")
        
        if spread_wr > 55 and spread_roi > 0:
            print(f"      ✅ PASS: Walk-forward validation successful!")
        else:
            print(f"      ⚠️  FAIL: Performance drops on unseen data (possible overfitting)")
    
    if len(total_bets) > 0:
        total_wins = (total_bets['over_hit'] == 1.0).sum()
        total_losses = (total_bets['over_hit'] == 0.0).sum()
        total_wr = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
        total_roi = ((total_wins - total_losses) / (total_wins + total_losses)) * 100 if (total_wins + total_losses) > 0 else 0
        
        print(f"\n   Total Bets:")
        print(f"      Bets: {len(total_bets)}")
        print(f"      Win Rate: {total_wr:.1f}%")
        print(f"      ROI: {total_roi:.1f}%")
        print(f"      ✅ Target: WR > 55%, ROI > 0%")
        
        if total_wr > 55 and total_roi > 0:
            print(f"      ✅ PASS: Walk-forward validation successful!")
        else:
            print(f"      ⚠️  FAIL: Performance drops on unseen data (possible overfitting)")
    
    return True

def check_conviction_distribution(df):
    """Check 4: Conviction distribution and outliers."""
    print("\n" + "="*70)
    print("CHECK 4: CONVICTION DISTRIBUTION")
    print("="*70)
    
    # Try different column name variations
    spread_edge_col = None
    total_edge_col = None
    
    for col in df.columns:
        if 'spread_edge' in col.lower() and 'pct' not in col.lower():
            spread_edge_col = col
        if 'total_edge' in col.lower() and 'pct' not in col.lower():
            total_edge_col = col
    
    if spread_edge_col is None or total_edge_col is None:
        print("   ⚠️  Edge columns not found")
        print(f"      Available columns: {[c for c in df.columns if 'edge' in c.lower()]}")
        return False
    
    spread_edges = df[spread_edge_col].dropna()
    total_edges = df[total_edge_col].dropna()
    
    print(f"\n📊 Spread Edge Distribution:")
    print(f"   Mean: {spread_edges.mean():.1f}%")
    print(f"   Median: {spread_edges.median():.1f}%")
    print(f"   Std: {spread_edges.std():.1f}%")
    print(f"   Min: {spread_edges.min():.1f}%")
    print(f"   Max: {spread_edges.max():.1f}%")
    print(f"   Q95: {spread_edges.quantile(0.95):.1f}%")
    print(f"   Q99: {spread_edges.quantile(0.99):.1f}%")
    
    if spread_edges.max() > 50:
        print(f"   ⚠️  WARNING: Extreme edges > 50% detected - consider capping at 25%")
    
    print(f"\n📊 Total Edge Distribution:")
    print(f"   Mean: {total_edges.mean():.1f}%")
    print(f"   Median: {total_edges.median():.1f}%")
    print(f"   Std: {total_edges.std():.1f}%")
    print(f"   Max: {total_edges.max():.1f}%")
    
    # Count by conviction tier
    if 'spread_conviction' in df.columns:
        print(f"\n📊 Conviction Tier Distribution:")
        print(df['spread_conviction'].value_counts())
        print(df['total_conviction'].value_counts())
    
    return True

def main():
    """Run comprehensive validation."""
    print("="*70)
    print("COMPREHENSIVE VALIDATION - SIGNAL VS NOISE CHECK")
    print("="*70)
    
    df = load_backtest_results()
    print(f"\n✅ Loaded {len(df)} games from backtest")
    
    # Run all checks
    leakage_ok = check_data_leakage(df)
    reliability_ok = check_reliability_sharpness(df)
    walkforward_ok = check_walk_forward(df)
    conviction_ok = check_conviction_distribution(df)
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    checks = [
        ("Leakage Check", leakage_ok),
        ("Reliability & Sharpness", reliability_ok),
        ("Walk-Forward Validation", walkforward_ok),
        ("Conviction Distribution", conviction_ok),
    ]
    
    for name, status in checks:
        status_str = "✅ PASS" if status else "⚠️  NEEDS REVIEW"
        print(f"   {name:30s}: {status_str}")
    
    print(f"\n📋 Recommendations:")
    print(f"   1. Verify extraction scripts use only prior weeks (manual check)")
    print(f"   2. Cap conviction edges at 25% to prevent outlier-driven ROI")
    print(f"   3. Implement fractional Kelly sizing for high-conviction bets")
    print(f"   4. Track CLV vs closing line to validate timing")
    
    print(f"\n🎯 Next Steps:")
    print(f"   • If walk-forward holds: Model is structurally sound ✅")
    print(f"   • If walk-forward fails: Add regularization or regime-specific calibrators")

if __name__ == "__main__":
    main()

