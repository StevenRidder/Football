"""
Fit isotonic calibrators for probability calibration (Priority 1 enhancement).

Uses z-scores: z = (sim_mean - market_line) / sim_sd
Maps z-scores to well-calibrated probabilities using isotonic regression.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.improve_calibration import AdvancedProbabilityCalibrator
import json

def load_backtest_data():
    """Load backtest with raw scores and actual outcomes."""
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        raise FileNotFoundError(f"Backtest file not found: {backtest_file}")
    
    df = pd.read_csv(backtest_file)
    completed = df[df['actual_home_score'].notna()].copy()
    
    print(f"✅ Loaded {len(completed)} completed games")
    return completed

def fit_isotonic_calibrators():
    """Fit isotonic calibrators for spreads and totals."""
    print("="*70)
    print("FITTING ISOTONIC CALIBRATORS")
    print("="*70)
    
    df = load_backtest_data()
    
    # Prepare spread data
    print(f"\n📊 Preparing spread calibration data...")
    sim_spreads = df['spread_raw'].values
    sim_sds = df.get('spread_raw_sd', df.get('spread_sd', np.full(len(df), 13.0))).values
    market_spreads = df['spread_line'].values
    spread_outcomes = (df['actual_spread'] > df['spread_line']).astype(float)
    spread_outcomes[abs(df['actual_spread'] - df['spread_line']) < 0.1] = 0.5  # Pushes
    
    # Filter valid
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
    
    # Filter valid
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
    
    # Evaluate calibrators
    print(f"\n📈 Evaluating calibrators...")
    
    # Spread predictions
    spread_probs = spread_calibrator.predict(sim_spreads, sim_sds, market_spreads)
    spread_valid_outcomes = spread_outcomes[spread_outcomes != 0.5]
    spread_valid_probs = spread_probs[spread_outcomes != 0.5]
    
    if len(spread_valid_outcomes) > 0:
        spread_mae = np.mean(np.abs(spread_valid_probs - spread_valid_outcomes))
        print(f"   Spread MAE: {spread_mae:.3f}")
        print(f"   Spread prob range: [{spread_probs.min():.3f}, {spread_probs.max():.3f}]")
    
    # Total predictions
    total_probs = total_calibrator.predict(sim_totals, sim_total_sds, market_totals)
    total_valid_outcomes = total_outcomes[total_outcomes != 0.5]
    total_valid_probs = total_probs[total_outcomes != 0.5]
    
    if len(total_valid_outcomes) > 0:
        total_mae = np.mean(np.abs(total_valid_probs - total_valid_outcomes))
        print(f"   Total MAE: {total_mae:.3f}")
        print(f"   Total prob range: [{total_probs.min():.3f}, {total_probs.max():.3f}]")
    
    # Save calibrators
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    calibrators = {
        'spread': spread_calibrator,
        'total': total_calibrator
    }
    
    with open(artifacts_dir / "isotonic_calibrators.pkl", 'wb') as f:
        pickle.dump(calibrators, f)
    
    print(f"\n💾 Saved isotonic calibrators to: {artifacts_dir / 'isotonic_calibrators.pkl'}")
    
    return calibrators

if __name__ == "__main__":
    calibrators = fit_isotonic_calibrators()
    print("\n✅ Isotonic calibrators fitted and saved!")
    print("\n📋 Next Steps:")
    print("   1. Update backtest_all_games_conviction.py to use isotonic calibrators")
    print("   2. Compare isotonic vs linear calibration performance")

