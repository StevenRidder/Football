# Pressure Calibration Integration Guide

This guide walks through integrating team-specific pressure calibration into the simulator.

## Overview

The pressure calibration system replaces the single `BASE_PRESSURE_RATE` (21.2%) with:
1. **Team-specific baselines** from rolling nflfastR data
2. **OL vs DL mismatch adjustments** using PFF grades
3. **Situational multipliers** (3rd & long, two-minute drill, etc.)
4. **Injury adjustments**

## Step 1: Compute Weekly Pressure Rates

Run this weekly to compute pressure baselines from nflfastR:

```bash
cd simulation_engine/nflfastR_simulator
python3 preprocessing/prep_pressure_rates.py --season 2025 --week 9
```

This creates: `data/nflfastR/pressure_rates_weekly.csv`

**Output format:**
```
team,season,week,off_pr_allowed,def_pr_created,dropbacks,pressures_allowed,...
```

## Step 2: Initialize Pressure Calibrator

In your weekly data prep or game simulation setup:

```python
from simulator.pressure_calibration import PressureCalibrator, PressureConfig
import pandas as pd

# Load weekly pressure rates
pressure_df = pd.read_csv("data/nflfastR/pressure_rates_weekly.csv")

# Initialize calibrator
cal = PressureCalibrator(PressureConfig(
    weeks_lookback=5,
    ema_alpha=0.45,
    ol_dl_beta=0.018  # Tune this if pressure gaps persist
))

# Fit to current week
cal.fit_from_weekly(pressure_df, season=2025, week=9)

# Optional: Save snapshot for inspection
cal.snapshot().to_csv("artifacts/pressure_baselines_week9.csv", index=False)
```

## Step 3: Update PlaySimulator

Modify `simulator/play_simulator.py` to accept and use the calibrator:

```python
class PlaySimulator:
    def __init__(self, offense: TeamProfile, defense: TeamProfile, 
                 trace: Optional[SimTrace] = None,
                 pressure_calibrator: Optional[PressureCalibrator] = None):
        self.offense = offense
        self.defense = defense
        self.trace = trace
        self.pressure_calibrator = pressure_calibrator  # NEW
        
    def simulate_pass_play(self, game_state: GameState) -> Dict:
        # Step 1: Determine if pressure occurs
        if self.pressure_calibrator:
            # Use new calibration system
            pressure_rate = self.pressure_calibrator.pressure_prob(
                offense_team=self.offense.team,
                defense_team=self.defense.team,
                down=game_state.down,
                ydstogo=game_state.ydstogo,
                quarter=game_state.quarter,
                sec_left_in_quarter=game_state.time_remaining % 900,  # seconds in current quarter
                offense_trailing_by=game_state.score_differential if game_state.possession == 'away' else -game_state.score_differential,
                half=1 if game_state.quarter <= 2 else 2,
                play_action=False,  # TODO: Track from play-calling
                shotgun=False,  # TODO: Track from play-calling
                injuries={
                    'OL': {'starters_out': getattr(self.offense, 'ol_starters_out', 0)},
                    'DL': {'starters_out': getattr(self.defense, 'dl_starters_out', 0)}
                },
                ol_rank=getattr(self.offense, 'ol_rank', None),  # Optional: PFF rank
                dl_rank=getattr(self.defense, 'dl_rank', None),  # Optional: PFF rank
            )
        else:
            # Fallback to old system
            pressure_rate = self.BASE_PRESSURE_RATE
            # ... existing PFF adjustments ...
        
        is_pressure = np.random.random() < pressure_rate
        # ... rest of pass simulation ...
```

## Step 4: Update GameSimulator

Modify `simulator/game_simulator.py` to initialize and pass the calibrator:

