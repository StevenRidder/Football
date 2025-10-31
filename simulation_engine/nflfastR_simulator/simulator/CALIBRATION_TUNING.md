# Calibration Tuning Plan

## 📊 Current State (Baseline)

From 50-game test:
- **Plays/drive**: 4.2 (target: 6.4) - Need 1.52x
- **TD%**: 8.2% (target: 23%) - Need 2.79x
- **FG%**: 31.6% (target: 9%) - Too high!
- **Total**: 37.6 pts (target: 44) - Close
- **Explosive%**: 5.8% (target: 11%) - Need 1.9x

## 🎯 Tuning Adjustments

### 1. Extend Drive Length (4.2 → 6.4 plays)

**Root cause:** Drives ending too early (punts, FGs, turnovers)

**Fixes:**
- ✅ Increase short-yardage conversion (+15%)
- ✅ Raise 2nd/3rd down success rates
- ✅ Add drive persistence bias (momentum)
- ✅ Reduce early-drive turnovers

**Implementation:**
- `play_simulator.py`: Adjust completion rates, yards distributions
- Target: 6.4 ± 0.3 plays/drive

### 2. Fix Scoring Mix (31.6% FG → 9%, 8.2% TD → 23%)

**Root cause:** Too conservative in red zone, too many FG attempts

**Fixes:**
- ✅ Lower FG attempt rate (only inside opponent 30)
- ✅ Increase red zone TD conversion (2.5x multiplier)
- ✅ Go for it more on 4th-and-short near midfield
- ✅ Reduce punt frequency in opponent territory

**Implementation:**
- `game_state.py`: Adjust `should_attempt_fg()` and `should_punt()`
- `play_simulator.py`: Boost red zone success rates
- Target: 23% ± 2% TD, 9% ± 1% FG

### 3. Boost Explosive Plays (5.8% → 11%)

**Root cause:** Not enough deep passes, YAC too conservative

**Fixes:**
- ✅ Increase deep pass success (clean pocket: 10% → 18%)
- ✅ Add YAC bursts on completions >15 yards
- ✅ Inject rare 30-50 yard gains (~2% rate)
- ✅ Use log-normal distribution for big plays

**Implementation:**
- `play_simulator.py`: Adjust yards distribution, add explosive play logic
- Target: 11% ± 1% explosive rate

## 📋 Validation Targets

| Metric       | Current | Target | Tolerance | Status |
|--------------|---------|--------|-----------|--------|
| Plays/drive  | 4.2     | 6.4    | ±0.3      | ❌     |
| TD%          | 8.2%    | 23%    | ±2%       | ❌     |
| FG%          | 31.6%   | 9%     | ±1%       | ❌     |
| Total points | 37.6    | 44     | ±1        | ⚠️     |
| Explosive%   | 5.8%    | 11%    | ±1%       | ❌     |

## 🔧 Implementation Order

1. **Fix scoring mix first** (biggest impact on total points)
   - Adjust FG/punt thresholds
   - Boost red zone TD rate

2. **Extend drive length** (enables more scoring opportunities)
   - Increase conversion rates
   - Add momentum bias

3. **Add explosive plays** (increases variance, realism)
   - Adjust yards distributions
   - Add big play logic

4. **Validate** (run 50-game test after each change)
   - Check all 5 metrics
   - Iterate until all pass

## 🎯 Success Criteria

**Pass when ALL metrics in tolerance:**
- Plays/drive: 6.1-6.7
- TD%: 21-25%
- FG%: 8-10%
- Total: 43-45 pts
- Explosive%: 10-12%

**Then:**
- Save constants to `calibration.json`
- Lock calibration
- Move to Step 2: Shrinkage + Roll-Forward

## 📝 Notes

- Each tuning round: 50 games (~30 seconds)
- Expect 3-5 iterations to converge
- Log all changes for reproducibility
- Don't overfit - aim for tolerance, not perfection

