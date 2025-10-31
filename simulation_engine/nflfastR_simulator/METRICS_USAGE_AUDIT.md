# Metrics Usage Audit

## Strategy Document Metrics Status

### ✅ LOADED AND USED

1. **EPA (Off/Def)** - `off_epa`, `def_epa`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for yards adjustments (pass and run)
   - Location: `play_simulator.py` lines 303-304 (run plays)

2. **QB Pressure Splits** - `qb_stats['clean']`, `qb_stats['pressure']`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for pass outcomes under pressure
   - Location: `play_simulator.py` lines 112-116

3. **PFF OL Pass Block Grade** - `ol_grade`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for pressure calculation
   - Location: `play_simulator.py` lines 86-108

4. **PFF DL Pass Rush Grade** - `dl_grade`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for pressure calculation
   - Location: `play_simulator.py` lines 86-108

5. **PFF OL Run Block Grade** - `ol_run_grade`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for run yardage adjustments
   - Location: `play_simulator.py` lines 309-316

6. **PFF DL Run Defense Grade** - `dl_run_grade`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for run yardage adjustments
   - Location: `play_simulator.py` lines 309-316

7. **PFF Passing Offense Grade** - `passing_grade`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for completion rate adjustments
   - Location: `play_simulator.py` lines 203-216

8. **PFF Coverage Grade** - `coverage_grade`
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator for completion rate and explosive play adjustments
   - Location: `play_simulator.py` lines 203-216, 225-229

9. **Play-Calling Tendencies** - `playcalling` DataFrame
   - ✅ Loaded in TeamProfile
   - ✅ Used in PlaySimulator to decide pass/run
   - Location: `play_simulator.py` lines 55-60

10. **Pace** - `pace` (plays per drive)
    - ✅ Loaded in TeamProfile
    - ⚠️ NOT USED - Should be used in GameSimulator for drive length

### ⚠️ LOADED BUT NOT YET USED

1. **Yards Per Play** - `off_yards_per_play`, `def_yards_per_play_allowed`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Should adjust yards gained distributions

2. **Yards Per Pass Attempt** - `off_yards_per_pass_attempt`, `def_yards_per_pass_allowed`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Should adjust pass completion yardage

3. **Early-Down Success Rate** - `early_down_success_rate`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Should modify drive continuation probability

4. **ANY/A** - `off_anya`, `def_anya_allowed`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Could adjust QB efficiency or pass success rates

5. **Turnover Regression Factor** - `turnover_regression_factor`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Should apply efficiency multiplier to reduce turnover luck

6. **Red Zone Trips Per Game** - `red_zone_trips_per_game`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Could adjust drive structure

7. **Red Zone TD %** - `red_zone_td_pct`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Should adjust TD probability inside opponent 20

8. **Special Teams** - `punt_net_yards`, `field_goal_make_pct`
   - ✅ Loaded in TeamProfile
   - ❌ NOT USED - Should adjust field position on punts and FG make rates

9. **Drive Probabilities** - `drive_probs` DataFrame
   - ✅ Loaded in TeamProfile
   - ⚠️ NOT USED - Should be used in GameSimulator for drive outcomes

10. **Situational Factors** - Rest days, weather, dome
    - ✅ Extracted to CSV
    - ❌ NOT LOADED in TeamProfile
    - ❌ NOT USED

## Summary

### Metrics Used: 9/19 (47%)
- ✅ All PFF grades (6 grades) - USED
- ✅ EPA (off/def) - USED  
- ✅ QB Splits - USED
- ✅ Play-Calling - USED
- ⚠️ Pace - LOADED but not used
- ❌ All new metrics (YPP, Success, ANY/A, Turnovers, Red Zone, ST) - LOADED but not used
- ❌ Drive Probabilities - LOADED but not used
- ❌ Situational Factors - NOT LOADED

## Action Items

1. **CRITICAL**: Integrate new metrics into PlaySimulator
   - Use YPP/YPA for yards distributions
   - Use early-down success for drive continuation
   - Use turnover regression factor for efficiency multiplier
   - Use red zone stats for TD probability inside 20

2. **HIGH**: Use pace in GameSimulator for drive length

3. **MEDIUM**: Load and use situational factors (rest, weather, dome)

4. **LOW**: Use drive probabilities in GameSimulator

