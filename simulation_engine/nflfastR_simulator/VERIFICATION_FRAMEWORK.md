# Verification Framework - Trust But Verify

**Goal:** Make results repeatable, falsifiable, and comparable to a dumb baseline.

---

## 🎯 **Three Truths That Cannot Be Sweet-Talked**

### 1. CLV (Closing Line Value)
**Definition:** Average movement from pick line to closing line  
**Target:** ≥ +0.3 points over 100+ bets  
**Failure:** CLV < 0 means not beating the market

**Measurement:**
```python
clv = (closing_line - pick_line) * sign(pick_side)
mean_clv = clv.mean()
```

### 2. Brier Score
**Definition:** Probability calibration for ATS and totals  
**Target:** Beat Gaussian baseline by ≥ 2%  
**Baseline:** Gaussian centered on Vegas with historical variance

**Measurement:**
```python
brier_model = ((prob - outcome)**2).mean()
brier_baseline = ((gaussian_prob - outcome)**2).mean()
improvement = brier_baseline - brier_model
```

### 3. Reproducibility
**Definition:** Same inputs → same outputs  
**Target:** Within ±0.1 pts on mean, ±3% on variance  
**Failure:** Results change on re-run

**Verification:**
```bash
# Run 1
make backtest YEAR=2023 > run1.log

# Run 2 (same SHA, same seed)
make backtest YEAR=2023 > run2.log

# Compare
diff artifacts/run1/manifest.json artifacts/run2/manifest.json
```

---

## 📦 **Artifact Requirements**

Every run MUST emit:

### Manifest (`manifest.json`)
```json
{
  "git_sha": "abc123...",
  "git_dirty": false,
  "timestamp": "2025-10-30T12:00:00Z",
  "seed": 42,
  "calibration_hash": "sha256:...",
  "data_snapshots": {
    "nflfastR": "2024-10-30",
    "rolling_epa": "sha256:..."
  },
  "as_of": {
    "season": 2023,
    "week": 17
  }
}
```

### Outputs
- `distributions.parquet` - Per-game raw + centered
- `picks.csv` - Weekly recommendations
- `clv.csv` - CLV by game, week, window
- `brier.csv` - Brier scores vs baseline
- `calibration.json` - Frozen parameters
- `key_numbers.csv` - Hit rates at 3,6,7,10,14,17
- `summary.html` - Human-readable report

### Hashes
- SHA256 for each artifact
- Stored in `manifest.json`
- Tampering is obvious

---

## ✅ **Merge Gates (CI/CD)**

### Gate 1: Unit Tests
**Requirement:** ≥ 90% coverage  
**Scope:** Simulator core, EB, market centering  
**Command:** `make test`

**Must pass:**
- `test_play_simulator.py`
- `test_turnover_subsystem.py`
- `test_empirical_bayes.py`
- `test_market_centering.py`
- `test_data_loader.py`

### Gate 2: Golden Tests
**Requirement:** Fixed games reproduce exactly  
**Tolerance:** ±0.1 pts mean, ±3% variance  
**Command:** `make golden`

**Golden games:**
- KC @ BUF 2024 Week 1
- BAL @ CIN 2024 Week 5
- SF @ DAL 2024 Week 8

### Gate 3: Backtest Gates
**Requirement:** Beat baseline on 2023  
**Command:** `make backtest YEAR=2023`

**Must pass:**
- CLV ≥ +0.3 points
- Brier improvement ≥ 2%
- Key numbers within bands

### Gate 4: No Look-Ahead
**Requirement:** All as_of ≤ game kickoff  
**Command:** `make rollforward`

**Check:**
```python
for game in games:
    for feature in game.features:
        assert feature.as_of <= game.kickoff
```

---

## 🚦 **Shadow Picks Scorekeeping**

### Week 1-2: Shadow Mode
**Publish:** Mon, Wed, Fri  
**Track:** CLV vs eventual close  
**Display:**

| Window | Bets | CLV | Brier | ROI |
|--------|------|-----|-------|-----|
| Mon Open | 12 | +0.4 | 0.245 | - |
| Wed Noon | 15 | +0.6 | 0.238 | - |
| Fri Lock | 18 | +0.3 | 0.242 | - |

**Decision:** If Wed CLV consistently best → use Wed window

---

## 🎛️ **Five Buttons (UI)**

### 1. Update Data
**Shows:**
- New data ranges
- SHA256 hashes
- as_of stamps

### 2. Rebuild Profiles
**Shows:**
- Shrinkage weights per team
- as_of stamps
- League priors used

### 3. Run Simulations
**Shows:**
- Distributions (raw + centered)
- Means locked to market (±0.2)
- Variance vs last week

### 4. Publish Picks
**Shows:**
- Edges by game
- Stake sizing
- "Rent badge" for each module

