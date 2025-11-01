#!/usr/bin/env python3
"""
Fit isotonic calibrators using ONLY 2025 data (Weeks 1-8).

This accounts for the 2025 dynamic kickoff rule changes that increased scoring.
Replaces the old isotonic calibrators that were trained on ALL historical data.
"""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
import sys

# Import AdvancedProbabilityCalibrator
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from improve_calibration import AdvancedProbabilityCalibrator

print("=" * 80)
print("FITTING ISOTONIC CALIBRATORS (2025 DATA ONLY)")
print("=" * 80)
print()

# Load completed 2025 games
artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
backtest_file = artifacts_dir / "simulator_predictions.csv"

df = pd.read_csv(backtest_file)
df_2025 = df[(df['season'] == 2025) & (df['is_completed'] == True) & (df['week'] <= 8)].copy()

print(f"✅ Loaded {len(df_2025)} completed 2025 games (Weeks 1-8)")
print()

# Reconstruct raw simulator outputs if needed
if 'spread_raw' not in df_2025.columns:
    # Calculate from raw scores
    if 'our_home_score_raw' in df_2025.columns and 'our_away_score_raw' in df_2025.columns:
        df_2025['spread_raw'] = df_2025['our_home_score_raw'] - df_2025['our_away_score_raw']
        df_2025['total_raw'] = df_2025['our_home_score_raw'] + df_2025['our_away_score_raw']
        print("✅ Reconstructed spread_raw and total_raw from raw scores")
    else:
        # Fallback: use calibrated scores (not ideal but works)
        df_2025['spread_raw'] = df_2025['our_spread']
        df_2025['total_raw'] = df_2025['our_total']
        print("⚠️  Using calibrated scores as proxy for raw (not ideal)")

# Prepare spread data
print("📊 Preparing SPREAD calibration data...")
sim_spreads = df_2025['spread_raw'].values
# Use spread_std if available, fill NaN with default, otherwise use default
if 'spread_std' in df_2025.columns:
    sim_sds = df_2025['spread_std'].fillna(11.0).values
elif 'spread_raw_sd' in df_2025.columns:
    sim_sds = df_2025['spread_raw_sd'].fillna(11.0).values
else:
    sim_sds = np.full(len(df_2025), 11.0)
market_spreads = df_2025['closing_spread'].values

# Calculate outcomes (handle pushes)
actual_spreads = df_2025['actual_home_score'].values - df_2025['actual_away_score'].values
spread_outcomes = (actual_spreads > market_spreads).astype(float)
# Mark pushes as 0.5 (will be filtered out during training)
push_mask = np.abs(actual_spreads - market_spreads) < 0.1
spread_outcomes[push_mask] = 0.5

# Filter valid
valid_spread = ~(np.isnan(sim_spreads) | np.isnan(sim_sds) | np.isnan(market_spreads) | np.isnan(spread_outcomes))
sim_spreads = sim_spreads[valid_spread]
sim_sds = sim_sds[valid_spread]
market_spreads = market_spreads[valid_spread]
spread_outcomes = spread_outcomes[valid_spread]

print(f"   Valid samples: {len(sim_spreads)}")
print(f"   Pushes filtered: {np.sum(push_mask)}")
print()

# Fit spread calibrator
print("🔧 Fitting SPREAD isotonic calibrator...")
spread_calibrator = AdvancedProbabilityCalibrator(method='isotonic', z_cap=3.0)
spread_calibrator.fit_from_historical(
    sim_spreads, sim_sds, market_spreads, spread_outcomes
)
print(f"✅ Spread calibrator fitted")
print()

# Prepare total data
print("📊 Preparing TOTAL calibration data...")
sim_totals = df_2025['total_raw'].values
# Use total_std if available, fill NaN with default, otherwise use default
if 'total_std' in df_2025.columns:
    sim_total_sds = df_2025['total_std'].fillna(8.0).values
elif 'total_raw_sd' in df_2025.columns:
    sim_total_sds = df_2025['total_raw_sd'].fillna(8.0).values
else:
    sim_total_sds = np.full(len(df_2025), 8.0)
market_totals = df_2025['closing_total'].values

# Calculate outcomes (handle pushes)
actual_totals = df_2025['actual_home_score'].values + df_2025['actual_away_score'].values
total_outcomes = (actual_totals > market_totals).astype(float)
# Mark pushes as 0.5 (will be filtered out during training)
push_mask_total = np.abs(actual_totals - market_totals) < 0.5
total_outcomes[push_mask_total] = 0.5

# Filter valid
valid_total = ~(np.isnan(sim_totals) | np.isnan(sim_total_sds) | np.isnan(market_totals) | np.isnan(total_outcomes))
sim_totals = sim_totals[valid_total]
sim_total_sds = sim_total_sds[valid_total]
market_totals = market_totals[valid_total]
total_outcomes = total_outcomes[valid_total]

print(f"   Valid samples: {len(sim_totals)}")
print(f"   Pushes filtered: {np.sum(push_mask_total)}")
print()

# Fit total calibrator
print("🔧 Fitting TOTAL isotonic calibrator...")
total_calibrator = AdvancedProbabilityCalibrator(method='isotonic', z_cap=3.0)
total_calibrator.fit_from_historical(
    sim_totals, sim_total_sds, market_totals, total_outcomes
)
print(f"✅ Total calibrator fitted")
print()

# Evaluate calibrators
print("📈 Evaluating calibrators...")

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
print()

# Save calibrators (same format as original)
calibrators = {
    'spread': spread_calibrator,
    'total': total_calibrator,
    'fitted_on': '2025 Weeks 1-8',
    'n_games': len(df_2025),
    'date_fitted': pd.Timestamp.now().isoformat()
}

output_file = artifacts_dir / "isotonic_calibrators.pkl"
with open(output_file, 'wb') as f:
    pickle.dump(calibrators, f)

print("=" * 80)
print(f"✅ SAVED: {output_file}")
print("=" * 80)
print()
print("✅ The 2025-only isotonic calibrators are now active!")
print("   All future predictions will use these improved calibrators.")
print("   Re-generate predictions to see the improved results.")
print()
