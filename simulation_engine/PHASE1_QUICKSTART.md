# Phase 1 Validation - Quick Start Guide

## 🎯 What is Phase 1?

Phase 1 tests whether **OL/DL mismatches and QB pressure** predict NFL game outcomes better than our current Ridge model.

**Key Question:** Does the market already price these matchup-specific factors, or is there an edge?

---

## 🔍 How is This Different from Our Ridge Model?

### **Current Ridge Model:**
```python
# Uses team averages as features
features = [
    team_epa_offense,      # Season average
    team_epa_defense,      # Season average
    ol_continuity,         # Season average
    dl_pressure,           # Season average
]

predicted_score = Ridge.predict(features)
```

**Result:** 48.6% WR, -7.2% ROI (no edge)

---

### **Phase 1 Approach:**
```python
# Calculates matchup-specific edges for THIS game
pressure_edge = away_DL_grade - home_OL_grade  # Matchup-specific
qb_vulnerability = QB_EPA_clean - QB_EPA_pressure  # QB-specific

# Test: Does this predict outcomes better?
```

**Key Differences:**

#### 1. **Matchup-Specific vs Team Averages**
- **Ridge:** "KC OL has 72.5 grade (season average)"
- **Phase 1:** "BUF DL (85.3) vs KC OL (72.5) = **+12.8 pressure edge in THIS game**"

#### 2. **QB-Specific Pressure Response**
- **Ridge:** Treats all QBs the same under pressure
- **Phase 1:** "Mahomes under pressure: -0.05 EPA (elite), Daniel Jones: -0.35 EPA (terrible)"

#### 3. **Non-Linear Effects**
- **Ridge:** 10-point advantage = 2X the effect of 5-point advantage (linear)
- **Phase 1:** 10-point advantage = **catastrophic** (sacks, turnovers, game flow collapse)

---

## 📊 What Phase 1 Tests

### **H1: Pressure Edge Predicts Sacks**
- Hypothesis: Games with `pressure_edge > 10` have more sacks
- Expected: Correlation r > 0.3

### **H2: QB Vulnerability Predicts Performance**
- Hypothesis: QBs facing high pressure edge perform worse than season average
- Expected: Significant deviation (p < 0.05)

### **H3: Pressure Affects Spread Outcomes**
- Hypothesis: Team with pressure advantage covers spread >55% of the time
- Expected: >55% cover rate (vs 50% baseline, 52.4% breakeven)

### **H4: Market Underprices Mismatches**
- Hypothesis: Lines move toward team with pressure advantage during the week
- Expected: Positive line movement (early betting edge)

### **Backtest: Bet Pressure Advantage**
- Strategy: Bet team with pressure edge > 10 ATS
- Expected: >53% WR or >3% ROI

---

## 🚀 How to Run Phase 1

### **Option A: Quick Start (5 minutes)**
```bash
cd /Users/steveridder/Git/Football/simulation_engine/phase1_validation
./RUN_PHASE1.sh
```

This will:
1. Create sample PFF data (for testing)
2. Calculate matchup metrics
3. Test all hypotheses
4. Generate decision report

### **Option B: Step-by-Step**

#### **Step 1: Collect PFF Data**
```bash
python3 collect_pff_data.py
```

**If you have PFF subscription:**
- Download OL/DL grades, QB pressure splits
- Save to `simulation_engine/data/pff_raw/`
- Re-run script to process

**If you don't have PFF:**
- Script creates sample data for testing
- Continue with sample data to see how it works

#### **Step 2: Calculate Matchup Metrics**
```bash
python3 calculate_matchup_metrics.py
```

This calculates for each 2024 game:
- `pressure_edge_away`: Away DL vs Home OL
- `pressure_edge_home`: Home DL vs Away OL
- `net_pressure_advantage`: Overall pressure advantage
- `expected_impact`: Pressure edge × QB vulnerability

#### **Step 3: Test All Hypotheses**
```bash
python3 test_all_hypotheses.py
```

This tests H1-H4, runs backtest, generates report.

---

## 📈 Success Criteria

### **GO to Phase 2 if ANY of:**
- ✅ H1: Correlation r > 0.3
- ✅ H2: Statistical significance p < 0.05
- ✅ H3: Cover rate > 55%
- ✅ H4: Positive line movement
- ✅ Backtest: WR > 53% OR ROI > 3%

### **NO-GO to Phase 2 if:**
- ❌ No correlation (r < 0.2)
- ❌ No statistical significance (p > 0.10)
- ❌ Cover rate ≈ 50%
- ❌ Backtest: WR < 52% AND ROI < 1%

---

## 📁 Project Structure

