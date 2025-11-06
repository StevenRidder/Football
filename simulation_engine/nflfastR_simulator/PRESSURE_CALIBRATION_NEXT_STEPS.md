# Pressure Calibration - Integration Complete ✅

## What Was Done

### 1. **Updated PlaySimulator** (`simulator/play_simulator.py`)
   - ✅ Added `pressure_calibrator` parameter to `__init__`
   - ✅ Replaced `BASE_PRESSURE_RATE` logic with calibrated system when available
   - ✅ Falls back to old system if calibrator not provided (backward compatible)
   - ✅ Enhanced logging with new pressure calculation details

### 2. **Updated GameSimulator** (`simulator/game_simulator.py`)
   - ✅ Added `pressure_calibrator` parameter to `__init__`
   - ✅ Passes calibrator to `PlaySimulator` in `_simulate_drive()`

### 3. **Updated Backtest Script** (`backtest_all_games_conviction.py`)
   - ✅ Initializes `PressureCalibrator` inside `simulate_one_game()`
   - ✅ Loads pressure rates from `data/nflfastR/pressure_rates_weekly.csv`
   - ✅ Fits calibrator to current week before simulation
   - ✅ Gracefully falls back if pressure file not found

## Testing the Integration

### Step 1: Ensure Pressure Rates Are Computed

```bash
cd simulation_engine/nflfastR_simulator
python3 preprocessing/prep_pressure_rates.py --season 2025 --week 9
```

This creates: `data/nflfastR/pressure_rates_weekly.csv`

### Step 2: Run a Quick Test

```bash
# Test with a single game
python3 -c "
from simulator.team_profile import TeamProfile
from simulator.game_simulator import GameSimulator
from simulator.pressure_calibration import PressureCalibrator, PressureConfig
import pandas as pd
from pathlib import Path

data_dir = Path('data/nflfastR')
pressure_df = pd.read_csv(data_dir / 'pressure_rates_weekly.csv')

cal = PressureCalibrator()
cal.fit_from_weekly(pressure_df, season=2025, week=9)

home = TeamProfile('KC', 2025, 9, data_dir)
away = TeamProfile('BUF', 2025, 9, data_dir)

sim = GameSimulator(home, away, season=2025, week=9, pressure_calibrator=cal)
result = sim.simulate_game()
print(f'Result: {away.team} {result[\"away_score\"]}, {home.team} {result[\"home_score\"]}')"
```

### Step 3: Run Full Backtest

```bash
python3 backtest_all_games_conviction.py
```

The backtest will automatically:
1. Load pressure rates for each week
2. Initialize calibrator per game
3. Use calibrated pressure rates in simulation

### Step 4: Validate Pressure Calibration

After running simulations, validate:

```bash
python3 scripts/validate_pressure_calibration.py --season 2025 --week 9
```

This compares simulated vs actual pressure rates.

## Expected Improvements

After integration, you should see:

1. **Reduced Pressure Gaps**
   - PIT: Should drop from 29.6% → closer to 15% actual
   - KC: Should increase from 30% → closer to 42.5% actual
   - IND: Should reduce EPA inflation (+0.43 gap should shrink)

2. **Better Total MAE**
   - Current: 11.18 points
   - Target: <10 points (8-10% improvement)

3. **Fewer Team-Specific Biases**
   - IND, CIN, SF, NYJ should show smaller prediction errors
   - Team bias tails should narrow

4. **More Realistic Situational Pressure**
   - 3rd & long: Higher pressure (1.25x multiplier)
   - Two-minute drill: Higher pressure when trailing (1.20x multiplier)
   - Trailing by 10+: Higher pressure (1.10x multiplier)

## Tuning Parameters

If pressure gaps persist after testing:

1. **`ol_dl_beta`**: Increase from 0.018 to 0.020-0.024
   ```python
   PressureConfig(ol_dl_beta=0.022)
   ```

2. **`third_long_mult`**: Increase from 1.25 to 1.30
   ```python
   PressureConfig(third_long_mult=1.30)
   ```

3. **`weeks_lookback`**: Decrease from 5 to 3 for more recent form
   ```python
   PressureConfig(weeks_lookback=3)
   ```

4. **`ema_alpha`**: Increase from 0.45 to 0.60 for more recency
   ```python
   PressureConfig(ema_alpha=0.60)
   ```

## Next Improvements (After Validation)

Once pressure calibration is validated:

1. **Defensive Variance Damping** (Improvement #2)
   - Drive-to-drive defensive reset
   - Rising stop probability after consecutive first downs

2. **Red Zone Efficiency** (Improvement #3)
   - Team-specific red zone TD rates
   - Lower completion/explosive rates inside the 20

3. **4th Down Decisions** (Improvement #4)
   - Use actual conversion rates by distance
   - Win probability-based decisions

4. **Opponent Adjustment** (Improvement #5)
   - Strength of schedule corrections
   - Weekly re-computation

## Files Modified

- ✅ `simulator/play_simulator.py` - Integrated pressure calibrator
- ✅ `simulator/game_simulator.py` - Passes calibrator to PlaySimulator
- ✅ `backtest_all_games_conviction.py` - Initializes calibrator per game

## Files Created

- ✅ `simulator/pressure_calibration.py` - Main calibration module
- ✅ `preprocessing/prep_pressure_rates.py` - Weekly data prep script
- ✅ `scripts/validate_pressure_calibration.py` - Validation tool
- ✅ `PRESSURE_CALIBRATION_INTEGRATION.md` - Integration guide
- ✅ `PRESSURE_CALIBRATION_IMPLEMENTATION.md` - Implementation summary

## Ready to Test

All integration is complete. Next steps:

1. Run `prep_pressure_rates.py` to ensure data is ready
2. Run a quick test game
3. Run full backtest
4. Validate with `validate_pressure_calibration.py`
5. Compare results to baseline (should see improvement in total MAE and team biases)

