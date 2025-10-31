# Phase 1: Validation - Testing OL/DL Mismatch Signal

## Goal
Prove that OL/DL mismatches and QB pressure predict outcomes better than our current Ridge model.

## Hypotheses to Test

### H1: Pressure Edge Predicts Sacks
**Hypothesis:** Games with large `pressure_edge` (>10 PFF grade points) have more sacks

**Test:**
- Calculate: `pressure_edge = DL_grade - OL_grade` for each team
- Measure: Correlation between `pressure_edge` and actual sacks in game
- **Expected:** r > 0.3 (moderate positive correlation)

### H2: QB Pressure Vulnerability Predicts Performance
**Hypothesis:** QBs facing mismatched pressure perform worse than season average

**Test:**
- Filter: Games where `pressure_edge` > 10
- Compare: QB's actual EPA in game vs season average EPA
- **Expected:** Significant negative deviation (t-test, p < 0.05)

### H3: Pressure Mismatches Affect Spread Outcomes
**Hypothesis:** Team with pressure advantage covers spread more often

**Test:**
- Filter: Games with `pressure_edge` > 10
- Measure: Cover rate for team with pressure advantage
- **Expected:** >55% cover rate (vs 50% baseline)

### H4: Market Underprices Early-Week Mismatches
**Hypothesis:** Lines move toward team with pressure advantage during the week

**Test:**
- Compare: Opening line vs closing line in games with `pressure_edge` > 10
- Measure: Line movement direction and magnitude
- **Expected:** Line moves toward team with pressure advantage
- **Implication:** Early betting opportunity exists

## Data Requirements

### PFF Data (Need to Obtain)
- [ ] Team OL pass-blocking grades (weekly, 2024)
- [ ] Team DL pass-rush grades (weekly, 2024)
- [ ] QB performance splits:
  - [ ] Clean pocket: Completion %, Y/A, EPA/play
  - [ ] Under pressure: Completion %, Y/A, EPA/play
- [ ] Run-blocking grades (OL)
- [ ] Run-defense grades (DL)

**Source:** PFF.com subscription (free trial or basic tier ~$200/year)

### nflfastR Data (Already Available)
- [x] Play-by-play for 2022-2024
- [x] Actual sack rates per game
- [x] EPA per play
- [x] Game results (scores, spreads)

**Source:** `nfl_data_py` library

### Betting Data (Already Available)
- [x] Opening lines (Sunday/Monday)
- [x] Closing lines (kickoff)
- [x] Actual results vs spread

**Source:** `nfl_data_py` library

## Analysis Scripts

### 1. `collect_pff_data.py`
- Download PFF grades for 2024 season
- Structure data for analysis
- Save to `data/pff_grades_2024.csv`

### 2. `calculate_matchup_metrics.py`
- For each game in 2024:
  - Calculate `pressure_edge_away` and `pressure_edge_home`
  - Calculate `qb_pressure_vulnerability` for each QB
  - Calculate `expected_pressure_impact`
- Save to `data/matchup_metrics_2024.csv`

### 3. `test_hypothesis_h1.py`
- Test correlation: `pressure_edge` vs actual sacks
- Generate scatter plot
- Calculate correlation coefficient

### 4. `test_hypothesis_h2.py`
- Test QB performance deviation when facing pressure mismatch
- T-test for statistical significance
- Generate box plots

### 5. `test_hypothesis_h3.py`
- Test cover rate for team with pressure advantage
- Chi-square test for significance
- Generate bar chart

### 6. `test_hypothesis_h4.py`
- Test line movement in games with pressure mismatch
- Calculate average line movement
- Identify early betting opportunities

### 7. `backtest_pressure_strategy.py`
- Simulate betting strategy:
  - Bet team with pressure advantage ATS
  - Bet under if both teams have weak OL
- Calculate: Win rate, ROI, CLV
- Generate performance report

## Success Criteria

### GO to Phase 2 if ANY of:
- [ ] H1: Correlation r > 0.3 (pressure edge predicts sacks)
- [ ] H2: QB performance deviation p < 0.05 (statistically significant)
- [ ] H3: Cover rate > 55% (profitable betting angle)
- [ ] H4: Positive line movement (early betting edge)
- [ ] Backtest: Win rate > 53% OR ROI > 3%

### NO-GO to Phase 2 if:
- [ ] No correlation found (r < 0.2)
- [ ] No statistical significance (p > 0.10)
- [ ] Cover rate ≈ 50% (no edge)
- [ ] Line movement random or against us
- [ ] Backtest: Win rate < 52% AND ROI < 1%

## Timeline

### Week 1: Data Collection
- Day 1-2: Sign up for PFF, download data
- Day 3-4: Structure data, create CSV files
- Day 5: Validate data quality

### Week 2: Hypothesis Testing
- Day 1-2: Test H1 and H2
- Day 3-4: Test H3 and H4
- Day 5: Run backtest

### Week 3: Analysis & Decision
- Day 1-2: Write results report
- Day 3: Review with stakeholders
- Day 4: **Decision: GO / NO-GO to Phase 2**

## Deliverables

1. **Data Files:**
   - `data/pff_grades_2024.csv`
   - `data/matchup_metrics_2024.csv`
   - `data/backtest_results_2024.csv`

2. **Analysis Scripts:**
   - All hypothesis testing scripts (listed above)

3. **Results Report:**
   - `PHASE1_VALIDATION_RESULTS.md`
   - Includes: Correlation coefficients, p-values, plots, backtest results
   - Recommendation: GO / NO-GO to Phase 2

## Notes

### Difference from Current Ridge Model
Our current Ridge model uses OL/DL stress features as **static inputs** (season averages).

Phase 1 tests if **matchup-specific calculations** (DL vs OL in THIS game) predict outcomes better.

**Example:**
- **Ridge:** "KC OL grade: 72.5" (feature)
- **Phase 1:** "BUF DL (85.3) vs KC OL (72.5) = +12.8 pressure edge" (matchup-specific)

### Why This Might Work
1. **Non-linear effects:** Extreme mismatches (>10 grade points) may have outsized impact
2. **QB-specific:** Elite QBs handle pressure better than average QBs
3. **Game flow:** Early pressure → turnovers → game script changes
4. **Market gap:** Vegas may use team averages, not matchup-specific calculations

### Why This Might Fail
1. **Market efficiency:** Vegas already prices OL/DL mismatches
2. **PFF grades subjective:** May not correlate with actual outcomes
3. **Small sample:** 2024 season only ~100 games
4. **Regression to mean:** Extreme mismatches may not persist

**Phase 1 will tell us which is true.**

