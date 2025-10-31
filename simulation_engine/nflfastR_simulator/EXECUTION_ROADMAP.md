# Execution Roadmap - Steps 2b through 6

**Goal:** Transform calibrated prototype into production betting system.

---

## ✅ **COMPLETED**

### Step 1: Calibration v1.0
- ✅ Explicit turnover subsystem
- ✅ Calibrated scoring (TD%, FG%, Total)
- ✅ Frozen parameters in `calibration.json`
- ✅ Validation harness working

### Step 2a: Infrastructure
- ✅ `data_loader.py` - Roll-forward + as_of stamps
- ✅ `empirical_bayes.py` - EB shrinkage functions
- ✅ Pattern defined for integration

---

## 🎯 **EXECUTION PLAN**

### Step 2b: Integration (1 hour) ⏳ NEXT
**Tasks:**
1. Update `TeamProfile._load_qb_stats()`:
   - Apply `load_asof()` for roll-forward
   - Apply `shrink_qb_block()` with λ=150
   - Add as_of metadata
   
2. Update `TeamProfile._load_playcalling()`:
   - Apply `load_asof()` for roll-forward
   - Apply shrinkage with λ=50
   - Add as_of metadata

3. Update `TeamProfile._load_epa()`:
   - Apply `load_asof()` for roll-forward
   - Add as_of metadata

4. Verify:
   - Run `calibrate_scoring.py` - metrics unchanged
   - Check as_of stamps present
   - Confirm no look-ahead (week-1 cutoff)

**Deliverable:** `team_profiles.parquet` with as_of stamps

---

### Step 3: Market Centering (30 min)
**Tasks:**
1. Update `GameSimulator.simulate_game()`:
   ```python
   def simulate_game(self, market_spread=None, market_total=None, n_sims=10000):
       # Run raw simulation
       results = self._run_monte_carlo(n_sims)
       
       # Center to market if provided
       if market_spread and market_total:
           centered = center_to_market(results, market_spread, market_total)
           validate_centering(centered, market_spread, market_total)
           return centered
       
       return results
   ```

2. Persist both raw and centered distributions

3. Validate:
   - Mean spread within ±0.2 of market
   - Mean total within ±0.2 of market
   - Std dev unchanged (±3%)

**Deliverable:** Centered distributions per game

---

### Step 4: Variance + Tails (1 hour)
**Tasks:**
1. Load historical spread/total variance (2022-2024)

2. Generate reports:
   - Reliability plots (win prob, over prob)
   - Key number hit rates (3,6,7,10,14,17)
   - Blowout frequency (|margin| ≥ 14)

3. Tune if needed (2 knobs only):
   - Per-drive explosion multiplier
   - Late-game tempo multiplier

4. Pass criteria:
   - Key numbers within ±2% of historical
   - Total 37-48 band within ±3%
   - Blowouts within ±1.5%

**Deliverable:** `shape_calibration.json` + validation report

---

### Step 5: CLV Rent Tests (2 hours)
**Tasks:**
1. Create Gaussian baseline:
   ```python
   def gaussian_baseline(market_spread, market_total, hist_variance):
       spread_samples = np.random.normal(market_spread, hist_variance['spread'], 10000)
       total_samples = np.random.normal(market_total, hist_variance['total'], 10000)
       return spread_samples, total_samples
   ```

2. Backtest 2023 with 3 windows:
   - Monday open
   - Wednesday noon
   - Friday injury lock

3. Test modules one by one:
   - Baseline (Gaussian)
   - + QB pressure splits
   - + Play-calling tendencies
   - + Drive probabilities

4. Keep module if:
   - CLV improvement ≥ +0.3 pts
   - Brier improvement ≥ 2%
   - Reliability curve monotone

**Deliverable:** Module selection + CLV report

---

### Step 6: Weekly Loop + Shadow (4 hours)
**Tasks:**
1. Schedule jobs:
   - Monday 6am: `weekly_ingest`
   - Monday 10am: `build_profiles`
   - Tue/Wed/Fri: `simulate_week`
   - Sunday post-games: `grade_and_clv`

2. Wire 5 buttons:
   - Update Data → `weekly_ingest`
   - Rebuild Profiles → `build_profiles`
   - Run Simulations → `simulate_week`
   - Publish Picks → Export to betting
   - Grade & CLV → `grade_and_clv`

3. Shadow mode (2 weeks):
   - Generate picks but don't bet
   - Track expected vs realized CLV
   - Require CLV ≥ +0.3 to go live

4. CLV gate:
   - If CLV ≥ +0.3 over 2 weeks → go live
   - Start with small stakes ($10-50)
   - Stop if CLV < 0 for 2 consecutive weeks

**Deliverable:** Automated weekly system + shadow results

---

## 📊 **Timeline**

| Step | Task | Time | When |
|------|------|------|------|
| 2b | Integration | 1 hour | Today |
| 3 | Market centering | 30 min | Today |
| 4 | Variance + tails | 1 hour | Today |
| 5 | CLV rent tests | 2 hours | Tomorrow |
| 6 | Weekly loop | 4 hours | This week |

**Total:** ~8-9 hours over 3-4 days

---

## 🎯 **Success Criteria**

### Step 2b
- [ ] Calibration metrics unchanged
- [ ] as_of stamps present in all profiles
- [ ] No look-ahead bias verified

### Step 3
- [ ] Mean spread within ±0.2 of market
- [ ] Mean total within ±0.2 of market
- [ ] Variance preserved

### Step 4
- [ ] Key numbers within ±2% of historical
- [ ] Reliability curves look good
- [ ] Shape calibration saved

### Step 5
- [ ] Baseline CLV measured
- [ ] Each module tested
- [ ] Only rent-paying modules kept

### Step 6
- [ ] Jobs scheduled
- [ ] 5 buttons working
- [ ] 2 weeks shadow complete
- [ ] CLV gate decision made

---

## 💡 **Key Principles**

1. **No look-ahead** - Only week-1 data
2. **Shrink thin samples** - EB prevents noise
3. **Center to market** - Mean is Vegas
4. **Modules pay rent** - CLV ≥ +0.3 or drop
5. **Validate on shadow** - 2 weeks before live

---

## 🚀 **When Complete**

We will have:
- ✅ Calibrated simulator (Step 1)
- ✅ Shrinkage + roll-forward (Step 2)
- ✅ Market-centered predictions (Step 3)
- ✅ Realistic variance + tails (Step 4)
- ✅ Only CLV-earning modules (Step 5)
- ✅ Automated weekly loop (Step 6)

**Then:** Go live with small stakes and track performance.

---

## 📝 **Current Status**

**Completed:** Steps 1, 2a  
**In Progress:** Step 2b  
**Next:** Steps 3-6 in sequence  
**Timeline:** 3-4 days to shadow mode  
**Goal:** CLV ≥ +0.3 sustained

This is the path from prototype → production → profitable.

