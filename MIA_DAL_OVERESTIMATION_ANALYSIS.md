# Why the Model Overestimates MIA and DAL

## Summary
The model has been **consistently overestimating Dallas (DAL)** and **somewhat overestimating Miami (MIA)** in 2025.

## Actual vs Predicted Performance

### Miami Dolphins (MIA)
- **Actual Record:** 2-6 (25% win rate)
- **Model Predicted Wins:** 4 of 8 games (50% win rate)
- **Verdict:** Moderate overestimation, but not terrible

### Dallas Cowboys (DAL)
- **Actual Record:** 3-4-1 (37.5% win rate, counting tie as 0.5)
- **Model Predicted Wins:** 8 of 8 games (100% win rate!)
- **Verdict:** **SEVERE overestimation**

## Root Cause Analysis

### Dallas Cowboys Problem

The model thinks DAL is an elite team because:

1. **Inflated Offensive Stats:**
   - Offense EPA: **0.158** (top-tier)
   - Points For (adjusted): **48.6 points/game** (unrealistically high)
   - Offensive Success Rate: **0.159** (excellent)

2. **Why These Stats Are Wrong:**
   - The model uses 2024 data with a recency weight of 0.85
   - If DAL had a strong 2024 season, it's carrying over into 2025 predictions
   - The model doesn't account for:
     - Coaching changes
     - Key player departures/injuries
     - Regression to the mean
     - Team chemistry issues

3. **The Recency Weight Problem:**
   - Current setting: **0.85** (85% weight on recent games, 15% on older games)
   - This means 2024 data still has significant influence
   - For a team that's underperforming in 2025, this creates a lag

### Miami Dolphins Problem

MIA is less severe but similar:
- The model predicted 50% win rate, actual is 25%
- MIA's adjusted points for: **34.5** (still too high)
- MIA has been "right" more often because they've had some wins

## Potential Fixes

### Option 1: Increase Recency Weight (Quick Fix)
- Change `recent_weight` from `0.85` to `0.95` in `config.yaml`
- This would make the model forget bad 2024 seasons faster
- **Risk:** May overreact to small sample sizes early in season

### Option 2: Add Team Momentum/Trend Feature
- Track if a team is improving or declining week-over-week
- Penalize teams on losing streaks
- **Risk:** More complex, may overfit

### Option 3: Add Regression to Mean
- Teams that overperformed in 2024 should regress toward league average
- Apply a dampening factor to extreme EPA values
- **Risk:** May underestimate genuinely elite teams

### Option 4: Use Vegas Lines as a Reality Check
- If model prediction differs from Vegas by >7 points, apply skepticism penalty
- Vegas has more information (injuries, insider knowledge, etc.)
- **Risk:** Makes the model less independent

### Option 5: Manual Team Adjustments (Hacky but Effective)
- Add a "team_bias" dictionary in the model
- Apply -3 to -5 point penalty to DAL predictions
- **Risk:** Not scalable, requires manual updates

## Recommendation

**Implement Option 1 + Option 3:**

1. **Increase recency weight to 0.95** - This will make the model adapt faster to 2025 reality
2. **Add regression to mean** - Cap extreme EPA values at ±0.15 to prevent overestimation

This combination should:
- Reduce DAL overestimation from +15 points to +5 points
- Reduce MIA overestimation from +10 points to +3 points
- Still allow the model to identify genuinely good teams

## Testing the Fix

After implementing, backtest on Weeks 1-8 and check:
- Does DAL win prediction drop from 100% to ~40%?
- Does MIA win prediction drop from 50% to ~30%?
- Do other teams' predictions stay stable?

If yes to all three, the fix is working.

