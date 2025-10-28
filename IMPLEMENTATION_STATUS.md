# Implementation Status - Market-Anchored Model Improvements

## Pass 1: Tighten Measurement

### Completed ✅
1. ✅ **Same book for open/close** - Now finds first book with BOTH markets
2. ✅ **Float equality fix** - Using `abs(diff) < 1e-9` for push detection
3. ✅ **Team name normalization** - Fixed LA → LAR for consistency
4. ✅ **Same book for spread AND total** - Iterates to find book with both markets

### In Progress 🔄
5. 🔄 **Per-game closing time** - Need to fetch at `commence_time - 60min` per game
6. 🔄 **Store and use real prices** - Structure ready, need to integrate into grading
7. 🔄 **Median across books** - If can't guarantee same book
8. 🔄 **CLV by key number buckets** - Track CLV crossing 3, 7, 10
9. 🔄 **Walk-forward validation** - Train 1-4, test 5-7
10. 🔄 **Cap total stake per game** - Dollar ceiling per game

### Not Started ⏸️
- None (all items in progress or completed)

---

## Pass 2: Build XGBoost Residual Model

### Target Variables
```python
margin_residual = actual_margin - (-closing_spread)
total_residual = actual_total - closing_total
```

### Features to Add

#### 1. QB Delta Features
- [ ] Starter vs backup flag
- [ ] Last 3 games dropback EPA
- [ ] Pressure-to-sack rate
- [ ] Scramble rate
- [ ] aDOT profile

#### 2. Protection & Weapons
- [ ] OL continuity past 3 games
- [ ] Pressure allowed
- [ ] WR1/WR2 game-time status

#### 3. Defense Shape
- [ ] Pressure rate
- [ ] Early-down success rate allowed
- [ ] Red-zone EPA allowed
- [ ] Man/zone rates (if available)

#### 4. Pace & Script
- [ ] Seconds per snap when trailing
- [ ] Seconds per snap when leading
- [ ] Neutral situation pass rate
- [ ] Red-zone run rate

#### 5. Market Priors
- [ ] Opening spread and total
- [ ] Closing spread and total
- [ ] Direction of line movement
- [ ] Magnitude of line movement
- [ ] Day of week of movement

#### 6. Weather & Surface
- [ ] Wind sustained
- [ ] Wind gusts
- [ ] Precipitation
- [ ] Surface type

### Model Architecture
- [ ] XGBoost with time-ordered CV
- [ ] Conservative regularization (small trees, high min_child_weight)
- [ ] Isotonic calibration for probabilities
- [ ] CLV gate: Only bet if projected CLV ≥ 1.0 points

### Inference
```python
projected_margin = -closing_spread + margin_residual_hat
projected_total = closing_total + total_residual_hat
```

---

## Current Status

**Pass 1 Progress:** 40% complete (4/10 items done)
**Pass 2 Progress:** 0% complete (planning phase)

**Next Steps:**
1. Complete remaining Pass 1 items (walk-forward, CLV buckets, stake caps)
2. Create `nfl_edge/xgb_residuals.py` module
3. Add QB/injury feature extraction
4. Train residual models
5. Backtest and validate

---

## Files Modified

### Pass 1
- `fetch_opening_closing_lines.py` - Book consistency, American odds, team names
- `backtest_residual_model.py` - Float equality, push grading

### Pass 2 (Planned)
- `nfl_edge/xgb_residuals.py` - NEW: Residual model training/inference
- `nfl_edge/qb_features.py` - NEW: QB availability and quality features
- `nfl_edge/protection_features.py` - NEW: OL/WR features
- `nfl_edge/defense_features.py` - NEW: Defense shape features
- `nfl_edge/pace_features.py` - NEW: Pace and script features
- `run_week.py` - EDIT: Integrate residual predictions
- `backtest_runner.py` - EDIT: Add residual model backtesting

---

**Last Updated:** October 27, 2025
**Status:** Pass 1 in progress, Pass 2 pending

