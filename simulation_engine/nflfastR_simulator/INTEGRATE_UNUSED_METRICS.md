# Integrating Unused Metrics - ACTION PLAN

## Current Status

From `METRICS_USAGE_AUDIT.md`:
- ✅ **9 metrics USED**: EPA, QB Splits, all 6 PFF grades, Play-Calling
- ❌ **10 metrics LOADED BUT UNUSED**: YPP, YPA, Success Rate, ANY/A, Turnover Regression, Red Zone, Special Teams, Pace, Drive Probs, Situational

## ✅ JUST INTEGRATED

1. **YPA (Yards Per Pass Attempt)** - NOW USED
   - Location: `play_simulator.py` line 243
   - Adjusts pass completion yardage based on team YPA vs defense allowed YPA

2. **YPP (Yards Per Play)** - NOW USED  
   - Location: `play_simulator.py` line 334
   - Adjusts run yardage based on team YPP vs defense allowed YPP

3. **Red Zone TD%** - NOW USED
   - Location: `play_simulator.py` line 267
   - Adjusts TD probability inside opponent 20 based on team red zone conversion rate

## ⚠️ STILL NEED TO INTEGRATE

### 1. Turnover Regression Factor (HIGH PRIORITY)
- **Location**: Apply in `play_simulator.py` for INT/fumble rates
- **Usage**: Multiply turnover probabilities by `turnover_regression_factor`
- **Strategy**: Fade teams with unsustainable turnover luck (factor < 1.0)

### 2. Early-Down Success Rate (HIGH PRIORITY)
- **Location**: Apply in `game_simulator.py` for drive continuation
- **Usage**: Adjust probability of getting first down on early downs
- **Strategy**: Teams with higher early-down success extend drives more

### 3. ANY/A (Adjusted Net Yards per Attempt) (MEDIUM)
- **Location**: Could adjust QB efficiency in `play_simulator.py`
- **Usage**: Scale QB stats (completion %, yards) based on ANY/A vs defense allowed
- **Strategy**: ANY/A rolls up multiple factors into one efficiency metric

### 4. Pace (HIGH PRIORITY)
- **Location**: Apply in `game_simulator.py` for drive length
- **Usage**: Use `offense.pace` to determine average plays per drive
- **Strategy**: Faster-paced teams = more plays per drive = more scoring opportunities

### 5. Special Teams (MEDIUM)
- **Punt Net Yards**: Adjust field position after punts
- **FG Make %**: Adjust field goal success rate
- **Location**: `play_simulator.py` `simulate_punt()` and `simulate_field_goal()`

### 6. Drive Probabilities (LOW)
- **Location**: `game_simulator.py` for drive outcomes
- **Usage**: Use field position buckets to determine TD/FG/Punt probability
- **Note**: Currently using hardcoded logic - could use actual team data

### 7. Situational Factors (LOW)
- **Location**: Load in `TeamProfile.__init__()` and apply in `GameSimulator`
- **Usage**: Rest days, weather, dome status affect pace/variance
- **Note**: Not yet loaded into TeamProfile

## Implementation Order

1. **Turnover Regression** - Most immediate impact
2. **Early-Down Success** - Affects drive structure significantly  
3. **Pace** - Controls drive length
4. **Special Teams** - Field position matters
5. **ANY/A** - Efficiency metric
6. **Drive Probabilities** - Fine-tuning
7. **Situational Factors** - Nice to have

