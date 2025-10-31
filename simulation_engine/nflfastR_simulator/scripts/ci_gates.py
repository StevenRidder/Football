"""
Step 3.3: CI Gates for Model Quality

Gates that must pass:
1. Centering: |mean(spread_sim) - spread_line| < 0.25
2. Centering: |mean(total_sim) - total_line| < 0.25
3. Variance: 10 < spread_sd < 16
4. Variance: 7 < total_sd < 13
5. Reliability: Brier score < 0.26 (better than random)
6. Zero-mean features: |mean(pff_z_scores)| < 0.2 per week
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

def check_centering(results_df):
    """Check that centering is correct."""
    if 'spread_mean' not in results_df.columns:
        return False, "Missing spread_mean column"
    
    spread_errors = (results_df['spread_mean'] - results_df['spread_line']).abs()
    total_errors = (results_df['total_mean'] - results_df['total_line']).abs()
    
    max_spread_error = spread_errors.max()
    max_total_error = total_errors.max()
    
    if max_spread_error > 0.25:
        return False, f"Spread centering failed: max error {max_spread_error:.3f} > 0.25"
    
    if max_total_error > 0.25:
        return False, f"Total centering failed: max error {max_total_error:.3f} > 0.25"
    
    return True, "Centering OK"

def check_variance(results_df):
    """Check that variance is in healthy range."""
    if 'spread_sd' not in results_df.columns:
        return False, "Missing spread_sd column"
    
    spread_sd_mean = results_df['spread_sd'].mean()
    total_sd_mean = results_df['total_sd'].mean()
    
    if not (10 < spread_sd_mean < 16):
        return False, f"Spread SD out of range: {spread_sd_mean:.2f} not in [10, 16]"
    
    if not (7 < total_sd_mean < 13):
        return False, f"Total SD out of range: {total_sd_mean:.2f} not in [7, 13]"
    
    return True, f"Variance OK (spread_sd={spread_sd_mean:.2f}, total_sd={total_sd_mean:.2f})"

def check_reliability(results_df):
    """Check that reliability is better than random."""
    # Calculate Brier score
    spread_valid = results_df[results_df['home_covered'].notna()].copy()
    
    if len(spread_valid) == 0:
        return False, "No valid spread outcomes"
    
    brier_spread = np.mean((spread_valid['p_home_cover'] - spread_valid['home_covered'])**2)
    
    if brier_spread > 0.26:
        return False, f"Brier score too high: {brier_spread:.4f} > 0.26 (worse than random)"
    
    return True, f"Reliability OK (Brier={brier_spread:.4f})"

def check_zero_mean_features():
    """Check that PFF features are zero-mean within each week."""
    pff_file = Path("data/pff_raw/pff_weekly_zscores_2024.csv")
    
    if not pff_file.exists():
        return False, "PFF z-scores file not found"
    
    pff = pd.read_csv(pff_file)
    
    # Check each week
    for week in range(1, 9):
        week_data = pff[pff['week'] == week]
        if len(week_data) == 0:
            continue
        
        # Combine home and away
        all_pass = list(week_data['home_pass_mismatch_z']) + list(week_data['away_pass_mismatch_z'])
        all_run = list(week_data['home_run_mismatch_z']) + list(week_data['away_run_mismatch_z'])
        
        pass_mean = np.mean(all_pass)
        run_mean = np.mean(all_run)
        
        if abs(pass_mean) > 0.2:
            return False, f"Week {week} pass_mismatch mean {pass_mean:.3f} > 0.2"
        
        if abs(run_mean) > 0.2:
            return False, f"Week {week} run_mismatch mean {run_mean:.3f} > 0.2"
    
    return True, "Zero-mean features OK"

def run_ci_gates(results_csv="artifacts/backtest_with_pff.csv"):
    """Run all CI gates."""
    print("=" * 60)
    print("CI GATES")
    print("=" * 60)
    
    results = pd.read_csv(results_csv)
    
    gates = [
        ("Centering", check_centering(results)),
        ("Variance", check_variance(results)),
        ("Reliability", check_reliability(results)),
        ("Zero-mean features", check_zero_mean_features()),
    ]
    
    all_passed = True
    
    for gate_name, (passed, message) in gates:
        status = "✅" if passed else "❌"
        print(f"\n{status} {gate_name}: {message}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL GATES PASSED")
    else:
        print("❌ SOME GATES FAILED")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    # First, we need to re-run backtest with spread_mean and total_mean
    print("⚠️  Re-running backtest to get shape metrics...")
    import subprocess
    subprocess.run([sys.executable, "backtest_ultra_fast.py"], check=True)
    
    # Now run gates on the new results
    passed = run_ci_gates("artifacts/backtest_2024_w1-8.csv")
    
    sys.exit(0 if passed else 1)

