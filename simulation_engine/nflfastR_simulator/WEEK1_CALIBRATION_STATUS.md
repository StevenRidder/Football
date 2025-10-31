# Week 1 Calibration Status

## 🎯 **Goal**: Match NFL Reality

Target metrics:
- Plays/drive: 6.0-6.8
- Drives/team: 10-12
- TD%: 22-24%
- FG%: 8-10%
- Total: 42-46 pts

## 📊 **Progress Tracking**

### Iteration 0 (Baseline)
| Metric       | Value | Target    | Status |
|--------------|-------|-----------|--------|
| Plays/drive  | 4.2   | 6.0-6.8   | ❌     |
| TD%          | 8.2%  | 22-24%    | ❌     |
| FG%          | 31.6% | 8-10%     | ❌     |
| Total        | 37.6  | 42-46     | ❌     |

### Iteration 1 (First Tuning)
**Changes:**
- Completion boost: +15%
- Red zone TD: 2.5x
- Explosive: 8%
- FG threshold: 70

| Metric       | Value | Target    | Δ      | Status |
|--------------|-------|-----------|--------|--------|
| Plays/drive  | 4.1   | 6.0-6.8   | -0.1   | ❌     |
| TD%          | 9.6%  | 22-24%    | +1.4%  | ❌     |
| FG%          | 33.7% | 8-10%     | +2.1%  | ❌ WORSE |
| Total        | 45.8  | 42-46     | +8.2   | ✅     |

### Iteration 2 (Aggressive Tuning)
**Changes:**
- Completion boost: +25% (was +15%)
- Red zone TD: 4.0x (was 2.5x)
- Explosive: 12% (was 8%)
- FG threshold: 75 + distance check (was 70)
- Persistence: +15% (was +10%)

| Metric       | Value | Target    | Δ from I1 | Status |
|--------------|-------|-----------|-----------|--------|
| Plays/drive  | 4.5   | 6.0-6.8   | +0.4      | ✅ Better |
| TD%          | 13.7% | 22-24%    | +4.1%     | ✅ Better |
| FG%          | 30.1% | 8-10%     | -3.6%     | ✅ Better |
| Total        | 47.0  | 42-46     | +1.2      | ⚠️  Slightly high |

## 📈 **Trend Analysis**

**Good trends:**
- TD% climbing (8.2% → 9.6% → 13.7%) ✅
- FG% decreasing (31.6% → 33.7% → 30.1%) ✅
- Plays/drive increasing (4.2 → 4.1 → 4.5) ✅

**Issues:**
- Still need **~10% more TD%** (13.7% → 23%)
- Still need **~20% less FG%** (30.1% → 9%)
- Still need **~2 more plays/drive** (4.5 → 6.4)

## 🔧 **Next Iteration Plan (Iteration 3)**

### Strategy
The FG% is STILL way too high. Root cause: The `should_attempt_fg()` logic is being called before `should_punt()`, so teams are kicking FGs instead of going for it or punting.

### Changes
1. **Drastically reduce FG attempts**
   - Only kick inside opponent 20 (yardline >= 80)
   - Only if 4th-and-long (ydstogo > 5)
   
2. **Boost TD conversion even more**
   - Red zone TD: 4.0x → 5.0x
   - Apply to ALL red zone plays, not just passes that reach goal
   
3. **Extend drives more**
   - Completion boost: 1.25x → 1.30x
   - Reduce INT rate by 30%
   
4. **Increase pass rate**
   - Boost pass tendency to 60%

### Expected Results
| Metric       | Current | Expected | Target    |
|--------------|---------|----------|-----------|
| Plays/drive  | 4.5     | 5.8-6.2  | 6.0-6.8   |
| TD%          | 13.7%   | 21-25%   | 22-24%    |
| FG%          | 30.1%   | 8-12%    | 8-10%     |
| Total        | 47.0    | 43-46    | 42-46     |

## 💡 **Key Insights**

1. **Total points are easy to hit** - We've been at 45.8 and 47.0, both close to target
2. **Scoring mix is the challenge** - Converting FGs → TDs is the main issue
3. **Iterative tuning works** - Each iteration moves us closer
4. **Need aggressive changes** - Small tweaks aren't enough, FG% needs to drop 20%

## ⏱️ **Time Estimate**

- Iteration 3: 10 min (apply changes + test)
- Iteration 4 (if needed): 10 min
- Freeze calibration: 5 min
- **Total remaining: ~25 min**

Then move to Step 2: Shrinkage + Roll-Forward

## 🚀 **Bottom Line**

**We're on track.** The calibration process is working. Each iteration brings us closer. The total points are already in range, we just need to fix the scoring mix (more TDs, fewer FGs).

**Next action:** Apply Iteration 3 changes now.

