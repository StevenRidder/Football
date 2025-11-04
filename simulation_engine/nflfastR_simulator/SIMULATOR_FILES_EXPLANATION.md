# Simulator Codebase: Detailed File Explanation

## Overview

This document explains what each file in the simulator codebase does, how the code works, and what's actually needed vs. what's redundant.

---

## Core Architecture Flow

```
1. TeamProfile (team_profile.py) → Load team stats/metrics
2. GameSimulator (game_simulator.py) → Run play-by-play simulation
3. Market Centering (market_centering.py) → Anchor to Vegas lines
4. Linear Calibration → Adjust raw scores to match historical reality
5. Probability Calibration (probability_calibration.py) → Convert to probabilities
6. Betting Recommendations → Generate picks
```

---

## File-by-File Breakdown

### **CORE SIMULATOR FILES** (Essential)

#### 1. `game_simulator.py` ✅ **ESSENTIAL - PRODUCTION**
**What it does:**
- Orchestrates the entire game simulation
- Runs play-by-play Monte Carlo simulation
- Manages game state (score, time, possession, field position)
- Calls `PlaySimulator` for individual plays
- Handles drives, 4th down decisions, field goals, punts

**Key Methods:**
- `simulate_game()`: Run one full game simulation
- `simulate_monte_carlo(n_sims)`: Run N simulations and aggregate results
- `get_betting_recommendations_centered()`: Generate betting picks (legacy method)

**How it works:**
1. Initialize `GameState` (score, possession, field position)
2. For each drive:
   - Determine offense/defense based on possession
   - Simulate plays until TD, turnover, or drive ends
   - Use `PlaySimulator` to simulate pass/run plays
3. Track scores, spreads, totals across all simulations
4. Return aggregated statistics

**Status:** ✅ **USED IN PRODUCTION** - This is the main simulator engine.

---

#### 2. `game_state.py` ✅ **ESSENTIAL - PRODUCTION**
**What it does:**
- Manages game state: score, quarter, time, possession, field position, down/distance
- Tracks drive information
- Handles clock management, quarter transitions
- Manages special situations (4th down, FG range, etc.)

**Key Methods:**
- `update_from_play()`: Update state after a play
- `start_new_drive()`: Reset for new drive
- `should_attempt_fg()`: Decision logic for field goals
- `should_punt()`: Decision logic for punts

**Status:** ✅ **USED IN PRODUCTION** - Core game state management.

---

#### 3. `play_simulator.py` ✅ **ESSENTIAL - PRODUCTION**
**What it does:**
- Simulates individual plays (pass, run, FG, punt)
- Uses team profiles (EPA, success rates, QB stats) to determine outcomes
- Handles turnovers, explosive plays, sacks
- Returns yards gained, TDs, turnovers

**Key Methods:**
- `simulate_pass_play()`: Simulate pass play outcome
- `simulate_run_play()`: Simulate run play outcome
- `simulate_field_goal()`: Simulate FG attempt
- `simulate_punt()`: Simulate punt
- `decide_play_type()`: Choose pass vs. run based on situation

**Status:** ✅ **USED IN PRODUCTION** - Core play simulation logic.

---

#### 4. `team_profile.py` ✅ **ESSENTIAL - PRODUCTION**
**What it does:**
- Loads and stores team statistics/metrics
- Calculates team ratings (EPA, success rates, QB stats, pace, etc.)
- Applies situational factors (rest days, weather, dome)
- Provides metrics to `PlaySimulator` for play outcomes

**Key Metrics Loaded:**
- EPA per play (offense/defense)
- Early-down success rate
- QB stats (PFF grades, completion %, etc.)
- Pace (plays per drive)
- Play-calling tendencies

**Status:** ✅ **USED IN PRODUCTION** - Core data loading.

---

### **MARKET CENTERING & CALIBRATION** (Critical for betting)

#### 5. `market_centering.py` ✅ **ESSENTIAL - PRODUCTION**
**What it does:**
- **Core Strategy**: Anchor simulator mean to Vegas lines, keep the SHAPE (variance/tails)
- Shifts raw simulation scores to match market spread/total exactly
- Preserves distribution shape (variance, skew, tails) while changing mean
- This is the KEY INSIGHT: We don't try to beat Vegas on mean, we model shape

**Key Functions:**
- `center_scores_to_market()`: **USED IN PRODUCTION** - Shifts scores to match market
  - Multiplicative scale toward target total
  - Additive total correction (preserves spread)
  - Additive spread correction (preserves total)
  - Hits market exactly even when scaling is clipped
  
- `center_to_market()`: Wrapper that processes full simulation results
- `validate_centering()`: Checks that mean matches market within tolerance
- `get_betting_recommendation()`: Generate picks from centered distribution
- `calculate_clv()`: Calculate Closing Line Value

**How it works:**
1. Takes raw simulation scores (home/away arrays)
2. Calculates raw mean spread and total
3. Applies 3-step transformation:
   - Scale scores toward target total (clipped for safety)
   - Add total correction (preserves spread)
   - Add spread correction (preserves total)
