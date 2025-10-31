# Calibration Iteration 1 - Results

## Changes Applied
1. ✅ Completion boost: +15%
2. ✅ Red zone TD multiplier: 2.5x (scaled by distance)
3. ✅ Explosive plays: 8% chance, log-normal distribution
4. ✅ Drive persistence: +10% after >4 yard gains
5. ✅ FG threshold: 70 yardline (opponent 30)
6. ✅ More aggressive 4th down

## Results

| Metric          | Baseline | After Tuning | Target    | Status |
|-----------------|----------|--------------|-----------|--------|
| Plays/drive     | 4.2      | 4.1          | 6.0-6.8   | ❌ FAIL |
| Drives/team     | 12.3     | 13.6         | 10-12     | ❌ FAIL |
| TD%             | 8.2%     | 9.6%         | 22-24%    | ❌ FAIL |
| FG%             | 31.6%    | 33.7%        | 8-10%     | ❌ FAIL |
| Turnover%       | 9.0%     | 10.7%        | 10-12%    | ✅ PASS |
| Pass rate       | 49.3%    | 50.5%        | 55-65%    | ❌ FAIL |
| Explosive%      | 5.8%     | 6.5%         | 10-12%    | ❌ FAIL |
| **Total points**| **37.6** | **45.8**     | **42-46** | **✅ PASS** |

## Analysis

### ✅ Good News
- **Total points PERFECT!** (45.8, target 42-46)
- **Turnover% in range** (10.7%, target 10-12%)
- Completion boost is working (more plays completing)
- Explosive plays improved (5.8% → 6.5%)

### ❌ Problems
1. **Drives too short** (4.1 plays) but **too many drives** (13.6)
   - This means drives are ending quickly but teams are getting the ball back fast
   - Likely: Too many punts, FGs, turnovers

2. **FG% got WORSE** (31.6% → 33.7%)
   - FG threshold change didn't work
   - Need to investigate why

3. **TD% barely improved** (8.2% → 9.6%)
   - Red zone boost not strong enough
   - Or not reaching red zone enough

4. **Pass rate too low** (50.5% vs 55-65%)
   - Need to increase pass tendency

## Root Cause Hypothesis

The simulator is **scoring the right total points** but via the **wrong mechanism**:
- Too many FGs (33.7% of drives)
- Not enough TDs (9.6% of drives)
- Drives too short (4.1 plays)

This suggests:
1. **FG logic is being called too often** - Need to check `should_attempt_fg()` vs `should_punt()`
2. **Red zone not being reached** - Need longer drives
3. **4th down logic might be wrong** - Check order of FG/punt decisions

## Next Iteration Plan

### Fix 1: Strengthen Red Zone TD Boost
- Current: 2.5x multiplier, scaled by distance
- New: 3.5x multiplier, apply to ALL plays in red zone (not just completions that reach goal)

### Fix 2: Reduce FG Attempts Drastically
- Current: FG if yardline >= 70
- New: FG if yardline >= 75 AND distance < 40 yards
- Go for it more on 4th-and-short in FG range

### Fix 3: Extend Drive Length
- Increase completion boost: 1.15x → 1.25x
- Increase persistence boost: 1.10x → 1.15x
- Reduce turnover rates slightly

### Fix 4: Increase Pass Rate
- Boost pass tendency in `decide_play_type()`
- Target: 60% pass rate (modern NFL)

## Expected Impact

| Metric          | Current | Expected | Target    |
|-----------------|---------|----------|-----------|
| Plays/drive     | 4.1     | 5.5-6.0  | 6.0-6.8   |
| TD%             | 9.6%    | 20-24%   | 22-24%    |
| FG%             | 33.7%   | 8-10%    | 8-10%     |
| Pass rate       | 50.5%   | 58-62%   | 55-65%    |
| Total points    | 45.8    | 43-46    | 42-46     |

**Next:** Apply these changes and re-test.

