"""
Fit probability calibrators from historical backtest data.

This script:
1. Loads backtest results with raw spreads/SDs and actual outcomes
2. Calculates z-scores: z = (sim_mean - market) / sim_sd
3. Fits isotonic regression (preferred) or Platt scaling
4. Saves separate calibrators for spreads and totals
5. Validates with reliability diagnostics
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import pickle
from simulator.probability_calibration import (
    ProbabilityCalibrator,
    calculate_z_scores,
    AdaptiveEnsemble
)

def fit_spread_calibrator(method: str = 'isotonic'):
    """
    Fit calibrator for spreads using z-scores.
    
    Args:
        method: 'isotonic' (preferred) or 'platt'
    """
    print("="*70)
    print(f"FITTING SPREAD PROBABILITY CALIBRATOR ({method.upper()})")
    print("="*70)
    
    # Load backtest results
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        print(f"❌ Backtest file not found: {backtest_file}")
        print("   Run backtest_all_games_conviction.py first")
        return None
    
    df = pd.read_csv(backtest_file)
    print(f"\n📂 Loaded {len(df)} games from backtest")
    
    # Check required columns (note: spread_sd is centered, spread_raw_sd is raw)
    required = ['spread_raw', 'spread_raw_sd', 'spread_line', 'actual_home_score', 'actual_away_score']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        print(f"❌ Missing required columns: {missing}")
        print(f"   Available columns: {df.columns.tolist()}")
        return None
    
    # Filter to games with valid data and results
    # Use raw_sd if available, otherwise use centered sd as proxy
    if 'spread_raw_sd' in df.columns:
        sd_col = 'spread_raw_sd'
    elif 'spread_sd' in df.columns:
        sd_col = 'spread_sd'  # Fallback to centered SD
    else:
        print("❌ Need either spread_raw_sd or spread_sd column")
        return None
    
    df_valid = df[
        df['spread_raw'].notna() & 
        df[sd_col].notna() &
        df['spread_line'].notna() &
        df['actual_home_score'].notna() &
        df['actual_away_score'].notna()
    ].copy()
    
    print(f"✅ {len(df_valid)} games with valid data")
    
    if len(df_valid) < 50:
        print(f"⚠️  Warning: Only {len(df_valid)} games - may need more data for reliable calibration")
    
    # Calculate actual outcomes: did home cover?
    actual_spreads = df_valid['actual_home_score'].values - df_valid['actual_away_score'].values
    market_spreads = df_valid['spread_line'].values
    
    # Home covers if (actual_spread - market_spread) > 0
    # Handle exact pushes (difference = 0)
    push_mask = np.abs(actual_spreads - market_spreads) < 0.01  # Within 0.01 = push
    outcomes = (actual_spreads - market_spreads > 0).astype(float)
    outcomes[push_mask] = 0.5  # Mark pushes
    
    # Filter out pushes
    valid_mask = ~push_mask
    sim_spreads = df_valid['spread_raw'].values[valid_mask]
    sim_sds = df_valid[sd_col].values[valid_mask]
    market_spreads_valid = market_spreads[valid_mask]
    outcomes_valid = outcomes[valid_mask].astype(int)
    
    print(f"✅ {len(outcomes_valid)} games (excluding {push_mask.sum()} pushes)")
    print(f"   Home covers: {outcomes_valid.sum()} ({outcomes_valid.mean():.1%})")
    
    # Fit calibrator using z-scores
    print(f"\n🔧 Fitting {method} calibrator (using z-scores)...")
    calibrator = ProbabilityCalibrator(method=method, z_cap=3.0)
    calibrator.fit_from_historical(
        sim_spreads, sim_sds, market_spreads_valid, outcomes_valid
    )
    
    # Validate calibration with reliability plot
    print(f"\n📊 Calibration Validation (Reliability):")
    z_scores = calculate_z_scores(sim_spreads, sim_sds, market_spreads_valid)
    pred_probs = np.array([
        calibrator.predict_proba(sim_spreads[i], sim_sds[i], market_spreads_valid[i])
        for i in range(len(sim_spreads))
    ])
    
    # Bin predictions and compare to actual
    n_bins = 10
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    
    print(f"\n   Reliability Bins (predicted vs actual):")
    ece = 0.0  # Expected Calibration Error
    total_samples = 0
    
    for i in range(n_bins):
        bin_mask = (pred_probs >= bins[i]) & (pred_probs < bins[i+1])
        if i == n_bins - 1:  # Include upper bound
            bin_mask = (pred_probs >= bins[i]) & (pred_probs <= bins[i+1])
        
        n_bin = bin_mask.sum()
        if n_bin >= 5:  # At least 5 samples
            bin_pred = pred_probs[bin_mask].mean()
            bin_actual = outcomes_valid[bin_mask].mean()
            bin_error = abs(bin_pred - bin_actual)
            ece += bin_error * n_bin
            total_samples += n_bin
            
            print(f"   [{bin_centers[i]:.2f}, {bin_centers[i+1]:.2f}]: "
                  f"n={n_bin:3d}, Pred={bin_pred:.1%}, Actual={bin_actual:.1%}, "
                  f"Error={bin_error:.1%}")
    
    ece /= total_samples if total_samples > 0 else 1
    print(f"\n   Expected Calibration Error (ECE): {ece:.3f}")
    print(f"   (Lower is better, <0.05 is excellent)")
    
    # Calculate Brier score
    brier = np.mean((pred_probs - outcomes_valid) ** 2)
    print(f"   Brier Score: {brier:.3f} (Lower is better, <0.25 is good)")
    
    # Save calibrator
    output_file = Path(__file__).parent.parent / "artifacts" / f"spread_calibrator_{method}.pkl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'wb') as f:
        pickle.dump(calibrator, f)
    
    print(f"\n✅ Saved calibrator to: {output_file}")
    
    return calibrator


def fit_total_calibrator(method: str = 'isotonic'):
    """Fit calibrator for totals (same structure as spreads)."""
    print("="*70)
    print(f"FITTING TOTAL PROBABILITY CALIBRATOR ({method.upper()})")
    print("="*70)
    
    # Load backtest results
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        print(f"❌ Backtest file not found: {backtest_file}")
        return None
    
    df = pd.read_csv(backtest_file)
    
    # Check required columns (use raw_sd if available)
    if 'total_raw_sd' in df.columns:
        sd_col = 'total_raw_sd'
    elif 'total_sd' in df.columns:
        sd_col = 'total_sd'  # Fallback to centered SD
    else:
        print("❌ Need either total_raw_sd or total_sd column")
        return None
    
    required = ['total_raw', 'total_line', 'actual_home_score', 'actual_away_score']
    if not all(c in df.columns for c in required):
        print(f"❌ Missing required columns")
        return None
    
    # Filter to valid data
    df_valid = df[
        df['total_raw'].notna() & 
        df[sd_col].notna() &
        df['total_line'].notna() &
        df['actual_home_score'].notna() &
        df['actual_away_score'].notna()
    ].copy()
    
    print(f"✅ {len(df_valid)} games with valid data")
    
    # Calculate outcomes: did over hit?
    actual_totals = df_valid['actual_home_score'].values + df_valid['actual_away_score'].values
    market_totals = df_valid['total_line'].values
    
    # Over hits if (actual_total - market_total) > 0
    push_mask = np.abs(actual_totals - market_totals) < 0.01
    outcomes = (actual_totals - market_totals > 0).astype(float)
    outcomes[push_mask] = 0.5
    
    # Filter out pushes
    valid_mask = ~push_mask
    sim_totals = df_valid['total_raw'].values[valid_mask]
    sim_sds = df_valid[sd_col].values[valid_mask]
    market_totals_valid = market_totals[valid_mask]
    outcomes_valid = outcomes[valid_mask].astype(int)
    
    print(f"✅ {len(outcomes_valid)} games (excluding {push_mask.sum()} pushes)")
    print(f"   Over hits: {outcomes_valid.sum()} ({outcomes_valid.mean():.1%})")
    
    # Fit calibrator
    print(f"\n🔧 Fitting {method} calibrator...")
    calibrator = ProbabilityCalibrator(method=method, z_cap=3.0)
    calibrator.fit_from_historical(
        sim_totals, sim_sds, market_totals_valid, outcomes_valid
    )
    
    # Save
    output_file = Path(__file__).parent.parent / "artifacts" / f"total_calibrator_{method}.pkl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'wb') as f:
        pickle.dump(calibrator, f)
    
    print(f"\n✅ Saved calibrator to: {output_file}")
    
    return calibrator


if __name__ == "__main__":
    # Fit both calibrators
    print("\n" + "="*70)
    print("FITTING CALIBRATORS")
    print("="*70)
    
    # Try isotonic first (preferred)
    try:
        spread_cal = fit_spread_calibrator(method='isotonic')
        total_cal = fit_total_calibrator(method='isotonic')
    except Exception as e:
        print(f"\n⚠️  Isotonic failed: {e}")
        print("   Falling back to Platt scaling...")
        spread_cal = fit_spread_calibrator(method='platt')
        total_cal = fit_total_calibrator(method='platt')
    
    print("\n" + "="*70)
    print("✅ CALIBRATORS FITTED")
    print("="*70)
    print("\nNext steps:")
    print("1. Update generate_week9_predictions.py to use calibrators")
    print("2. Update backtest_all_games_conviction.py to use calibrators")
    print("3. Compare calibrated vs centered probabilities on test set")

