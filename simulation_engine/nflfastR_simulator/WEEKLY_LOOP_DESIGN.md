# Weekly Loop Design - Living Model

**Goal:** Self-updating system that learns coaching behavior and earns CLV every week.

---

## 📅 **Weekly Schedule**

### Monday (Early AM)
**Job:** `weekly_ingest`
- Ingest new play-by-play data from nflfastR
- Update QB pressure splits
- Update play-calling tendencies
- Update drive probabilities
- Recompute league priors
- **Output:** `artifacts/features/{season}_week{week}/`

### Monday (Late AM)
**Job:** `build_profiles`
- Apply roll-forward cutoff (week-1)
- Apply empirical Bayes shrinkage
- Generate team profiles with as_of stamps
- **Output:** `artifacts/features/{season}_week{week}/team_profiles.parquet`

### Tuesday, Wednesday, Friday
**Job:** `simulate_week`
- Load latest market lines (spread, total)
- Run 10k simulations per game
- Apply market centering
- Generate betting recommendations
- **Output:** `artifacts/predictions/{season}_week{week}/`

### Sunday (Post-games)
**Job:** `grade_and_clv`
- Load actual results
- Grade predictions
- Calculate CLV (bet line vs closing line)
- Update performance metrics
- **Output:** `artifacts/grading/{season}_week{week}/`

---

## 🎛️ **Five Control Buttons**

### 1. Update Data
**Action:** Run `weekly_ingest`  
**Trigger:** Manual or scheduled (Mon 6am)  
**Output:** New feature files  
**Idempotent:** Yes (overwrites existing week)

### 2. Rebuild Profiles
**Action:** Run `build_profiles`  
**Trigger:** After data update  
**Output:** `team_profiles.parquet`  
**Idempotent:** Yes

### 3. Run Simulations
**Action:** Run `simulate_week`  
**Trigger:** Manual (Tue/Wed/Fri) or on market line update  
**Output:** Predictions + recommendations  
**Idempotent:** Yes (can re-run with updated lines)

### 4. Publish Picks
**Action:** Export recommendations to betting interface  
**Trigger:** Manual approval after simulation  
**Output:** `picks_{season}_week{week}.csv`  
**Gate:** Requires CLV ≥ +0.3 in shadow mode

### 5. Grade & CLV
**Action:** Run `grade_and_clv`  
**Trigger:** After games complete  
**Output:** Performance report  
**Idempotent:** Yes

---

## 🔄 **Weekly Update Logic**

```python
# weekly_update.py

def weekly_update(season: int, week: int):
    """
    Full weekly update cycle.
    
    Steps:
    1. Ingest new play-by-play data
    2. Recompute QB splits, play-calling, drives
    3. Refit shrinkage priors (league + coaching-tree)
    4. Refit shape multipliers (rolling 6-week window)
    5. Re-run rent tests on last 4 weeks (sanity check)
    6. Emit picks + expected CLV
    7. Archive as_of snapshot
    """
    
    # 1. Ingest
    pbp_data = ingest_nflfastR(season, week)
    
    # 2. Recompute features
    qb_splits = compute_qb_pressure_splits(pbp_data, season, week)
    playcalling = compute_playcalling_tendencies(pbp_data, season, week)
    drives = compute_drive_probabilities(pbp_data, season, week)
    
    # 3. Refit priors
    league_qb_prior = qb_splits.groupby(["season","week"]).mean()
    league_playcalling_prior = playcalling.groupby(["season","week"]).mean()
    
    # 4. Refit shape (optional, only if drift detected)
    if detect_shape_drift(last_4_weeks):
        refit_shape_multipliers(rolling_window=6)
    
    # 5. Sanity check (rent tests on recent weeks)
    clv_last_4 = run_rent_tests(weeks=range(week-4, week))
    if clv_last_4 < 0:
        alert("CLV negative in last 4 weeks - investigate")
    
    # 6. Generate picks
    picks = simulate_and_recommend(season, week)
    
    # 7. Archive
    archive_snapshot(season, week, {
        "as_of": {"season": season, "week": week-1},
        "module_versions": get_module_versions(),
        "expected_clv": picks["expected_clv"].mean()
    })
    
    return picks
```

---

## 📊 **Audit Trail**

Every week logs:
1. **as_of stamp** - (season, week-1, timestamp)
2. **Module versions** - Which modules were active
3. **Expected CLV** - Pre-game prediction
4. **Realized CLV** - Post-game actual
5. **Shrinkage weights** - How much each QB/team was shrunk
6. **Shape drift** - Whether variance was refitted

**Storage:**
```
artifacts/
├── features/
│   ├── 2024_week1/
│   │   ├── qb_splits.parquet
│   │   ├── playcalling.parquet
│   │   ├── drives.parquet
│   │   └── team_profiles.parquet
│   ├── 2024_week2/
│   └── ...
├── predictions/
│   ├── 2024_week1/
│   │   ├── simulations.parquet
│   │   ├── recommendations.csv
│   │   └── metadata.json
│   └── ...
└── grading/
    ├── 2024_week1/
    │   ├── results.csv
    │   ├── clv_report.json
    │   └── performance.json
    └── ...
```

---

## 🚦 **CLV Gate (Shadow Mode)**

### Week 1-2: Shadow Picks
- Generate picks but don't bet
- Track expected vs realized CLV
- Require CLV ≥ +0.3 over 2 weeks

### Week 3+: Live Betting (if gate passes)
- Start with small stakes ($10-50)
- Track rolling 4-week CLV
- Stop if CLV < 0 for 2 consecutive weeks

### Kill Switch
If any of these trigger, stop betting:
- 2 consecutive weeks with CLV ≤ 0
- 4-week rolling CLV < +0.1
- Realized ATS < 48% over 50+ bets

---

## 🎯 **Success Metrics**

### Weekly
- Expected CLV (pre-game)
- Realized CLV (post-game)
- Brier score (ATS, totals)
- Module rent (each module's CLV contribution)

### Monthly
- Rolling 4-week CLV
- Win rate by edge bucket
- Reliability curve (monotone check)
- Shape drift (variance stability)

### Seasonal
- Total CLV vs Gaussian baseline
- ROI (if betting)
- Module survival (which modules still pay rent)

---

## 💡 **Key Principles**

1. **Evergreen** - Learns every week, doesn't decay
2. **Auditable** - Every decision has an as_of stamp
3. **Gated** - Must earn CLV to bet
4. **Modular** - Modules can be added/removed
5. **Reproducible** - Same seed + same as_of → same picks

---

## 🚀 **Implementation Priority**

### Phase 1: Core Loop (This week)
1. ✅ Calibration frozen
2. ⏳ Shrinkage + roll-forward integrated
3. ⏳ Market centering enabled
4. ⏳ Variance + tails validated

### Phase 2: Rent Tests (Next week)
1. Gaussian baseline
2. Module testing (QB, playcalling, drives)
3. CLV measurement
4. Module selection

### Phase 3: Weekly Automation (Week 3)
1. Schedule jobs
2. Wire 5 buttons
3. Shadow mode (2 weeks)
4. CLV gate

### Phase 4: Live Betting (Week 5+)
1. Small stakes
2. Track performance
3. Adjust as needed
4. Scale if successful

---

## 📝 **Status**

**Current:** Step 2b (integration) in progress  
**Next:** Steps 3-6 execution  
**Timeline:** 2-3 weeks to live betting  
**Goal:** CLV ≥ +0.3 sustained over 4+ weeks

This is the path from prototype → production → profitable.

