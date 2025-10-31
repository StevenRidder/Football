# Simulation Architecture & Data Flow

## 📁 Main Simulation Files

### Core Simulation
1. **`simulator/team_profile.py`** - Loads ALL data sources
   - NFLfastR: EPA, QB stats, playcalling, drive probs, pace, YPP, YPA, success rate, ANY/A, turnovers, red zone, special teams
   - PFF: OL/DL pass, OL/DL run, passing, coverage grades
   - Situational: Rest days, dome, weather

2. **`simulator/play_simulator.py`** - Simulates individual plays
   - Uses: PFF grades, YPP/YPA, ANY/A, red zone, turnovers, special teams
   - Outputs: Play outcomes (yards, TD, turnover)

3. **`simulator/game_simulator.py`** - Orchestrates full game
   - Uses: Pace, early-down success, playcalling, drive probs
   - Outputs: Final scores (home_score, away_score)

4. **`simulator/market_centering.py`** - Centers scores to market
   - Input: Raw simulator scores
   - Output: Market-aligned scores (for display)

### Calibration & Backtesting
5. **`backtest_all_games_conviction.py`** - Main backtest script
   - Runs simulations
   - Applies linear calibration
   - Calculates probabilities and edges

6. **`scripts/generate_week9_predictions.py`** - Generates predictions
   - Uses same simulation pipeline
   - Outputs formatted predictions

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
├─────────────────────────────────────────────────────────┤
│ NFLfastR:                                               │
│   • rolling_epa_2022_2025.csv                           │
│   • team_yards_per_play_season.csv                      │
│   • early_down_success_season.csv                       │
│   • team_anya_season.csv                                │
│   • turnover_regression_season.csv                      │
│   • red_zone_stats_season.csv                           │
│   • special_teams_season.csv                            │
│   • playcalling_tendencies_season.csv                   │
│   • drive_probabilities_season.csv                      │
│   • qb_pressure_splits_season.csv                       │
│   • team_pace.csv                                       │
│   • situational_factors.csv                             │
│                                                          │
│ PFF:                                                     │
│   • team_grades_2024.csv (6 grades per team)            │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              TeamProfile.__init__()                      │
│  Loads all 30 attributes from data sources              │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│            GameSimulator.simulate_game()                │
│  1. Initialize game state                                │
│  2. Loop through drives                                  │
│  3. For each play:                                      │
│     - PlaySimulator.decide_play_type()                  │
│     - PlaySimulator.simulate_pass_play() or             │
│       PlaySimulator.simulate_run_play()                 │
│  4. Update game state                                    │
│  5. Return final scores                                  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          Raw Simulator Output                            │
│  home_score_raw, away_score_raw                         │
│  spread_raw = home - away                               │
│  total_raw = home + away                                │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          Calibration (Current: Linear)                   │
│  calibrated_total = 26.45 + 0.571 * total_raw            │
│  calibrated_spread = f(home_raw, away_raw)               │
│                                                          │
│  ⚠️  ISSUE: Also centers to market (reduces signal)      │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          Probability Calculation                         │
│  p_home_cover = 1 - norm.cdf(                           │
│      (spread_line - calibrated_spread) / calibrated_sd  │
│  )                                                       │
│                                                          │
│  p_over = 1 - norm.cdf(                                 │
│      (total_line - calibrated_total) / calibrated_sd     │
│  )                                                       │
└─────────────────────────────────────────────────────────┘
```

## ⚠️ Current Calibration Issues

### Problem 1: Market Centering Reduces Signal
**Current Flow**:
```
Raw Sim → Center to Market → Linear Calibrate → Probabilities
```

**Issue**: Market centering aligns means but may hide model's true predictive power.

**Better Flow**:
```
Raw Sim → Calibrate to Actual Outcomes → Probabilities
```

### Problem 2: Calibration Based on Market Alignment, Not Accuracy
**Current**: `calibrated = 26.45 + 0.571 * raw` was fit to match market means.

**Better**: Fit calibration to **actual historical outcomes**:
```python
# Fit: actual_score = f(raw_score, features)
# Features: pace, dome, weather, rest days, etc.
calibrator = Ridge()
calibrator.fit(
    X=[raw_scores, pace, dome, ...],
    y=actual_scores
)
```

## ✅ What's Working Well

1. **Data Loading**: 100% of expected data sources are loaded
2. **PFF Integration**: All 6 grades fully integrated and used
3. **Play Simulation**: 16/17 metrics actively used in play outcomes
4. **Game Simulation**: Pace and early-down success used for drive logic

## 🔧 Recommended Improvements

### 1. Refactor Calibration (Priority 1)
**Goal**: Predict actual scores, not just align to market

**Approach**:
- Remove market centering (or make optional)
- Fit calibration model on historical actual outcomes
- Use features: raw_score, pace, dome, weather, rest days
- Target: actual_score (not market_mean)

### 2. Verify All Data Usage (Priority 2)
- ✅ Early-down success: USED (in game_simulator.py line 204)
- ⚠️ Playcalling: Verify full DataFrame is used
- ⚠️ Drive probs: Verify all field positions mapped

### 3. Strengthen Simulation (Priority 3)
- Add more situation-specific logic
- Use more granular playcalling data
- Apply situational factors (rest, weather) more directly

## 📊 Data Usage Summary

| Component | Data Sources | Attributes | Used | Utilization |
|-----------|--------------|------------|------|-------------|
| TeamProfile | 13 files | 30 | 30 | 100% |
| PlaySimulator | TeamProfile | 17 | 16 | 94% |
| GameSimulator | TeamProfile | 4 | 3 | 75% |
| **Overall** | **13** | **30** | **28** | **93%** |

## 🎯 Next Steps

1. ✅ Audit complete - identified gaps
2. ⏳ Refactor calibration to predict actual scores
3. ⏳ Verify playcalling and drive_probs full usage
4. ⏳ Test improved calibration on OOS data
5. ⏳ Compare ROI: market-centered vs actual-score-predicting