```
simulation_engine/
├── data/
│   ├── pff_raw/                    # Raw PFF downloads
│   ├── pff_processed/              # Processed PFF data
│   └── matchup_metrics_2024.csv    # Calculated metrics
│
├── phase1_validation/
│   ├── README.md                   # Phase 1 overview
│   ├── RUN_PHASE1.sh              # Quick start script
│   ├── collect_pff_data.py        # Step 1: Get data
│   ├── calculate_matchup_metrics.py  # Step 2: Calculate edges
│   ├── test_all_hypotheses.py     # Step 3: Test signal
│   └── results/
│       ├── h1_pressure_vs_spread.png
│       ├── h3_cover_rates.png
│       └── PHASE1_VALIDATION_SUMMARY.txt
│
├── phase2_prototype/               # (If Phase 1 passes)
└── phase3_production/              # (If Phase 2 passes)
```

---

## 🔑 Key Metrics Explained

### **Pressure Edge**
```
pressure_edge = DL_grade - OL_grade
```

**Example:**
- BUF DL: 85.3
- KC OL: 72.5
- **Pressure Edge: +12.8** (BUF has big advantage)

**Interpretation:**
- Edge > 10: Significant mismatch
- Edge > 15: Catastrophic mismatch
- Edge < 5: Relatively even

### **QB Pressure Vulnerability**
```
vulnerability = EPA_clean - EPA_pressure
```

**Example:**
- Mahomes clean: +0.25 EPA
- Mahomes pressure: -0.05 EPA
- **Vulnerability: 0.30** (loses 0.30 EPA under pressure)

**Interpretation:**
- Low vulnerability (0.20-0.25): Elite QB (Mahomes, Allen)
- Medium vulnerability (0.30-0.35): Average QB
- High vulnerability (0.40+): Struggles under pressure

### **Expected Pressure Impact**
```
impact = pressure_edge × qb_vulnerability
```

**Example:**
- BUF pressure edge: +12.8
- Mahomes vulnerability: 0.30
- **Expected Impact: 3.84** (BUF DL expected to disrupt KC offense)

**Interpretation:**
- Impact > 3: Significant effect on game
- Impact > 5: Game-changing effect

---

## 💡 What Happens Next?

### **If Phase 1 Shows Signal (GO):**
1. **Proceed to Phase 2:** Build Monte Carlo simulation engine
2. **Timeline:** 5-7 weeks
3. **Goal:** Backtest on 2023-2024, validate edge

### **If Phase 1 Shows No Signal (NO-GO):**
1. **Pivot to alternatives:**
   - Live betting (in-game win probability)
   - Player props (less efficient market)
   - Totals focus (market may be weaker)
2. **Or:** Accept that market is efficient, bet for fun

### **If Phase 1 is Marginal (CONDITIONAL GO):**
1. **Review results carefully**
2. **Decide if signal is strong enough**
3. **Consider smaller-scale Phase 2 (fewer features)**

---

## 🎓 Learning from Phase 1

Even if Phase 1 shows no edge, we learn:

1. **Market Efficiency:** How quickly Vegas prices matchup-specific factors
2. **Data Quality:** Whether PFF grades correlate with actual outcomes
3. **Model Validation:** Whether our hypothesis about pressure is correct
4. **Research Skills:** How to test betting theories systematically

**This is valuable even if we don't find an edge.**

---

## 📞 Next Steps

### **This Week:**
1. ✅ Review this roadmap
2. ✅ Decide: Run Phase 1 with sample data or wait for PFF?
3. ✅ Run `./RUN_PHASE1.sh` to see how it works
4. ✅ Review results, understand the analysis

### **Week 1-2 (If Committed):**
1. Sign up for PFF subscription ($200/year)
2. Download real 2024 data
3. Re-run Phase 1 with real data
4. **Decision: GO / NO-GO to Phase 2**

---

## 🔥 Why This Matters

**Our current Ridge model doesn't beat Vegas.**

Phase 1 tests if a **different approach** (matchup-specific simulation) can find edges.

**If yes:** We build it (Phase 2-3).  
**If no:** We pivot to other strategies.

**Either way, we learn and improve.**

---

## 📚 Additional Resources

- **Roadmap:** `SIMULATION_ENGINE_ROADMAP.md` (full 3-phase plan)
- **Strategy Document:** `strategy.rtf` (research foundation)
- **Phase 1 README:** `phase1_validation/README.md` (detailed hypotheses)

---

**Ready to start? Run:**
```bash
cd simulation_engine/phase1_validation
./RUN_PHASE1.sh
```

**Questions? Review the roadmap or ask!**

