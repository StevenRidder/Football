# Fixes Applied Based on Feedback

## ✅ Completed Fixes

### 1. Method Name Mismatch
**Issue**: `test_simulator.py` calls `get_betting_recommendations()` but class defines `get_betting_recommendations_centered()`.

**Fix**: Added alias method `get_betting_recommendations()` that calls `get_betting_recommendations_centered()` for backward compatibility.

**File**: `simulator/game_simulator.py`

---

### 2. Rest Days Assignment Bug
**Issue**: Both teams were getting the same `home_rest_days` and `away_rest_days` values.

**Fix**: Corrected logic so:
- Home team gets `home_rest_days` from CSV (their rest days)
- Away team gets `away_rest_days` from CSV (their rest days)

**File**: `simulator/game_simulator.py` (lines 102-116)

---

### 3. PFF Abbreviation Mapping Expanded
**Issue**: Only 5 teams mapped (BAL, ARI, CLE, HOU, LAR), causing failures for other teams.

**Fix**: 
- Expanded mapping to include all 32 NFL teams with historical variations
- Added soft fallback with league averages (50th percentile) instead of crashing
- Added `_fallback_used` flag for confidence downgrade tracking

**File**: `simulator/pff_loader.py` (lines 94-140)

---

### 4. PFF Hard Failures → Soft Fallbacks
**Issue**: `PlaySimulator` raises `ValueError` on missing PFF data, halting all sims.

**Fix**: 
- `PFFLoader` now returns league averages with warning instead of raising
- `TeamProfile._load_pff_grades()` catches exceptions and uses defaults
- Added `pff_fallback_used` flag for confidence tracking

**Files**: 
- `simulator/pff_loader.py`
- `simulator/team_profile.py` (lines 453-476)

---

### 5. Run-Play Yard Adjustment Reduced
**Issue**: Stacked signals (EPA × 24, YPP × 1.6, PFF × 0.10) inflating rushing yards.

**Fix**:
- EPA coefficient: 24 → 12 (50% reduction)
- PFF grade coefficient: 0.10 → 0.06 (40% reduction)
- YPP coefficient: 1.6 → 0.8 (50% reduction, shares credit with EPA)

**File**: `simulator/play_simulator.py` (lines 466-488)

---

### 6. Opening Possession Randomized
**Issue**: Always giving home team opening kickoff biases home totals and first-half shapes.

**Fix**: Randomize opening possession (50% home, 50% away) to simulate coin toss.

**File**: `simulator/game_simulator.py` (lines 132-137)

---

### 7. Schema Validation Added
**Issue**: No validation that required fields exist and are proper types.

**Fix**: Added `_validate_schema()` method that checks all required fields:
- `off_epa`, `def_epa`, `off_anya`, `def_anya_allowed`
- `off_yards_per_pass_attempt`, `def_yards_per_pass_allowed`
- `off_yards_per_play`, `def_yards_per_play_allowed`
- `red_zone_td_pct`, `early_down_success_rate`, `pace`
- `field_goal_make_pct`, `punt_net_yards`

Fails fast with clear error message showing missing/invalid fields.

**File**: `simulator/team_profile.py` (new method `_validate_schema()`)

---

## 📋 Still Pending (Not Yet Implemented)

### 8. Drive Length/Timing Improvements
**Issue**: Fixed 40s/25s per snap and pace-based drive caps don't target realistic possessions.

**Status**: Needs refactoring to possessions-first clock model targeting 10-15 possessions per team.

---

### 9. Fourth-Down Logic Enhancement
**Issue**: Heuristic logic doesn't vary by time, score, distance with learned curve.

**Status**: Needs lookup table or model based on yardline, distance, time, win-prob delta.

---

### 10. Weekly Injuries Module
**Issue**: No loading or application of inactives, snap-share downgrades, QB downgrade flags.

**Status**: Needs new module that:
- Loads weekly injury data
- Applies multipliers to QB downgrade, WR room depth, OL starters out, CB room attrition
- Modifies completion rate, INT rate, sack rate, run yards in `PlaySimulator`

---

### 11. Market Centering Consistency
**Issue**: Backtest uses market centering/calibration, but in-class betting method compares raw distributions.

**Status**: Needs refactoring to reuse same centering and calibrators everywhere.

---

## 🎯 Summary

**Fixed**: 7 critical bugs/issues
**Pending**: 4 enhancements (drive timing, 4th down logic, injuries, market centering)

The fixes address the most critical bugs that would cause silent failures or incorrect behavior. The pending items are enhancements that require more substantial refactoring.