4. Returns centered scores that match market mean exactly
5. Preserves variance, tails, skew (the edge comes from shape!)

**Status:** ✅ **USED IN PRODUCTION** - Used in `backtest_all_games_conviction.py` and `generate_week9_10_predictions.py`

**Example Usage:**
```python
# In production prediction scripts:
home_c, away_c = center_scores_to_market(
    home_scores, away_scores, spread_line, total_line
)
# Now mean(home_c - away_c) ≈ spread_line
# And mean(home_c + away_c) ≈ total_line
```

---

#### 6. `market_calibration.py` ❌ **NOT USED - REDUNDANT**
**What it does:**
- Similar to `market_centering.py` but uses weighted blending approach
- Blends raw predictions with market (70% weight to market)
- Less precise than `market_centering.py` (doesn't hit market exactly)

**Key Function:**
- `calibrate_monte_carlo_results()`: Blends raw and market (weighted average)

**Why it's redundant:**
- `market_centering.py` is better (hits market exactly, preserves shape better)
- Only used in `test_10_games_corrected.py` (old test file)
- Production uses `market_centering.py` instead

**Status:** ❌ **NOT USED IN PRODUCTION** - Can be deleted or kept for reference.

---

#### 7. `calibrate_scoring.py` ⚠️ **DEVELOPMENT/DEBUGGING TOOL**
**What it does:**
- **Purpose**: Tune raw simulator to match NFL reality (plays per drive, TD%, FG%, etc.)
- Instruments the simulator with detailed logging
- Compares simulator output to NFL targets (e.g., 6.0-6.8 plays/drive, 22-24% TD rate)
- Provides recommendations for parameter adjustments

**Key Classes:**
- `InstrumentedGameSimulator`: GameSimulator with detailed logging
  - Logs drives, plays, scoring events, field positions
  - Tracks play types, outcomes, explosive plays

**Key Functions:**
- `run_calibration_test()`: Run N games and compare to NFL targets

**Status:** ⚠️ **DEVELOPMENT TOOL** - Not used in production, but useful for tuning simulator parameters.

**When to use:**
- When simulator output doesn't match NFL reality
- When tuning drive length, scoring rates, etc.
- Before deploying changes to core simulator logic

---

#### 8. `probability_calibration.py` ⚠️ **PARTIALLY USED - LEGACY**
**What it does:**
- Converts raw simulator output to calibrated probabilities using z-scores
- Uses isotonic regression or Platt scaling (logistic regression)
- Features: `z = (sim_mean - market) / sim_sd`
- Targets: Binary outcomes (cover/not cover)

**Key Classes:**
- `ProbabilityCalibrator`: Fits isotonic/Platt calibrator on historical data
- `PlattScaling`: Logistic regression for probability calibration
- `AdaptiveEnsemble`: Blends model probability with neutral baseline (50%)

**Key Functions:**
- `calibrate_probabilities()`: Convert raw spread to calibrated probability
- `calibrate_total_probabilities()`: Convert raw total to calibrated probability

**Current Status:**
- ⚠️ **PARTIALLY USED** - Imported in some scripts but not actively used
- Production uses **linear calibration** instead (simple formula: `calibrated = 26.45 + 0.571 * raw`)
- Probability calibration was experimented with but linear calibration is simpler and works better

**Why it's not used:**
- Linear calibration (score-level) is simpler and more reliable
- Probability calibration requires fitting on historical data
- Production scripts use linear calibration directly

**Status:** ⚠️ **LEGACY/EXPERIMENTAL** - Can be kept for future experiments, but not critical.

---

### **DATA LOADING** (Essential)

#### 9. `data_loader.py` ✅ **ESSENTIAL - PRODUCTION**
**What it does:**
- Loads nflfastR play-by-play data
- Handles roll-forward (as_of dates to prevent look-ahead)
- Provides data filtering and aggregation utilities

**Status:** ✅ **USED IN PRODUCTION** - Core data infrastructure.

---

#### 10. `pff_loader.py` ✅ **ESSENTIAL - PRODUCTION**
**What it does:**
- Loads PFF (Pro Football Focus) QB grades
- Handles missing data, normalization
- Provides QB stats to `TeamProfile`

**Status:** ✅ **USED IN PRODUCTION** - Required for QB metrics.

---

#### 11. `pff_zero_mean.py` ⚠️ **UTILITY - MAY BE USED**
**What it does:**
- Normalizes PFF grades to zero mean
- Ensures grades don't bias simulator

**Status:** ⚠️ **CHECK USAGE** - May be used in preprocessing.

---

#### 12. `empirical_bayes.py` ⚠️ **DEVELOPMENT TOOL**
**What it does:**
- Empirical Bayes shrinkage for small sample sizes
- Reduces overfitting when team has limited data

**Status:** ⚠️ **DEVELOPMENT TOOL** - May be used in team profile calculations.

---

#### 13. `team_profile.py` ✅ **ESSENTIAL - PRODUCTION**
*(Already covered above)*

---

### **TEST FILES** (Development/Validation)

#### 14. `test_simulator.py` ✅ **USEFUL TEST**
**What it does:**
- Quick test of simulator on single game (KC vs BUF)
- Runs 100 simulations for speed
- Tests betting recommendations
- Sanity checks (scores in range, etc.)

**Status:** ✅ **USEFUL** - Good for quick validation after changes.

---

#### 15. `test_centering.py` ✅ **USEFUL TEST**
**What it does:**
- Tests market centering functionality
- Demonstrates the key insight (anchor to mean, model shape)
- Validates centering works correctly

**Status:** ✅ **USEFUL** - Good for understanding market centering.

---

#### 16. `test_centering_exact.py` ✅ **UNIT TEST**
**What it does:**
- Unit test: Verifies centering is exact (within 0.1 points)
- Tests `center_scores_to_market()` function

**Status:** ✅ **UNIT TEST** - Validates core centering logic.

---

#### 17. `test_centered_game.py` ✅ **INTEGRATION TEST**
**What it does:**
- Full integration test: KC @ BUF with market centering
- Runs 1,000 simulations
- Centers to market
- Generates betting recommendations
- Compares to actual result

**Status:** ✅ **INTEGRATION TEST** - Good for end-to-end validation.

---

## How Production Works (Current Flow)

### **Production Prediction Scripts:**
1. `scripts/generate_week9_10_predictions.py` (or similar)
2. `backtest_all_games_conviction.py`

### **Flow:**
```python
# 1. Load team profiles
home_team = TeamProfile(home, season, week, data_dir)
away_team = TeamProfile(away, season, week, data_dir)

# 2. Run raw simulation
simulator = GameSimulator(home_team, away_team)
home_scores, away_scores = [], []
for _ in range(N_SIMS):
    result = simulator.simulate_game()
    home_scores.append(result['home_score'])
    away_scores.append(result['away_score'])

# 3. Market centering (OPTIONAL - used in production)
home_c, away_c = center_scores_to_market(
    home_scores, away_scores, spread_line, total_line
)

# 4. Linear calibration (score-level)
calibrated_home_mean = LINEAR_ALPHA/2 + LINEAR_BETA * raw_home_mean
calibrated_away_mean = LINEAR_ALPHA/2 + LINEAR_BETA * raw_away_mean
calibrated_spread_mean = calibrated_home_mean - calibrated_away_mean

# 5. Calculate probabilities (from centered distribution)
p_home_cover = np.mean(spreads_c > spread_line)
p_over = np.mean(totals_c > total_line)

# 6. Generate betting recommendations
# (edge calculation, conviction tiers, etc.)
```

---

## Summary: What's Needed vs. Not Needed

### ✅ **ESSENTIAL - KEEP:**
1. `game_simulator.py` - Core simulator
2. `game_state.py` - Game state management
3. `play_simulator.py` - Play simulation
4. `team_profile.py` - Team data loading
5. `market_centering.py` - **CRITICAL** - Market anchoring
6. `data_loader.py` - Data infrastructure
7. `pff_loader.py` - PFF data loading
8. Test files (`test_simulator.py`, `test_centering.py`, etc.) - Validation

### ❌ **REDUNDANT - CAN DELETE:**
1. `market_calibration.py` - Replaced by `market_centering.py`
2. `probability_calibration.py` - Not used, replaced by linear calibration

### ⚠️ **DEVELOPMENT TOOLS - KEEP FOR TUNING:**
1. `calibrate_scoring.py` - Useful for tuning simulator parameters
2. `empirical_bayes.py` - May be used in team profile calculations

---

## Key Insights

1. **Market Centering is CRITICAL**: 
   - We anchor to Vegas mean, model the shape (variance/tails)
   - Edge comes from distribution shape, not mean prediction
   - `market_centering.py` is the production approach

2. **Linear Calibration is Simple and Effective**:
   - Production uses: `calibrated = 26.45 + 0.571 * raw`
   - More reliable than complex probability calibration
   - Applied at score level, preserves variance

3. **Two-Step Process**:
   - Step 1: Market centering (optional, used in production) - anchors mean to Vegas
   - Step 2: Linear calibration - adjusts raw scores to match historical reality

4. **Test Files are Valuable**:
   - `test_centering_exact.py`: Unit test for core centering logic
   - `test_centered_game.py`: Integration test for full flow
   - Use these after making changes

---

## Recommendations

1. **Delete `market_calibration.py`** - It's redundant, `market_centering.py` is better
2. **Keep `probability_calibration.py` for future experiments** - But not critical for production
3. **Keep `calibrate_scoring.py`** - Useful for tuning simulator when metrics drift
4. **Document the two-step process** clearly:
   - Market centering (optional): Anchor mean to Vegas
   - Linear calibration (required): Adjust scores to match reality