### 5. CLV and Grading
**Shows:**
- Live CLV vs close
- Final ROI
- Locks after grading

**Rule:** If any button hides logs/artifacts → pause betting

---

## 🔍 **Four Spot Checks (Every Run)**

### 1. Centering Check
**Requirement:** Simulated means match market  
**Tolerance:** ±0.2 points  
**Failure:** Fix centering before anything else

```python
assert abs(sim_spread.mean() - market_spread) < 0.2
assert abs(sim_total.mean() - market_total) < 0.2
```

### 2. Variance Sanity
**Requirement:** Spread SD in 10-13 range  
**Failure:** Flag if collapses or explodes

```python
assert 10 <= sim_spread.std() <= 13
```

### 3. Key-Number Hits
**Requirement:** Rates at 3,6,7,10,14,17 within ±2%  
**Failure:** Recalibrate tails

```python
for key_num in [3, 6, 7, 10, 14, 17]:
    sim_rate = (abs(sim_spread - key_num) < 0.5).mean()
    hist_rate = historical_rates[key_num]
    assert abs(sim_rate - hist_rate) < 0.02
```

### 4. Roll-Forward Audit
**Requirement:** All features ≤ game-1 week  
**Failure:** Stop and fix look-ahead

```python
for game in sample(games, 5):
    latest_date = max(f.as_of for f in game.features)
    assert latest_date <= game.kickoff - timedelta(days=7)
```

---

## 🚨 **BS Detector Checklist**

### Red Flags (Stop Immediately)

❌ **Results improve only on MAE, not CLV**  
❌ **No Gaussian baseline in comparison**  
❌ **No manifest with git SHA**  
❌ **as_of timestamps missing or after kickoff**  
❌ **Backtests change on re-run**  
❌ **Pick sheets without closing line**  
❌ **Code diffs without new tests**  
❌ **Hand-edited notebooks instead of scripts**

### Green Flags (Proceed)

✅ **CLV positive vs Gaussian baseline**  
✅ **Manifest with SHA + hashes**  
✅ **Reproducible within tolerance**  
✅ **as_of stamps enforced**  
✅ **Unit tests ≥ 90% coverage**  
✅ **Golden tests pass**  
✅ **Roll-forward audit clean**  
✅ **Closing lines tracked**

---

## 📋 **One-Command Verification**

### What to Ask For:

> "Give me `make backtest YEAR=2023` and `make holdout YEAR=2024` that produce:
> 
> 1. `artifacts/<timestamp>/summary.html`
> 2. `artifacts/<timestamp>/manifest.json` with git SHA, seed, data hashes
> 
> The summary must show:
> - CLV vs Gaussian baseline
> - Brier vs baseline
> - Key-number calibration
> - Five spot checks (centering, variance, key numbers, roll-forward)
> 
> I will run these on a fresh machine. If my outputs differ beyond your tolerances, we stop and fix reproducibility."

### Expected Workflow:

```bash
# Clean start
make clean all

# Dev backtest
make backtest YEAR=2023

# Generate report
make report

# View results
open artifacts/*/summary.html

# Verify
make verify

# Holdout test
make holdout YEAR=2024

# Compare
diff artifacts/run1/manifest.json artifacts/run2/manifest.json
```

---

## 💰 **Payment Gates**

### Gate 1: Reproducibility
**Pass:** Same SHA + seed → same results (±tolerance)  
**Fail:** Fix before any payment

### Gate 2: Beat Baseline
**Pass:** CLV ≥ +0.3 AND Brier ≥ +2% vs Gaussian  
**Fail:** No edge, no payment

### Gate 3: Calibration
**Pass:** All four spot checks pass  
**Fail:** Fix calibration before payment

### Gate 4: Roll-Forward
**Pass:** No look-ahead bias detected  
**Fail:** Fix temporal leakage before payment

### Gate 5: Shadow Performance
**Pass:** 2 weeks shadow with CLV ≥ +0.3  
**Fail:** No live betting, no payment

---

## 🎯 **Bottom Line**

**Tie pay to gates, not prose.**

If the code:
- ✅ Produces reproducible artifacts
- ✅ Beats Gaussian baseline on CLV
- ✅ Passes calibration audits
- ✅ Proves roll-forward discipline

**Then it's real.**

If not, it's theater.

---

## 📊 **Verification Status**

| Check | Status | Notes |
|-------|--------|-------|
| Makefile | ✅ Created | One-command verification |
| Unit tests | ⏳ TODO | Need ≥90% coverage |
| Golden tests | ⏳ TODO | Need 3 fixed games |
| Backtest script | ⏳ TODO | Need run_backtest.py |
| Report generator | ⏳ TODO | Need generate_report.py |
| Roll-forward audit | ⏳ TODO | Need audit script |
| Calibration checks | ⏳ TODO | Need check script |

**Next:** Build the verification scripts to make `make verify` work.

