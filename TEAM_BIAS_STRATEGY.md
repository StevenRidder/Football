# Team Bias Strategy Guide

## The Problem: 100% Winner vs. 100% Loser

### What's Really Happening

When you see:
- **Team A**: 100% win rate (5W-0L when we bet on them)
- **Team B**: 0% win rate (0W-3L when we bet on them)  
- **Game**: Team A playing Team B

This creates a **conflicting signal** problem.

### Root Cause: Small Sample Size + Model Biases

Your model likely has:
1. **Uncorrected team-specific biases** - The model consistently over/under-estimates certain teams
2. **Small sample size** - 3-5 games is NOT enough data to declare a team "always right" or "always wrong"
3. **Contextual factors missing** - QB changes, injuries, schedule strength, home/away, etc.

## How to Handle This Scenario

### Option 1: **PASS on the Game** (Most Conservative)
If you see extreme conflicting biases (100% vs 0%), **don't bet**. The conflicting signals indicate:
- Your model doesn't have a clear edge
- One team is likely mismeasured
- The uncertainty is too high

**When to use**: Until you have 20+ games of data per team.

### Option 2: **Trust the Conviction Level** (Recommended for now)
Instead of team history, rely on:
1. **Conviction level** (HIGH/MEDIUM/LOW) from your current simulation
2. **Edge percentage** - Is the edge still strong despite the bias?
3. **Simulation-based probabilities** - What does the 2000-sim prediction say?

**Logic**: Your conviction system already accounts for:
- Market-centered predictions
- Calibrated probabilities
- Edge thresholds

If the model says "HIGH conviction, 20% edge" even with conflicting team biases, **the simulation is more reliable** than 5-game team history.

### Option 3: **Adjust Your Bet Size** (Risk Management)
When biases conflict:
- **Reduce bet size by 50%** for that game
- **Only bet HIGH conviction** games with conflicting biases
- **Skip MEDIUM/LOW** conviction games with conflicting biases

**Example**:
- Normal HIGH conviction bet: 5 units
- HIGH conviction with 100% winner team: 7.5 units (increase by 50%)
- HIGH conviction with conflicting biases (100% vs 0%): 2.5 units (reduce by 50%)

### Option 4: **Fix the Model** (Long-term solution)

**Immediate fixes**:
1. **Add team-level adjustments** - If GB is always wrong, investigate WHY
   - Are you missing QB injuries for GB?
   - Is GB's offensive line continuity wrong?
   - Is GB's defensive pressure rating off?

2. **Increase sample size threshold** - Only show team biases with 10+ games

3. **Add context** - Track team performance by:
   - Home vs Away
   - Spread size (favorites vs underdogs)
   - Division vs non-division games
   - Pre/post bye week

**Code changes needed**:
```python
# In your simulator/backtest code, add team adjustments:
if team == 'GB':
    home_score -= 3  # Penalize GB predictions
elif team == 'SEA':
    away_score -= 2  # SEA may be overrated
```

## Practical Decision Framework

```
IF game has team with 100% win rate vs team with 0% win rate:
    IF conviction == HIGH and edge >= 15%:
        BET with 50% normal size
    ELIF conviction == HIGH and edge >= 20%:
        BET with 75% normal size
    ELSE:
        PASS (conflicting signals too strong)
```

## What Your Current Data Says

### Perfect Records (RED FLAGS - Small Sample Bias):
- **LA**: 3W-0L spread (100%)
- **SEA**: 5W-0L spread (100%)
- **NO**: 6W-0L totals (100%)
- **GB**: 0W-3L spread (0%) ⚠️

### Strong Records (More Reliable - Larger Sample):
- **NE**: 5W-1L spread (83.3%)
- **DET**: 5W-1L spread (83.3%)
- **TEN**: 6W-1L totals (85.7%)

**Recommendation**: Don't heavily weight team bias until you have 15+ games per team.

## Next Steps

1. ✅ **For now**: Use the team bias indicators as **warning flags**, not decision drivers
2. ✅ **Trust your simulation**: If 2000 sims say HIGH conviction, bet it (maybe reduced size)
3. ⚠️ **Investigate GB, SEA, LA biases**: Why are they always right/wrong?
4. 📊 **Track outcomes**: After 10 more weeks, revisit team adjustments with better data

---

**Bottom Line**: When 100% winner plays 0% loser → **Trust the conviction level and edge, but reduce bet size by 50%**. Small sample sizes make team-level history unreliable.