```python
class GameSimulator:
    def __init__(self, home_team: TeamProfile, away_team: TeamProfile,
                 game_id: str = None, season: int = None, week: int = None,
                 trace: Optional[SimTrace] = None, seed: Optional[int] = None,
                 pressure_calibrator: Optional[PressureCalibrator] = None):  # NEW
        # ... existing init ...
        self.pressure_calibrator = pressure_calibrator  # NEW
        
    def _simulate_drive(self, game_state: GameState, offense: TeamProfile, defense: TeamProfile):
        play_sim = PlaySimulator(
            offense, 
            defense, 
            trace=self.trace,
            pressure_calibrator=self.pressure_calibrator  # NEW
        )
        # ... rest of drive simulation ...
```

## Step 5: Initialize in Backtest/Prediction Scripts

Update `backtest_all_games_conviction.py` or `scripts/generate_week9_10_predictions.py`:

```python
from simulator.pressure_calibration import PressureCalibrator, PressureConfig

# At the top of your script, after loading data
def get_pressure_calibrator(season: int, week: int) -> Optional[PressureCalibrator]:
    """Initialize pressure calibrator for current week."""
    pressure_file = Path("data/nflfastR/pressure_rates_weekly.csv")
    
    if not pressure_file.exists():
        print("⚠️  Pressure rates file not found. Run prep_pressure_rates.py first.")
        return None
    
    pressure_df = pd.read_csv(pressure_file)
    cal = PressureCalibrator(PressureConfig(
        weeks_lookback=5,
        ema_alpha=0.45,
        ol_dl_beta=0.018
    ))
    cal.fit_from_weekly(pressure_df, season=season, week=week)
    
    return cal

# In your simulation function
pressure_cal = get_pressure_calibrator(season=2025, week=9)

simulator = GameSimulator(
    home_team=home_profile,
    away_team=away_profile,
    season=season,
    week=week,
    pressure_calibrator=pressure_cal  # NEW
)
```

## Step 6: Validate Pressure Calibration

After running simulations, validate against actuals:

```bash
python3 scripts/validate_pressure_calibration.py --season 2025 --week 9
```

This will:
1. Load actual pressure rates from nflfastR
2. Load simulated pressure rates from traces
3. Compare and report gaps
4. Save results to `artifacts/pressure_validation/`

## Expected Improvements

After implementing:

1. **Team-specific baselines** → Fixes PIT (29.6% → 15%), KC (30% → 42.5%), IND overrating
2. **Situational multipliers** → Reduces "perfect drives" in obvious passing situations
3. **OL/DL mismatch** → Better pressure rates in mismatches
4. **Injury adjustments** → More realistic pressure when starters are out

## Tuning Parameters

If pressure gaps persist after implementation:

1. **`ol_dl_beta`**: Increase from 0.018 to 0.020-0.024 if mismatch effects are too weak
2. **`third_long_mult`**: Increase from 1.25 to 1.30 if long-yardage pressure is still low
3. **`weeks_lookback`**: Decrease from 5 to 3 if you want more recent form weighting
4. **`ema_alpha`**: Increase from 0.45 to 0.60 if you want more recency weighting

## Quick Test

Run a quick sanity check:

```python
from simulator.pressure_calibration import PressureCalibrator, PressureConfig
import pandas as pd

# Load data
df = pd.read_csv("data/nflfastR/pressure_rates_weekly.csv")
cal = PressureCalibrator()
cal.fit_from_weekly(df, season=2025, week=9)

# Check baseline snapshots
snapshot = cal.snapshot()
print("Team Baselines:")
print(snapshot.sort_values('off_pr_allowed', ascending=False).head(10))

# Test a specific situation
p = cal.pressure_prob(
    offense_team='IND',
    defense_team='PIT',
    down=3,
    ydstogo=10,
    quarter=2,
    sec_left_in_quarter=90,
    offense_trailing_by=7,
    half=1,
    play_action=False,
    shotgun=True
)
print(f"\nIND @ PIT, 3rd & 10, trailing by 7: {p:.3f} pressure prob")
```

## Next Steps

Once pressure calibration is working:
1. Implement **defensive variance damping** (next improvement)
2. Add **red zone efficiency modeling**
3. Improve **4th down decision model**

