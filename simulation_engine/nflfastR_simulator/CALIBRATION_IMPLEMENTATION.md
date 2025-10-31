# Calibration Implementation Summary

## ✅ What's Been Implemented

### 1. Core Calibration Module (`simulator/probability_calibration.py`)

- **Z-score features**: `z = (sim_mean - market) / sim_sd` (normalized, scale-aware)
- **Isotonic regression** (preferred): Monotone mapping, fewer assumptions
- **Platt scaling** (fallback): Logistic regression with regularization
- **Adaptive ensemble**: Blends to 0.50 (not 0.524!), with α as function of |z|
- **Z-score capping**: Clips |z| at 3.0 to avoid instability
- **Separate calibrators**: Spread and totals handled independently

### 2. Fitting Script (`scripts/fit_calibrator.py`)

- Loads backtest results with raw spreads/SDs and actual outcomes
- Calculates z-scores automatically
- Fits isotonic (preferred) or Platt (fallback)
- **Reliability diagnostics**: ECE (Expected Calibration Error) and Brier score
- Excludes pushes from training
- Saves separate calibrators for spreads and totals

### 3. Backtest Updates (`backtest_all_games_conviction.py`)

- Now outputs:
  - `spread_raw`, `spread_raw_sd` (pre-centered)
  - `total_raw`, `total_raw_sd` (pre-centered)
  - `spread_mean`, `spread_sd` (centered - for display)
  - `total_mean`, `total_sd` (centered - for display)

### 4. Prediction Script Updates (`scripts/generate_week9_predictions.py`)

- Stores both centered and raw scores
- Ready to use calibrated probabilities (when calibrators are fitted)
- Currently uses centered probabilities (will switch once calibrators are fitted)

## 🔄 Next Steps

### Step 1: Re-run Backtest to Get Raw SDs
```bash
cd simulation_engine/nflfastR_simulator
python3 backtest_all_games_conviction.py
```

This will generate `backtest_all_games_conviction.csv` with:
- `spread_raw`, `spread_raw_sd`
- `total_raw`, `total_raw_sd`

### Step 2: Fit Calibrators
```bash
python3 scripts/fit_calibrator.py
```

This will:
- Fit isotonic calibrator for spreads (preferred)
- Fit isotonic calibrator for totals
- Show reliability diagnostics (ECE, Brier)
- Save to `artifacts/spread_calibrator_isotonic.pkl` and `total_calibrator_isotonic.pkl`

### Step 3: Update Prediction Scripts to Use Calibration

Once calibrators are fitted, update:
- `generate_week9_predictions.py`: Load calibrators and use for betting decisions
- `backtest_all_games_conviction.py`: Use calibration for probabilities

### Step 4: Compare Methods

After fitting, compare:
- **Current (centered)**: Probabilities from centered distribution
- **Calibrated**: Probabilities from z-score calibration
- **Ensemble**: Calibrated + adaptive blending to 0.50

## 📊 Key Improvements Over Original Approach

1. **Z-scores instead of raw deltas**: Scale-aware, normalizes by simulator SD
2. **Isotonic over logistic**: Monotone mapping, better reliability
3. **Blend to 0.50, not 0.524**: Market neutral, not house vig baseline
4. **Adaptive α**: Higher confidence (|z|) → more model weight
5. **Separate calibrators**: Spreads and totals handled independently
6. **Proper push handling**: Excluded from training, handled at inference
7. **Reliability diagnostics**: ECE and Brier score for validation

## 🎯 Expected Outcomes

- **Better calibration**: ECE < 0.05, Brier < 0.25
- **Preserved variance**: Raw simulator shape maintained
- **Clean separation**: UI shows centered, betting uses calibrated
- **More stable ROI**: Better probability estimates → better bet sizing

