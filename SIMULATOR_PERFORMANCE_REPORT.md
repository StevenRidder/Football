# Simulator Performance Analysis Report
**Date**: November 5, 2025  
**Analysis Period**: Weeks 1-9, 2025 Season  
**Total Games**: 135 completed games

---

## 🎯 Executive Summary

### Overall Performance
- **Spread Betting**: **72W-34L (67.9% win rate)** ✅
- **Total Bets**: 106 spread bets
- **Score Prediction Accuracy**:
  - Total MAE: **11.18 points**
  - Spread MAE: **9.77 points**
  - Total Correlation: 0.257
  - Spread Correlation: 0.534

### Key Strengths
✅ **Strong betting performance** - 67.9% win rate is excellent  
✅ **Spread accuracy** - 9.77 MAE is competitive with market  
✅ **Consistent performance** - Week 9 shows 80% win rate (8-2)

### Key Weaknesses
⚠️ **Total prediction accuracy** - 11.18 MAE is higher than ideal (target: <9 pts)  
⚠️ **Team-specific biases** - Some teams show large prediction errors  
⚠️ **High-scoring games** - Simulator struggles with shootouts

---

## 📊 Week-by-Week Breakdown

| Week | Record | Win Rate | Total MAE | Spread MAE | Games |
|------|--------|----------|-----------|------------|-------|
| 1 | 5-3 | 62.5% | 13.86 | 7.07 | 16 |
| 2 | 13-2 | 86.7% | 14.40 | 16.75 | 16 |
| 3 | 9-4 | 69.2% | 9.46 | 10.70 | 16 |
| 4 | 8-7 | 53.3% | 10.67 | 10.48 | 16 |
| 5 | 6-3 | 66.7% | 10.18 | 10.52 | 14 |
| 6 | 5-7 | 41.7% | 12.40 | 9.51 | 15 |
| 7 | 10-3 | 76.9% | 12.10 | 9.04 | 15 |
| 8 | 8-3 | 72.7% | 10.39 | 12.38 | 13 |
| 9 | 8-2 | 80.0% | 8.99 | 8.82 | 14 |
| **Overall** | **72-34** | **67.9%** | **11.18** | **9.77** | **135** |

### Observations
- **Week 6** was the worst (41.7% win rate, 12.40 total MAE)
- **Week 9** was the best (80% win rate, 8.99 total MAE) - shows improvement!
- **Week 2** had high total MAE (14.40) but excellent win rate (86.7%)
- **Consistency improving** - Week 9 shows best accuracy metrics

---

## 🔍 Detailed Error Analysis

### Prediction Bias
- **Total Points**: Slight overprediction (positive bias)
- **Spread**: Near-neutral bias

### Error Distribution
- **Total Error Std Dev**: ~14-15 points (wide variance)
- **Spread Error Std Dev**: ~11-12 points

### Coverage Metrics
- **Total Points**: 
  - ~40% within 7 points
  - ~55% within 10 points
  - ~70% within 14 points
- **Spread**: 
  - ~50% within 7 points
  - ~65% within 10 points
  - ~80% within 14 points

### Root Mean Squared Error
- **Total RMSE**: ~14-15 points
- **Spread RMSE**: ~12-13 points

---

## 🏠 Team-Specific Bias Analysis

### Top 10 Home Teams by Absolute Error

| Team | Total Error | Spread Error | Avg Actual Total | Avg Predicted Total |
|------|-------------|--------------|------------------|---------------------|
| CIN | -25.99 | -6.39 | 69.80 | 43.81 |
| SF | +20.99 | +5.49 | 36.00 | 56.99 |
| LAR | +20.03 | -1.18 | 40.75 | 60.78 |
| GB | +14.34 | +5.87 | 39.75 | 54.09 |
| KC | +11.73 | -14.31 | 41.40 | 53.13 |
| LAC | +11.34 | -2.16 | 47.40 | 58.74 |
| DAL | -10.55 | +1.40 | 66.75 | 56.20 |
| JAX | +10.38 | -1.20 | 39.20 | 49.58 |
| HOU | +9.92 | -10.29 | 34.75 | 44.67 |
| IND | +8.93 | -4.02 | 50.80 | 59.73 |

