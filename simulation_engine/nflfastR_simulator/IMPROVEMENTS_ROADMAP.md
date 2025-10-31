# Model Improvement Roadmap

## ✅ Completed

1. **Linear Calibration** - Implemented with raw SD preservation
2. **Conviction Thresholds** - Adjusted to 6%/3% for better distribution
3. **Backtest Scripts** - Created for 2023-2024 seasons

## 🚧 In Progress

### 1. Non-Linear Calibration (Isotonic/Spline)
**Status:** Tools created, ready to fit
**File:** `scripts/improve_calibration.py`
**Next Steps:**
- Fit isotonic calibrator on 2022-2024 data
- Compare to linear calibration on 2025 OOS test
- If better, integrate into backtest scripts

**Usage:**
```python
from scripts.improve_calibration import AdvancedProbabilityCalibrator
calibrator = AdvancedProbabilityCalibrator(method='isotonic')
calibrator.fit_from_historical(sim_spreads, sim_sds, market_spreads, outcomes)
probs = calibrator.predict(sim_spreads, sim_sds, market_spreads)
```

### 2. Feature Refinement for Totals
**Status:** Data exists, need to apply in calibration
**Files:**
- Pace: `data/nflfastR/team_pace.csv` (already loaded in TeamProfile)
- Weather: `data/nflfastR/situational_factors.csv` (already loaded)
- Injuries: Need to add ESPN API integration

**Next Steps:**
- Add pace feature to total calibration (fast/fast = higher total)
- Add weather feature (cold/wind = lower total)
- Add injury tags (QB out, WR1 out = adjust totals)
- Refit calibration with these features

**Implementation Plan:**
1. Create `scripts/enhance_totals_features.py`
2. Extract pace mismatch (fast team vs slow team)
3. Extract weather impact (temp, wind, dome)
4. Extract injury impact (ESPN API)
5. Feed as features into totals calibrator

### 3. Regime-Specific Models
**Status:** Framework created, ready to use
**File:** `scripts/improve_calibration.py` (RegimeIdentifier class)
**Next Steps:**
- Fit separate calibrators for:
  - Indoor vs Outdoor games
  - High total (>45) vs Low total (<45)
  - Combined (4 regimes: indoor/high, indoor/low, outdoor/high, outdoor/low)

**Usage:**
```python
from scripts.improve_calibration import AdvancedProbabilityCalibrator, RegimeIdentifier

# Identify regimes
regimes = RegimeIdentifier.identify_combined_regime(totals, is_dome)

# Fit with regime splitting
calibrator = AdvancedProbabilityCalibrator(method='isotonic', regime_col='combined')
calibrator.fit_from_historical(sim_totals, sim_sds, market_totals, outcomes, regime_values=regimes)
```

### 4. Dynamic Bet Sizing (Fractional Kelly)
**Status:** Implementation complete
**File:** `scripts/improve_calibration.py` (FractionalKelly class)
**Next Steps:**
- Integrate into backtest to see impact on ROI
- Start with fraction=0.25 (quarter Kelly)
- Test different fractions (0.1, 0.25, 0.5)

**Usage:**
```python
from scripts.improve_calibration import FractionalKelly

kelly = FractionalKelly(fraction=0.25, bankroll=1000.0)
bet_size = kelly.calculate_bet_size(win_prob=0.60, edge=0.076)
# Result: ~$22.80 (quarter Kelly on 7.6% edge)
```

### 5. Walk-Forward Refresh
**Status:** Framework created
**File:** `scripts/improve_calibration.py` (WalkForwardRefresher class)
**Next Steps:**
- Implement in prediction pipeline
- Refit every 4 weeks on rolling 8-week window
- Track calibration drift over time

**Usage:**
```python
from scripts.improve_calibration import WalkForwardRefresher

refresher = WalkForwardRefresher(refit_frequency=4)
if refresher.should_refit(current_week=9, historical_weeks=[1,2,3,4,5,6,7,8]):
    start_week, end_week = refresher.get_training_window(9, lookback_weeks=8)
    # Refit calibrator on weeks start_week to end_week
```

### 6. Validation Checklist
**Status:** Complete tool created
**File:** `scripts/validation_checklist.py`
**Next Steps:**
- Run validation on current model
- Establish baseline metrics
- Track improvements as we add features

**Usage:**
```python
from scripts.validation_checklist import ModelValidator

validator = ModelValidator()
results = validator.validate_model(predicted_probs, actual_outcomes, "Model Name")
validator.print_validation_report(results)
validator.plot_reliability(results, save_path="reliability.png")
```

## 📋 Implementation Priority

### Priority 1 (Quick Wins):
1. **Non-linear calibration** - Fit isotonic, compare to linear
2. **Validation checklist** - Establish baseline, run on current model
3. **Regime-specific models** - Split indoor/outdoor, high/low totals

### Priority 2 (Medium Effort):
4. **Feature refinement for totals** - Add pace, weather, injuries
5. **Dynamic bet sizing** - Test impact on ROI

### Priority 3 (Ongoing):
6. **Walk-forward refresh** - Integrate into production pipeline

## 🎯 Success Criteria

### Reliability:
- ECE < 0.02
- Slope ≈ 1.0 (±0.1)
- Intercept ≈ 0.0 (±0.05)

### Sharpness:
- Concentration around 0.5 < 40%
- Mean distance from 0.5 > 0.10
- Std > 0.08

### Scoring:
- Log-loss improvement ≥ 10% vs baseline
- Brier improvement ≥ 10% vs baseline

### ROI:
- HIGH conviction: ≥ 5% ROI
- Overall: ≥ 4% ROI (target)
- OOS (2025): Positive ROI

## 📝 Notes

- All improvements should be tested on 2022-2024 data first
- Final validation on 2025 OOS (weeks 1-8)
- Track all changes in version control
- Document performance impact of each improvement

