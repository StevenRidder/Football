# Proper Scoring Framework - No CLV Phantoms

**Date:** 2025-10-30  
**Status:** ✅ READY TO TEST

---

## 🎯 **THE NEW SCORECARD**

### Forget CLV. Judge by actual betting performance.

**Why:**
- Market barely moves → CLV is a phantom
- What matters: **Do we make money at posted prices?**
- Truth serum: **Proper scoring rules + ROI**

---

## 📊 **SIX TESTS**

### 1. Beat the Market's Probabilities
**Metric:** Log loss & Brier score vs vig-stripped market

**How:**
- Convert odds to implied probabilities
- Remove vig (assume 4.5% hold)
- Compare model probs to market probs
- Score with log loss and Brier

**Target:** ≥1-2% log loss improvement OR ≥2-3% Brier improvement

**Why:** This asks: "Given the same price, did our probabilities describe reality better?"

---

### 2. Prove Money on the Table
**Metric:** ROI at posted prices

**How:**
- Calculate EV = p_model × payout - (1 - p_model) × stake
- Only bet when EV ≥ +3%
- Track: ROI, Kelly growth, Sharpe, max drawdown

**Target:** Positive ROI, positive Kelly growth, stable Sharpe

**Why:** If the line never moves, this is the truth.

---

### 3. Calibration & Sharpness
**Metric:** Reliability curves

**How:**
- Plot: when we say 58%, do we win 58%?
- Check: are our probs more spread than market's?
- Verify: after centering to spread/total

**Target:** Monotone reliability, sharper than market

**Why:** Good probabilities = good bets.

---

### 4. Monotonicity & Lift
**Metric:** Win rate by edge bucket

**How:**
- Bucket games by model edge (0-2%, 2-4%, 4-6%, etc.)
- Track realized win rate per bucket
- Compute Spearman correlation

**Target:** Win rate rises with edge

**Why:** Model's ranking power matters.

---

### 5. Key-Number Respect
**Metric:** Spread distribution shape

**How:**
- Check frequencies at 3, 6, 7, 10, 14, 17
- Verify spread SD in realistic band
- Validate after centering

**Target:** Within ±2% of historical

**Why:** If we cheat the shape, we leak money live.

---

### 6. Decision Thresholds
**Metric:** Robustness across EV thresholds

**How:**
- Test EV ≥ 2%, 3%, 5%
- Report: bet count, hit rate, ROI, Kelly growth
- Pick middle bar if robust

**Target:** Stable performance across thresholds

**Why:** Avoid overfitting to one threshold.

---

## 🚀 **WEEKLY EVERGREEN LOOP**

### Monday AM
1. Ingest new data
2. Rebuild shrinkage priors
3. Simulate & center
4. Publish slate with probabilities & EV

### Wednesday & Friday
1. Re-ingest injuries & weather
2. Re-price
3. Re-publish
4. Only bet if EV still clears bar

### Post-Week
1. Autograde: log loss, Brier, ROI
2. Calibration plots
3. If metrics slip 2 weeks → disable module
4. Fall back to last passing config

---

## ✅ **WHAT "WORKING" LOOKS LIKE**

1. **Log loss or Brier** better than market (rolling 4 weeks)
2. **Positive ROI** at chosen EV threshold
3. **Controlled drawdowns**
4. **Monotone lift** by edge buckets
5. **Good calibration** plots
6. **Stability** across weeks

---

## 📋 **IMPLEMENTATION**

### File: `scripts/proper_scoring_test.py`

**Tests:**
1. ✅ Log loss & Brier vs vig-stripped market
2. ✅ EV calculation at posted odds
3. ✅ ROI tracking
4. ✅ Bet filtering (EV ≥ 3%)
5. ⏳ Calibration curves (TODO)
6. ⏳ Monotonicity test (TODO)
7. ⏳ Key-number validation (TODO)

---

## 🎯 **NEXT STEPS**

### Step 1: Run Proper Scoring Test (30 min)
```bash
cd /Users/steveridder/Git/Football/simulation_engine/nflfastR_simulator
python3 scripts/proper_scoring_test.py
```

**This will tell us:**
- Do we beat market on log loss?
- Do we beat market on Brier?
- What's our ROI at posted prices?

---

### Step 2: If We Beat Market (≥1% improvement)
**Action:** Run on full slate (6-8 weeks)

**Measure:**
- Log loss improvement
- Brier improvement
- ROI by EV threshold
- Calibration curves
- Lift by edge bucket

---

### Step 3: If We Don't Beat Market
**Debug order:**
1. Roll-forward audit
2. Shrinkage check
3. Market centering on
4. Gaussian baseline
5. Module ablations

---

## 💡 **KEY DIFFERENCES FROM CLV**

| CLV Approach | Proper Scoring |
|--------------|----------------|
| Chases line movement | Judges at posted price |
| Needs closing line | Needs outcomes only |
| Phantom if market doesn't move | Always meaningful |
| Hard to measure | Clean metrics |
| Indirect | Direct (ROI) |

---

## ✅ **BOTTOM LINE**

**Old way:** "Did we beat the closing line?"  
**New way:** "Did we make money at the price we paid?"

**Old metric:** CLV (line movement)  
**New metric:** Log loss, Brier, ROI (actual performance)

**Old problem:** Market doesn't move  
**New solution:** Doesn't matter, we judge at posted prices

---

## 🚀 **READY TO RUN**

```bash
cd /Users/steveridder/Git/Football/simulation_engine/nflfastR_simulator
python3 scripts/proper_scoring_test.py
```

**This will tell us if the model beats the market's probabilities.** 🎯

No phantoms. Just truth.

