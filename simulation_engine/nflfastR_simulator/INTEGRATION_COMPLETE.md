# Pressure Calibration Integration - Complete ✅

## Summary

Pressure calibration has been successfully integrated into the simulator. The system now uses team-specific pressure baselines with situational adjustments instead of a single global rate.

## What Changed

### Core Simulator Files
1. **`simulator/play_simulator.py`**
   - Added `pressure_calibrator` parameter
   - New pressure calculation uses team baselines + situational multipliers
   - Falls back to old system if calibrator not provided (backward compatible)

2. **`simulator/game_simulator.py`**
   - Added `pressure_calibrator` parameter
   - Passes calibrator to `PlaySimulator`

### Backtest & Prediction Scripts
3. **`backtest_all_games_conviction.py`**
   - Initializes pressure calibrator per game
   - Loads from `data/nflfastR/pressure_rates_weekly.csv`

4. **`scripts/generate_week9_10_predictions.py`**
   - Initializes pressure calibrator per game
   - Uses same calibration system

### New Files Created
5. **`simulator/pressure_calibration.py`** - Main calibration module
6. **`preprocessing/prep_pressure_rates.py`** - Weekly data prep
7. **`scripts/validate_pressure_calibration.py`** - Validation tool
8. **Integration guides** - Documentation

## How It Works

### Weekly Data Prep
```bash
python3 preprocessing/prep_pressure_rates.py --season 2025 --week 9
```
- Computes `off_pr_allowed` and `def_pr_created` from nflfastR
- Saves to `data/nflfastR/pressure_rates_weekly.csv`

### During Simulation
1. Backtest/prediction script loads pressure rates CSV
2. Initializes `PressureCalibrator` and fits to current week
3. Passes calibrator to `GameSimulator`
4. `GameSimulator` passes to `PlaySimulator`
5. `PlaySimulator` uses calibrated pressure rates per snap

### Per-Snap Calculation
The calibrator computes pressure probability using:
- **Team baselines**: Rolling EMA of offensive/defensive pressure rates
- **OL/DL mismatch**: PFF grade adjustments
- **Situational multipliers**:
  - 3rd & long: 1.25x
  - Two-minute drill (trailing): 1.20x
  - Trailing by 10+ (2H): 1.10x
  - Play-action: 0.90x (reduces pressure)
  - Shotgun: 1.05x (increases pressure)
- **Injury adjustments**: +5% per missing OL starter, -5% per missing DL starter

## Testing

### Quick Test
```python
from simulator.pressure_calibration import PressureCalibrator, PressureConfig
import pandas as pd

df = pd.read_csv("data/nflfastR/pressure_rates_weekly.csv")
cal = PressureCalibrator()
cal.fit_from_weekly(df, season=2025, week=9)

# Check baselines
print(cal.snapshot().sort_values('off_pr_allowed', ascending=False))
```

### Validation
After running simulations:
```bash
python3 scripts/validate_pressure_calibration.py --season 2025 --week 9
```

## Expected Improvements

1. **Team-Specific Pressure Rates**
   - PIT: 29.6% → ~15% (matches actual)
   - KC: 30% → ~42.5% (matches actual)
   - IND: Reduced EPA inflation

2. **Total MAE**
   - Current: 11.18 points
   - Target: <10 points (8-10% improvement)

3. **Team Bias Reduction**
   - IND, CIN, SF, NYJ should show smaller errors
   - Fewer extreme prediction errors

4. **Situational Realism**
   - Higher pressure in obvious passing situations
   - Better late-game simulation

## Next Steps

1. **Test the integration**:
   - Run `prep_pressure_rates.py` for weeks 1-9
   - Run backtest on week 9
   - Validate pressure rates

2. **If pressure gaps persist**:
   - Tune `ol_dl_beta` (0.018 → 0.020-0.024)
   - Tune `third_long_mult` (1.25 → 1.30)
   - Adjust `weeks_lookback` or `ema_alpha`

3. **After validation**:
   - Move to **Improvement #2: Defensive Variance Damping**
   - Then **Improvement #3: Red Zone Efficiency**

## Files Ready

- ✅ All code integrated
- ✅ Backward compatible (falls back if calibrator unavailable)
- ✅ Ready to test
- ✅ Documentation complete