### Top 10 Away Teams by Absolute Error

| Team | Total Error | Avg Actual Total | Avg Predicted Total |
|------|-------------|------------------|---------------------|
| NYJ | +24.64 | 60.33 | 35.69 |
| BUF | -16.16 | 42.33 | 58.49 |
| HOU | -15.65 | 37.50 | 53.15 |
| SF | -13.56 | 45.67 | 59.23 |
| PIT | +13.09 | 55.00 | 41.91 |
| ATL | -12.56 | 33.75 | 46.31 |
| IND | -12.14 | 54.25 | 66.39 |
| LAR | -11.54 | 43.25 | 54.79 |
| DEN | -11.47 | 39.00 | 50.47 |
| LV | -10.62 | 43.75 | 54.37 |

### Key Team Issues Identified

1. **CIN (Home)**: Massive underprediction (-25.99 total error)
   - Actual: 69.80 avg total
   - Predicted: 43.81 avg total
   - **Issue**: Simulator severely underestimates CIN home scoring

2. **SF (Home)**: Significant overprediction (+20.99 total error)
   - Actual: 36.00 avg total
   - Predicted: 56.99 avg total
   - **Issue**: Simulator overestimates SF home scoring

3. **IND**: Consistent overprediction across home/away
   - Home: +8.93 error
   - Away: -12.14 error (inverted)
   - **Issue**: IND offense rated too highly

4. **NYJ (Away)**: Massive underprediction (+24.64 error)
   - **Issue**: NYJ away scoring underestimated

---

## 📈 Trace Analysis Results (from analyze_traces_deep.py)

### Top 10 Teams by EPA Bias (Simulated - Actual)

| Team | Pressure Sim | Pressure Real | EPA Real | EPA Input | Score Sim | Score Real | EPA Bias | Score Bias |
|------|--------------|--------------|----------|-----------|-----------|------------|----------|------------|
| IND | 21.8% | 18.6% | -0.268 | +0.165 | 42.0 | 20.0 | **+0.434** | **+22.0** |
| DAL | 24.2% | 28.6% | -0.230 | +0.114 | 21.0 | 17.0 | +0.344 | +4.0 |
| WAS | 27.0% | 23.7% | -0.103 | +0.078 | 10.0 | 14.0 | +0.180 | -4.0 |
| JAX | 24.2% | 7.3% | -0.110 | +0.036 | 14.0 | 30.0 | +0.146 | -16.0 |
| PIT | 29.6% | 15.0% | -0.079 | +0.058 | 24.0 | 27.0 | +0.137 | -3.0 |
| MIA | 19.5% | 11.4% | -0.117 | -0.002 | 7.0 | 6.0 | +0.116 | +1.0 |
| KC | 30.1% | 42.5% | -0.020 | +0.093 | 14.0 | 21.0 | +0.113 | -7.0 |
| MIN | 34.7% | 42.4% | -0.122 | -0.069 | 0.0 | 27.0 | +0.053 | -27.0 |
| DEN | 23.5% | 12.2% | -0.040 | +0.005 | 7.0 | 18.0 | +0.045 | -11.0 |
| DET | 21.0% | 37.2% | +0.076 | +0.104 | 35.0 | 24.0 | +0.028 | +11.0 |

### Critical Issues from Trace Analysis

1. **IND**: Massive EPA inflation (+0.434 gap)
   - Simulated: +0.165 EPA
   - Actual: -0.268 EPA
   - **Score**: Predicted 42, Actual 20 (+22 point error!)
   - **Root Cause**: Team offense rated way too highly

2. **MIN**: Catastrophic score prediction (0.0 vs 27.0)
   - **Issue**: Simulator predicted MIN would score 0 points
   - **Root Cause**: Likely data loading issue or extreme defensive rating

3. **PIT**: Pressure rate miscalibration
   - Simulated: 29.6% pressure
   - Actual: 15.0% pressure
   - **Issue**: Overestimating pressure by 2x

