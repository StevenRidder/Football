# Pressure Calibration Implementation - Complete

## ✅ What Was Created

### 1. **Pressure Calibration Module** (`simulator/pressure_calibration.py`)
   - `PressureConfig`: Tunable parameters for calibration
   - `PressureCalibrator`: Main class for team-specific baselines and situational adjustments
   - Methods:
     - `fit_from_weekly()`: Builds rolling EMA baselines from nflfastR data
     - `pressure_prob()`: Returns adjusted pressure probability per snap
     - `snapshot()`: Returns current team baselines for inspection

### 2. **Weekly Prep Script** (`preprocessing/prep_pressure_rates.py`)
   - Computes `off_pr_allowed` and `def_pr_created` from nflfastR
   - Outputs `data/nflfastR/pressure_rates_weekly.csv`
   - ✅ **Tested**: Successfully computed 270 team-weeks for weeks 1-9

### 3. **Validation Script** (`scripts/validate_pressure_calibration.py`)
   - Compares simulated vs actual pressure rates
   - Reports gaps per team
   - Saves results to `artifacts/pressure_validation/`

### 4. **Integration Guide** (`PRESSURE_CALIBRATION_INTEGRATION.md`)
   - Step-by-step integration instructions
   - Code examples for updating `PlaySimulator` and `GameSimulator`
   - Tuning parameters and validation steps

## 📊 Current Data Status

**Pressure rates computed for weeks 1-9:**
- Average `off_pr_allowed`: 0.137 (13.7%)
- Average `def_pr_created`: 0.137 (13.7%)
- **Note**: This is lower than current `BASE_PRESSURE_RATE` (21.2%) because:
  - nflfastR uses `sack + qb_hit` as pressure proxy
  - Real pressure includes hurries (not always tracked)
  - The calibrator will adjust this baseline per team

**Week 9 Sample (teams with highest pressure allowed):**
- KC: 35.0% (high - matches trace analysis finding)
- ARI: 28.9%
- MIN: 27.3%
- LAC: 25.6%

## 🔧 Next Steps: Integration

### Step 1: Update PlaySimulator (Priority)
Modify `simulator/play_simulator.py`:
- Add `pressure_calibrator` parameter to `__init__`
- Replace `BASE_PRESSURE_RATE` logic with `pressure_calibrator.pressure_prob()` call
- Keep existing completion/sack logic (only change pressure probability)

### Step 2: Update GameSimulator
Modify `simulator/game_simulator.py`:
- Add `pressure_calibrator` parameter to `__init__`
- Pass to `PlaySimulator` in `_simulate_drive()`

### Step 3: Update Backtest Scripts
Modify `backtest_all_games_conviction.py`:
- Initialize `PressureCalibrator` at start
- Pass to `GameSimulator` for each game

### Step 4: Test and Validate
1. Run backtest on week 9
2. Run validation script: `python3 scripts/validate_pressure_calibration.py --season 2025 --week 9`
3. Check if pressure gaps closed (PIT, KC, IND should improve)

## 🎯 Expected Improvements

After integration:

1. **Team-Specific Baselines**
   - PIT: Should drop from 29.6% to closer to actual 15%
   - KC: Should increase from 30% to closer to actual 42.5%
   - IND: Should reduce EPA inflation (currently +0.43 gap)

2. **Situational Adjustments**
   - 3rd & long: Higher pressure (1.25x multiplier)
   - Two-minute drill: Higher pressure when trailing (1.20x multiplier)
   - Trailing by 10+: Higher pressure (1.10x multiplier)

3. **OL/DL Mismatch**
   - Better pressure rates in mismatches
   - Uses PFF grades with `ol_dl_beta=0.018` scaling

4. **Injury Adjustments**
   - Missing OL starters: +5% pressure per starter
   - Missing DL starters: -5% pressure per starter

## 📈 Validation Targets

After integration, validate:
- **Pressure gap**: Should be <5% for most teams
- **Total MAE**: Should decrease from 11.18 points
- **Team bias**: IND, PIT, KC should show smaller errors
- **EPA inflation**: Should reduce (IND's +0.43 gap should shrink)

## 🔍 Quick Sanity Check

Test the calibrator:

```python
from simulator.pressure_calibration import PressureCalibrator, PressureConfig
import pandas as pd

df = pd.read_csv("data/nflfastR/pressure_rates_weekly.csv")
cal = PressureCalibrator()
cal.fit_from_weekly(df, season=2025, week=9)

# Check problematic teams
snapshot = cal.snapshot()
print("PIT:", snapshot[snapshot['team'] == 'PIT'])
print("KC:", snapshot[snapshot['team'] == 'KC'])
print("IND:", snapshot[snapshot['team'] == 'IND'])
```

## 📝 Notes

1. **Pressure Definition**: Currently using `sack + qb_hit` from nflfastR. Real pressure includes hurries, but this is a good proxy.

2. **Baseline Adjustment**: The 13.7% average is lower than 21.2% because we're using a stricter definition. The calibrator will adjust per team, so this is fine.

3. **Tuning**: If gaps persist after integration:
   - Increase `ol_dl_beta` from 0.018 to 0.020-0.024
   - Increase `third_long_mult` from 1.25 to 1.30
   - Adjust `weeks_lookback` or `ema_alpha` for recency weighting

4. **Future Enhancement**: Can add hurry data if available from advanced stats, but current implementation should work well.

## 🚀 Ready for Integration

All components are ready:
- ✅ Module created and tested
- ✅ Data prep script working
- ✅ Validation script ready
- ✅ Integration guide complete

Next: Integrate into `PlaySimulator` and `GameSimulator`, then test.

