# Implementation Status - nflfastR Simulator

**Date:** 2025-10-30  
**Status:** Step 1 Complete, Step 2 Foundation Ready

---

## ✅ **COMPLETED: Core Foundation**

### Step 1: Calibration v1.0 - FROZEN
**Status:** ✅ COMPLETE  
**Time:** 2 hours  
**Files:**
- `simulator/calibrate_scoring.py` - 50-game validation harness
- `simulator/calibration.json` - Frozen parameters
- `simulator/play_simulator.py` - Explicit turnover subsystem
- `simulator/game_state.py` - Calibrated 4th down logic
- `CALIBRATION_V1_COMPLETE.md` - Full documentation

**Achievements:**
- ✅ Turnover%: 10.4% (target 10-12%)
- ✅ Total: 43.9 pts (target 42-46)
- ✅ TD%: 24.0% (target 22-24%)
- ✅ Explicit turnover subsystem with bounded rates
- ✅ Pressure outlets (scramble 18%, throwaway 10%, sack 28%)
- ✅ Calibrated scoring mix (TD/FG balance)

### Step 2: Shrinkage + Roll-Forward Infrastructure
**Status:** ✅ FOUNDATION COMPLETE  
**Time:** 30 min  
**Files:**
- `simulator/data_loader.py` - Roll-forward with as_of stamps
- `simulator/empirical_bayes.py` - EB shrinkage functions

**Ready to integrate:**
- `load_asof()` - Filters data to week-1
- `latest_by()` - Gets most recent row per group
- `shrink_rate()` - Core EB formula
- `shrink_qb_block()` - QB stat shrinkage

---

## ⏳ **IN PROGRESS: Integration**

### Step 2b: Integrate Shrinkage into TeamProfile
**Status:** ⏳ NEXT  
**Time Est:** 30-45 min

**Tasks:**
1. Update `TeamProfile._load_qb_stats()`:
   ```python
   from data_loader import load_asof, latest_by
   from empirical_bayes import shrink_qb_block
   
   # Load with roll-forward
   qb_hist = load_asof(qb_splits_df, ["passer"], ("season","week"), season, week)
   
   # Get league prior
   qb_league = qb_hist.groupby(["season","week"]).mean(numeric_only=True).reset_index()
   league_row = latest_by(qb_league, ["season","week"], ["season","week"]).iloc[-1]
   
   # Get QB row
   qb_row = latest_by(qb_hist[qb_hist["passer"] == self.qb_name],
                      ["passer"], ["season","week"]).iloc[0]
   
   # Apply shrinkage
   self.qb_stats = shrink_qb_block(qb_row, league_row, n_dropbacks)
   self.as_of = {"season": season, "week": week-1}
   ```

2. Update `TeamProfile._load_playcalling()`:
   ```python
   # Similar pattern with λ=50 for play-calling
   ```

3. Update `TeamProfile._load_epa()`:
   ```python
   # Apply roll-forward cutoff
   epa_data = load_asof(epa_df, ["team"], ("season","week"), season, week)
   ```

**Verification:**
- [ ] Calibration unchanged (run `calibrate_scoring.py`)
- [ ] as_of stamps present in all features
- [ ] No look-ahead bias (week-1 cutoff enforced)

---

## 📋 **REMAINING WORK**

### Step 3: Market Centering (30 min)
**Status:** Pending  
**Module exists:** `simulator/market_centering.py`

**Tasks:**
1. Update `GameSimulator.simulate_game()` to accept market lines
2. Apply `center_to_market()` after simulation
3. Validate mean within ±0.2 pts
4. Verify variance preserved

**Pass criteria:**
- Mean spread within ±0.2 of closing
- Mean total within ±0.2 of closing
- Std dev unchanged within ±3%

---

### Step 4: Variance + Tails (1 hour)
**Status:** Pending

**Tasks:**
1. Load historical spread/total variance
2. Compare simulated to historical
3. Tune two knobs only:
   - Per-drive explosion multiplier
   - Late-game tempo multiplier
4. Check key numbers (3,6,7,10,14,17) within ±2%

**Pass criteria:**
- Spread key numbers within ±2% of historical
- Total 37-48 band within ±3% of historical
- Blowouts (|margin| ≥ 14) within ±1.5% of historical

---

### Step 5: CLV Rent Tests (2 hours)
**Status:** Pending

**Tasks:**
1. Create Gaussian baseline (centered on market)
2. Score baseline: Brier, log loss, CRPS, CLV
3. Test modules one by one:
   - QB pressure splits
   - Play-calling tendencies
   - Drive probabilities
4. Keep only if CLV ≥ +0.3 AND Brier ≥ +2%

**Pass criteria:**
- Each module must earn CLV ≥ +0.3 pts
- Each module must improve Brier ≥ 2%
- Reliability curve must be monotone

---

### Step 6: Risk Gates + Timing + Holdout (4 hours)
**Status:** Pending

**Tasks:**
1. Add risk gates:
   - Wind ≥ 15 mph: no overs unless edge ≥ 2.0
   - QB status D/Q: skip or half-stake
   - Ref pace top/bottom decile: reduce stake 50%
2. Timing study (4 windows):
   - Monday open
   - Wednesday noon
   - Friday PM
   - T-90 minutes
3. Choose window by CLV
4. Freeze parameters
5. Run 2024 holdout

**Pass criteria:**
- CLV ≥ +0.3 on spreads with ≥ 200 bets
- Edge-bucket reliability is monotone
- Holdout CLV positive and stable

---

## 📊 **Time Estimates**

| Step | Task | Status | Time | Priority |
|------|------|--------|------|----------|
| 1 | Calibration | ✅ DONE | - | - |
| 2a | Shrinkage/loader modules | ✅ DONE | - | - |
| 2b | Integrate into TeamProfile | ⏳ NEXT | 45 min | HIGH |
| 2c | Verify calibration unchanged | ⏳ NEXT | 15 min | HIGH |
| 3 | Market centering | Pending | 30 min | HIGH |
| 4 | Variance + tails | Pending | 1 hour | MEDIUM |
| 5 | CLV rent tests | Pending | 2 hours | MEDIUM |
| 6 | Risk gates + timing + holdout | Pending | 4 hours | LOW |

**Total remaining:** ~8-9 hours

---

## 🎯 **Current State**

**We have:**
- ✅ Calibrated simulator matching NFL reality
- ✅ Explicit, bounded turnover subsystem
- ✅ Frozen parameters in `calibration.json`
- ✅ Shrinkage and roll-forward infrastructure ready
- ✅ Market centering module ready
- ✅ Clear roadmap for Steps 3-6

**Next action:**
1. Integrate shrinkage into `TeamProfile` (45 min)
2. Verify calibration unchanged (15 min)
3. Re-enable market centering (30 min)
4. Then march through Steps 4-6

---

## 💡 **Key Principles**

1. **No look-ahead** - Only use data through week-1
2. **Shrink thin samples** - EB prevents noise
3. **Center to market** - Mean is Vegas, edge is shape
4. **Modules pay rent** - CLV ≥ +0.3 or drop
5. **Validate on holdout** - 2024 is truth

---

## 🚀 **When Complete**

We will have a production-ready system that:
- Matches NFL reality (calibrated)
- Has no look-ahead bias (roll-forward)
- Shrinks thin samples (EB)
- Centers to market (mean anchored)
- Only uses modules that earn CLV (rent tests)
- Has been validated on holdout (2024)

**Then:** Go live with small stakes and track performance.

This is the path from prototype → production.