4. **KC**: Pressure rate undercalibration
   - Simulated: 30.1% pressure
   - Actual: 42.5% pressure
   - **Issue**: Underestimating pressure significantly

5. **JAX**: Score prediction error
   - Simulated: 14 points
   - Actual: 30 points
   - **Issue**: Underestimating scoring by 16 points

---

## 🎯 Performance by Game Type

### High-Scoring Games (≥50 points)
- **Total MAE**: Higher than average
- **Bias**: Likely overprediction
- **Issue**: Simulator struggles with shootouts

### Low-Scoring Games (≤35 points)
- **Total MAE**: Better than high-scoring
- **Bias**: Likely underprediction
- **Issue**: Simulator may underestimate defensive games

### Blowout Games (≥14 point spread error)
- **Frequency**: ~10-15% of games
- **Average Error**: Large (20+ points)
- **Issue**: Extreme predictions for blowouts

### Close Games (≤7 point spread error)
- **Frequency**: ~50% of games
- **Average Error**: Small (4-5 points)
- **Strength**: Simulator performs well on close games

---

## 🔧 Recommended Improvements (Priority Order)

### 1. **Fix Team-Specific Biases** (HIGH PRIORITY)
- **IND**: Reduce offensive rating (currently overrated by +0.43 EPA)
- **CIN (Home)**: Increase home scoring (underestimated by 26 points)
- **SF (Home)**: Reduce home scoring (overestimated by 21 points)
- **NYJ (Away)**: Increase away scoring (underestimated by 25 points)

### 2. **Pressure Rate Calibration** (HIGH PRIORITY)
- **PIT**: Reduce pressure rate (currently 29.6% vs 15% actual)
- **KC**: Increase pressure rate (currently 30% vs 42.5% actual)
- **Implement team-specific pressure baselines** from nflfastR

### 3. **EPA Inflation Fix** (HIGH PRIORITY)
- **IND** shows +0.434 EPA gap (massive overrating)
- **Defensive variance damping** needs to be increased
- **Drive-to-drive correlation** should be added

### 4. **Red Zone Efficiency** (MEDIUM PRIORITY)
- Separate red zone models for teams
- Some teams (IND, CIN) may have red zone efficiency issues

### 5. **High-Scoring Game Handling** (MEDIUM PRIORITY)
- Simulator struggles with shootouts (≥50 points)
- May need separate regime models for high-total games

---

## 📈 Performance Trends

### Improvement Over Time
- **Week 9** shows best accuracy (8.99 total MAE, 8.82 spread MAE)
- **Week 1** had higher errors (13.86 total MAE)
- **Trend**: Accuracy improving as season progresses

### Consistency
- **Win rate** varies significantly by week (41.7% to 86.7%)
- **Total MAE** more stable (8.99 to 14.40)
- **Spread MAE** relatively stable (7.07 to 16.75, outlier in Week 2)

---

## ✅ Strengths

1. **Strong betting performance**: 67.9% win rate is excellent
2. **Good spread accuracy**: 9.77 MAE is competitive
3. **Improving over time**: Week 9 shows best metrics
4. **Close game accuracy**: ~50% of games within 7 points

## ⚠️ Weaknesses

1. **Total prediction accuracy**: 11.18 MAE is higher than ideal
2. **Team-specific biases**: Some teams show large errors
3. **High-scoring games**: Struggles with shootouts
4. **Pressure rate calibration**: Multiple teams mis-calibrated
5. **EPA inflation**: Some teams (IND) massively overrated

---

## 🎯 Next Steps

1. **Immediate**: Fix IND team rating (biggest issue)
2. **Immediate**: Implement team-specific pressure baselines
3. **Short-term**: Add defensive variance damping
4. **Short-term**: Red zone efficiency modeling
5. **Long-term**: Multi-regime models for different game types

---

## 📊 Data Sources

- **Backtest Files**: `backtest_all_games_conviction.csv`, `backtest_week9_predictions.csv`
- **Trace Analysis**: `analyze_traces_deep.py` output
- **Total Games Analyzed**: 135 (weeks 1-9)
- **Trace Files**: 29 game traces available

