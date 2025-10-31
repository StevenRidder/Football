# Main Simulation Files - Quick Reference

## 📁 Core Files (Required for Simulations)

### 1. Data Loading
- **`simulator/team_profile.py`** - Loads all 30 attributes from NFLfastR + PFF
- **`simulator/pff_loader.py`** - Loads PFF grades from CSV

### 2. Simulation
- **`simulator/play_simulator.py`** - Simulates individual plays
- **`simulator/game_simulator.py`** - Orchestrates full game simulation
- **`simulator/game_state.py`** - Game state management

### 3. Calibration
- **`simulator/market_centering.py`** - Centers scores to market (optional)
- **`backtest_all_games_conviction.py`** - Main backtest with linear calibration

### 4. Predictions
- **`scripts/generate_week9_predictions.py`** - Generate predictions
- **`scripts/format_for_frontend.py`** - Format for frontend

## 📊 Data Sources Used

### NFLfastR (13 files):
1. `rolling_epa_2022_2025.csv` - EPA per play
2. `team_yards_per_play_season.csv` - YPP/YPA
3. `early_down_success_season.csv` - Success rates
4. `team_anya_season.csv` - ANY/A
5. `turnover_regression_season.csv` - Turnover factors
6. `red_zone_stats_season.csv` - Red zone stats
7. `special_teams_season.csv` - Special teams
8. `playcalling_tendencies_season.csv` - Play calling
9. `drive_probabilities_season.csv` - Drive outcomes
10. `qb_pressure_splits_season.csv` - QB stats
11. `team_pace.csv` - Pace (plays per drive)
12. `situational_factors.csv` - Rest, weather, dome

### PFF (1 file):
13. `team_grades_2024.csv` - 6 grades per team (OL/DL pass, OL/DL run, passing, coverage)

## ✅ Data Usage Status

- **TeamProfile**: 30/30 attributes loaded (100%)
- **PlaySimulator**: 17/17 metrics used (100%)
- **GameSimulator**: 4/4 core attributes used (100%)
- **Overall**: 29/30 attributes fully utilized (97%)

## 🔄 Simulation Flow

```
TeamProfile → GameSimulator → PlaySimulator → Raw Scores → Calibration → Probabilities
```

## ⚠️ Key Finding

**Calibration Issue**: Currently centering to market THEN calibrating. Better approach:
- Remove market centering (or make optional)
- Calibrate raw scores directly to actual historical outcomes
- Use features: pace, dome, weather, rest days
