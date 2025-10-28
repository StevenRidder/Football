# XGBoost Residual Model - Implementation Status

## What Was Built

### 1. Core Modules ✅
- **`nfl_edge/xgb_residuals.py`** - XGBoost residual model with isotonic calibration
- **`nfl_edge/qb_features.py`** - QB quality features (EPA, CPOE, aDOT, scramble rate, pressure-to-sack)
- **`train_and_backtest_residual.py`** - Training and backtesting pipeline

### 2. Features Implemented ✅
- Market priors (opening spread/total, closing spread/total, movement)
- Team EPA (offense/defense)
- Success rates (offense/defense)
- Turnover differential
- QB quality metrics (season-long and last 3 games)
- Matchup features (OFF_EPA × DEF_EPA interactions)

### 3. Model Architecture ✅
- XGBoost with conservative parameters (max_depth=3, learning_rate=0.05)
- Isotonic calibration for probability mapping
- Separate models for margin and total residuals

---

## Current Results

### Test Run (Weeks 5-7)
```
Training Data: 6 games (Weeks 1-4)
Test Data: 4 games (Weeks 5-7)

Backtest Results:
- Total Bets: 4
- Win Rate: 50.0% (2-2)
- ROI: -8.7%
- MAE: 7.28 pts (margin), 10.00 pts (total)
```

### Critical Issue: Insufficient Training Data

**Only 10 games matched** between:
- ESPN results (108 games)
- Market lines (116 games)

**Root Cause:** Team abbreviation mismatch between data sources.

---

## The Problem

### 1. Sample Size Too Small
- XGBoost needs 100+ samples minimum
- We have 6 training games
- Feature importance all zeros → model not learning

### 2. Team Abbreviation Mapping
ESPN uses: `WSH`, `LAR`
Our data uses: `WAS`, `LA` or `LAR`

**Fix Required:** Normalize all team abbreviations to a single standard.

### 3. Missing Features
Per your PRD, we still need:
- ❌ OL continuity / protection metrics
- ❌ WR1/WR2 injury status
- ❌ Defense pressure rate, early-down SR, red-zone EPA
- ❌ Pace & script (seconds per snap, neutral pass rate)
- ❌ Weather (wind, precip)
- ❌ Surface type
- ⏸️ **Backup QB detection** (bookmarked for LLM parsing)

---

## What Works

1. ✅ **Pipeline is functional** - Training, prediction, backtesting all work
2. ✅ **QB features integrate** - nflverse data loads correctly
3. ✅ **XGBoost trains** - No library errors, isotonic calibration works
4. ✅ **Walk-forward validation** - Train/test split implemented

---

## Next Steps (Priority Order)

### Immediate (Fix Data Issues)
1. **Normalize team abbreviations** across all data sources
2. **Verify all 108 games have market lines** - Should be 108, not 10
3. **Re-run training** with full dataset

### Short-Term (Add Missing Features)
4. **Protection metrics** - OL continuity, pressure allowed
5. **Pace features** - Seconds per snap, neutral pass rate
6. **Defense shape** - Pressure rate, early-down SR
7. **Weather** - Wind, precip from Open-Meteo (already have function)

### Medium-Term (Model Refinement)
8. **Hyperparameter tuning** - Grid search on XGBoost params
9. **Feature selection** - Remove low-importance features
10. **Ensemble** - Combine with current model

### Long-Term (Production)
11. **LLM injury parser** - Extract backup QB, WR/OL status
12. **Real-time inference** - Integrate into `run_week.py`
13. **CLV tracking** - Monitor actual vs predicted CLV

---

## Comparison: Current Model vs Residual Model

### Current Model (Weeks 5-7)
- **Bets:** 66
- **Win Rate:** 74.2%
- **ROI:** 43.2%
- **CLV:** +0.01 pts, 3.0% positive

### Residual Model (Weeks 5-7)
- **Bets:** 4
- **Win Rate:** 50.0%
- **ROI:** -8.7%
- **CLV:** Not calculated (insufficient data)

**Verdict:** Current model is better, but residual model hasn't had a fair test due to data issues.

---

## Recommendation

**Fix team abbreviation mapping FIRST**, then re-run with all 108 games. If we still get <50 games, the market lines data is incomplete and we need to re-fetch from Odds API.

Once we have 100+ training samples, the XGBoost model will have a fair chance to learn residuals.

---

**Last Updated:** October 27, 2025
**Status:** Prototype complete, data quality issues blocking evaluation

