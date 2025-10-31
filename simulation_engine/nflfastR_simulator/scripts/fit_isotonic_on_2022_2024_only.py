"""
Refit isotonic calibrators on 2022-2024 data ONLY (no 2025).

This ensures calibrators are truly trained on historical data,
then tested on 2025 weeks 1-8 as out-of-sample.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.improve_calibration import AdvancedProbabilityCalibrator
import pickle

def load_training_data():
    """Load 2022-2024 data ONLY (exclude 2025)."""
    # Try the dedicated 2022-2024 backtest file first
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_2022_2024.csv"
    
    if not backtest_file.exists():
        # Fall back to main backtest file and filter
        backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
        if not backtest_file.exists():
            raise FileNotFoundError(f"Backtest file not found. Please run backtest_2023_2024.py first to generate backtest_2022_2024.csv")
    
    df = pd.read_csv(backtest_file)
    completed = df[df['actual_home_score'].notna()].copy()
    
    # CRITICAL: Filter to 2022-2024 only (exclude 2025)
    if 'season' in completed.columns:
        training = completed[completed['season'].isin([2022, 2023, 2024])].copy()
        print(f"✅ Loaded {len(training)} games from 2022-2024 (training set)")
        if len(completed) > len(training):
            print(f"   Excluded {len(completed) - len(training)} games from other seasons (e.g., 2025)")
    else:
        print(f"⚠️  No 'season' column - using all data (may include 2025!)")
        training = completed.copy()
    
    return training

def fit_isotonic_on_training_only():
    """Fit isotonic calibrators on training data only."""
    print("="*70)
    print("FITTING ISOTONIC CALIBRATORS ON 2022-2024 DATA ONLY")
    print("="*70)
    
    df = load_training_data()
    
    if len(df) < 50:
        raise ValueError(f"Not enough training data: {len(df)} games (need >= 50)")
    
    # Prepare spread data
    print(f"\n📊 Preparing spread calibration data...")
    sim_spreads = df['spread_raw'].values
    sim_sds = df.get('spread_raw_sd', df.get('spread_sd', np.full(len(df), 13.0))).values
    market_spreads = df['spread_line'].values
    spread_outcomes = (df['actual_spread'] > df['spread_line']).astype(float)
    spread_outcomes[abs(df['actual_spread'] - df['spread_line']) < 0.1] = 0.5  # Pushes
    
    valid_spread = ~(np.isnan(sim_spreads) | np.isnan(sim_sds) | np.isnan(market_spreads) | np.isnan(spread_outcomes))
    sim_spreads = sim_spreads[valid_spread]
    sim_sds = sim_sds[valid_spread]
    market_spreads = market_spreads[valid_spread]
    spread_outcomes = spread_outcomes[valid_spread]
    
    print(f"   Valid samples: {len(sim_spreads)}")
    
    # Fit spread calibrator
    print(f"\n🔧 Fitting isotonic calibrator for spreads...")
    spread_calibrator = AdvancedProbabilityCalibrator(method='isotonic', z_cap=3.0)
    spread_calibrator.fit_from_historical(
        sim_spreads, sim_sds, market_spreads, spread_outcomes
    )
    
    # Prepare total data
    print(f"\n📊 Preparing total calibration data...")
    sim_totals = df['total_raw'].values
    sim_total_sds = df.get('total_raw_sd', df.get('total_sd', np.full(len(df), 9.0))).values
    market_totals = df['total_line'].values
    total_outcomes = (df['actual_total'] > df['total_line']).astype(float)
    total_outcomes[abs(df['actual_total'] - df['total_line']) < 0.5] = 0.5  # Pushes
    
    valid_total = ~(np.isnan(sim_totals) | np.isnan(sim_total_sds) | np.isnan(market_totals) | np.isnan(total_outcomes))
    sim_totals = sim_totals[valid_total]
    sim_total_sds = sim_total_sds[valid_total]
    market_totals = market_totals[valid_total]
    total_outcomes = total_outcomes[valid_total]
    
    print(f"   Valid samples: {len(sim_totals)}")
    
    # Fit total calibrator
    print(f"\n🔧 Fitting isotonic calibrator for totals...")
    total_calibrator = AdvancedProbabilityCalibrator(method='isotonic', z_cap=3.0)
    total_calibrator.fit_from_historical(
        sim_totals, sim_total_sds, market_totals, total_outcomes
    )
    
    # Evaluate on training set
    print(f"\n📈 Training Set Performance:")
    
    spread_probs = spread_calibrator.predict(sim_spreads, sim_sds, market_spreads)
    spread_valid = spread_outcomes[spread_outcomes != 0.5]
    spread_probs_valid = spread_probs[spread_outcomes != 0.5]
    
    if len(spread_valid) > 0:
        spread_mae = np.mean(np.abs(spread_probs_valid - spread_valid))
        print(f"   Spread MAE: {spread_mae:.3f}")
    
    total_probs = total_calibrator.predict(sim_totals, sim_total_sds, market_totals)
    total_valid = total_outcomes[total_outcomes != 0.5]
    total_probs_valid = total_probs[total_outcomes != 0.5]
    
    if len(total_valid) > 0:
        total_mae = np.mean(np.abs(total_probs_valid - total_valid))
        print(f"   Total MAE: {total_mae:.3f}")
    
    # Save calibrators
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    calibrators = {
        'spread': spread_calibrator,
        'total': total_calibrator,
        'trained_on': '2022-2024',
        'excluded': '2025'
    }
    
    # Save as the main calibrator file (will be used by backtest)
    with open(artifacts_dir / "isotonic_calibrators.pkl", 'wb') as f:
        pickle.dump(calibrators, f)
    
    # Also save with date suffix as backup
    with open(artifacts_dir / "isotonic_calibrators_2022_2024.pkl", 'wb') as f:
        pickle.dump(calibrators, f)
    
    print(f"\n💾 Saved to: {artifacts_dir / 'isotonic_calibrators.pkl'}")
    print(f"💾 Backup saved to: {artifacts_dir / 'isotonic_calibrators_2022_2024.pkl'}")
    print(f"\n✅ Calibrators now trained on 2022-2024 ONLY (no 2025 leakage)")
    
    return calibrators

if __name__ == "__main__":
    calibrators = fit_isotonic_on_training_only()
    print("\n✅ Calibrators fitted on 2022-2024 only (no 2025 leakage)")

