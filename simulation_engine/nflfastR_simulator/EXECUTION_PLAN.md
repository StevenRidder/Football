# Execution Plan - Audit Fixes & Strategy Signals

**Date**: 2025-10-30  
**Status**: Ready to execute

## ✅ Completed Analysis

### 1. Strategy Signal Analysis
- **Result**: All 12 core signals from strategy doc are implemented ✅
- **Coverage**: 83% fully implemented, 11% partial, 6% missing
- **Missing**: Only situational factors (weather, rest days) need active integration

### 2. Calibration Test Results
- **Current**: Linear calibration shows good performance
  - Spread bets: 54.8% win rate, 9.5% ROI
  - Total bets: 59.1% win rate, 18.2% ROI
- **Issue**: Isotonic calibrators not used in backtest (needs re-run)

## 🎯 High Priority Execution Items

### Priority 1: Test Isotonic Calibrators ✅ READY
**Status**: Isotonic calibrators fitted and saved, but backtest hasn't used them yet

**Action Required**:
1. Re-run `backtest_all_games_conviction.py` to use isotonic calibrators
2. Compare ROI: isotonic vs linear
3. Verify `calibration_method` column shows 'isotonic'

**Expected Outcome**: 
- Isotonic should show better calibration (reliability curve)
- ROI may improve due to better probability estimates

**Command**: 
```bash
cd simulation_engine/nflfastR_simulator
python3 backtest_all_games_conviction.py
```

### Priority 2: Add Features to Score Calibration ✅ READY
**Status**: Script created but needs proper data merging

**Action Required**:
1. Fix data merging in `improve_score_calibration_features.py`
2. Merge situational factors (dome, rest days, weather)
3. Merge pace data
4. Refit score calibration models
5. Compare R² improvement

**Expected Outcome**:
- R² should improve from 0.1-0.2 to 0.25-0.35
- Better actual score predictions

**Command**:
```bash
cd simulation_engine/nflfastR_simulator
python3 scripts/improve_score_calibration_features.py
```

### Priority 3: Integrate Situational Factors ✅ PARTIAL
**Status**: Data loaded but not actively used in simulation

**Signals to Integrate**:
1. **Weather** (wind, precipitation)
   - Impact on passing efficiency
   - Impact on totals
   - **Implementation**: Adjust completion rate and YPA based on wind
   
2. **Rest Days**
   - Short week (< 7 days rest) = performance penalty
   - Bye week (> 7 days rest) = performance boost
   - **Implementation**: Adjust team efficiency by ±2-3%
   
3. **Dome**
   - Indoor = better passing conditions
   - **Implementation**: Small boost to passing efficiency

**Files to Modify**:
- `simulator/play_simulator.py` - Apply weather/rest adjustments
- `simulator/team_profile.py` - Already loads situational factors ✅

## 📋 Medium Priority Items

### 4. Compare Market-Centered vs Pure Prediction
**Action**: Set `USE_MARKET_CENTERING = False` in backtest and compare ROI

### 5. Regime-Specific Models
**Action**: Fit separate calibrators for indoor/outdoor, high/low totals

## 🚀 Execution Steps

### Step 1: Re-run Backtest with Isotonic (5 min)
```bash
cd simulation_engine/nflfastR_simulator
python3 backtest_all_games_conviction.py
python3 scripts/test_isotonic_vs_linear.py
```

### Step 2: Improve Score Calibration (15 min)
```bash
# Fix data merging first
python3 scripts/improve_score_calibration_features.py
```

### Step 3: Integrate Situational Factors (30 min)
- Modify `play_simulator.py` to use weather/rest/dome
- Test on sample games
- Verify impact

### Step 4: Validate Improvements (10 min)
- Run full backtest with all improvements
- Compare ROI vs baseline
- Check reliability curves

## 📊 Expected Impact

### Current Performance:
- Spread: 54.8% win rate, 9.5% ROI
- Totals: 59.1% win rate, 18.2% ROI

### Expected After Improvements:
- **Isotonic Calibration**: +1-2% ROI (better probability estimates)
- **Situational Factors**: +2-3% ROI (better total predictions)
- **Score Calibration**: Better actual score predictions (for validation)

### Target:
- Spread: 55-56% win rate, 11-12% ROI
- Totals: 60-61% win rate, 20-21% ROI

## ⚠️ Risks

1. **Overfitting**: Adding too many features could reduce OOS performance
2. **Data Quality**: Situational factors might have missing data
3. **Complexity**: More features = harder to debug

## ✅ Validation Checklist

After execution, verify:
- [ ] Isotonic calibrators are actually used in backtest
- [ ] Score calibration R² improved
- [ ] Situational factors show measurable impact
- [ ] ROI improved (or at least maintained)
- [ ] No regressions in existing functionality

