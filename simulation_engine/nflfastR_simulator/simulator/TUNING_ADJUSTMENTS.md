# Calibration Tuning Adjustments Applied

## Changes Made

### 1. Game State (`game_state.py`)

**FG Attempt Threshold:**
- OLD: `yardline >= 65` (inside opponent 35)
- NEW: `yardline >= 70` (inside opponent 30)
- **Effect:** Reduces FG attempts from 31.6% → ~10%

**Punt Logic (More Aggressive):**
- Added: Go for it on 4th-and-3 in opponent territory (was 4th-and-2)
- Added: Go for it on 4th-and-1 anywhere past own 40
- **Effect:** More drives continue, fewer punts

### 2. Play Simulator (`play_simulator.py`)

**Need to apply these changes:**

#### A. Boost Completion Rates (+15%)
```python
# In simulate_pass_play(), after getting qb_stats:
# Apply calibration boost
completion_boost = 1.15  # +15% to extend drives
qb_stats_adjusted = qb_stats.copy()
qb_stats_adjusted['completion_pct'] = min(0.85, qb_stats['completion_pct'] * completion_boost)
```

#### B. Red Zone TD Boost (2.5x)
```python
# In _check_touchdown() or simulate_pass_play():
if game_state.is_red_zone:
    # Boost TD probability in red zone
    td_multiplier = 2.5
    # Apply to scoring logic
```

#### C. Explosive Plays (10% → 18% when clean)
```python
# In simulate_pass_play(), for completions:
# Add explosive play logic
if not is_pressure and np.random.random() < 0.08:  # 8% chance of explosive
    # Draw from log-normal for big play
    yards = int(np.random.lognormal(3.0, 0.8))  # Mean ~20, tail to 50+
    yards = np.clip(yards, 15, 80)
```

#### D. Drive Persistence Bias
```python
# Track recent success in GameState
# If last play gained >4 yards, boost next play success by 10%
```

## Next Steps

1. **Apply remaining changes to `play_simulator.py`**
2. **Run 50-game calibration test**
3. **Check metrics against targets**
4. **Iterate if needed**

## Expected Results After Tuning

| Metric       | Before | After (Expected) | Target |
|--------------|--------|------------------|--------|
| Plays/drive  | 4.2    | 6.2-6.6          | 6.4    |
| TD%          | 8.2%   | 21-25%           | 23%    |
| FG%          | 31.6%  | 8-10%            | 9%     |
| Total points | 37.6   | 43-45            | 44     |
| Explosive%   | 5.8%   | 10-12%           | 11%    |

## Implementation Status

- [x] FG threshold adjusted
- [x] Punt logic more aggressive
- [ ] Completion rate boost
- [ ] Red zone TD multiplier
- [ ] Explosive play logic
- [ ] Drive persistence bias

**Next:** Apply remaining changes to `play_simulator.py` and re-test.

