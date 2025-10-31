# Probability Calibration Strategy

## Problem Statement

Currently, we center the simulator distribution to match the market mean, which is correct for display purposes. However, **calibration** (mapping raw simulator output to market-calibrated probabilities) could improve betting accuracy while preserving the simulator's natural variance.

## Two Approaches

### 1. Logistic Regression Calibration (Idea 1)

**Concept**: Use market lines as a calibration layer to convert raw spread deltas into probabilities.

```
P(win) = sigmoid(β₀ + β₁·(sim_spread - market_spread))
```

**Benefits**:
- Preserves raw simulator's natural mean and variance
- Learns how raw deltas map to actual win rates from historical data
- No artificial centering that might distort the distribution shape

**Implementation**:
- Fit logistic regression on historical backtest data
- Input: `raw_spread - market_spread` (the delta)
- Output: `actual_cover_result` (1 = home covered, 0 = away covered)
- Use fitted model to convert new predictions to probabilities

### 2. Dual Ensemble (Idea 2)

**Concept**: Treat model and market as two separate predictors, blend at probability level.

```
P_final = α·P_model + (1-α)·P_market

where P_market = 0.524 (breakeven at -110)
```

**Benefits**:
- Conservative - pulls probabilities toward market baseline
- Easy to tune with `α` parameter
- Measures "lift above 52.4%" directly

**Implementation**:
- Calculate `P_model` from centered distribution (current approach)
- Blend with `P_market = 0.524`
- Adjust `α` based on backtest performance

## Hybrid Approach (Recommended)

**Use BOTH**:

1. **For Display**: Keep current centering approach (shows market-implied scores)
2. **For Betting**: Use calibrated probabilities from logistic regression
3. **For Confidence**: Optionally blend calibrated model + market baseline

## Implementation Steps

### Step 1: Fit Calibrator from Historical Data

```python
from simulator.probability_calibration import ProbabilityCalibrator

# Load historical backtest results
backtest_df = pd.read_csv('artifacts/backtest_all_games_conviction.csv')

# Extract features: (raw_spread - market_spread)
# Extract outcomes: did home actually cover?

calibrator = ProbabilityCalibrator()
calibrator.fit_from_historical(
    raw_spreads=backtest_df['spread_raw'],
    market_spreads=backtest_df['spread_line'],
    outcomes=backtest_df['spread_result']  # 1 = win, 0 = loss
)
```

### Step 2: Use Calibrated Probabilities for Betting

```python
# Get raw simulator output (preserve natural mean/variance)
raw_spread_mean = np.mean(raw_spreads)

# Convert to calibrated probability (NOT centered distribution)
p_home_cover_calibrated = calibrator.predict_probability(
    raw_spread_mean, 
    market_spread
)

# Use calibrated prob for betting decisions
if p_home_cover_calibrated > BREAKEVEN + EDGE_THRESHOLD:
    bet = 'HOME'
```

### Step 3: Keep Centered Display for UI

```python
# Still center for display purposes
home_c, away_c = center_scores_to_market(home_raw, away_raw, spread_line, total_line)

# But use CALIBRATED probabilities for betting
p_home_cover = calibrator.predict_probability(raw_spread_mean, market_spread)
```

### Step 4: Optional Ensemble Blending

```python
from simulator.probability_calibration import DualEnsemble

# Blend calibrated model + market baseline
ensemble = DualEnsemble(alpha=0.7)  # 70% model, 30% market
p_final = ensemble.blend(p_home_cover_calibrated)
```

## Advantages

1. **Preserves Raw Simulator Signal**: No artificial mean-shifting that could distort variance
2. **Empirically Calibrated**: Learns from historical data how deltas map to win rates
3. **Backward Compatible**: Still shows centered scores for UI, uses calibrated probs for betting
4. **Conservative Option**: Dual ensemble pulls toward market baseline when uncertain

## Testing Plan

1. Fit calibrator on 2022-2024 data (or weeks 1-7 of 2025)
2. Test on held-out data (week 8 of 2025)
3. Compare:
   - Current approach (centered probabilities)
   - Calibrated probabilities
   - Ensemble approach
4. Measure: ROI, Log Loss, Brier Score, Calibration curves

## Expected Outcomes

- **Calibrated approach** should improve probability accuracy (better calibration)
- **Ensemble approach** should be more conservative but potentially more stable
- **Raw simulator** variance preserved (no artificial distortion)

