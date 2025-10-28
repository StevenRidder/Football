# Current Adjustment Factors Summary

## Adjustments Currently Calculated Per Game

The model now calculates **4 types of situational adjustments** for each game:

### 1. **Travel Distance Adjustment**
- **What it measures:** Distance the away team must travel
- **Impact:** 
  - Long distance (>2000 miles): -1.0 pts to away team
  - Medium distance (1000-2000 miles): -0.5 pts to away team
  - Short distance (<1000 miles): No adjustment
- **Applied to:** Both spread and total

### 2. **Home/Away Splits**
- **What it measures:** Team performance at home vs away (2025 season records)
- **Impact:**
  - **Away team dominance** (win rate >70% away): +1.0 pts
  - **Away team struggles** (win rate <30% away): -1.5 pts
  - **Home team dominance** (win rate >70% home): +1.0 pts
  - **Home team struggles** (win rate <30% home): -1.5 pts
- **Applied to:** Both spread and total

### 3. **Divisional Games**
- **What it measures:** Whether teams are in the same division
- **Impact:** -1.0 pts to total (divisional games tend to be lower scoring)
- **Applied to:** Total only

### 4. **Pace Adjustments** (Currently disabled due to performance issues)
- Was checking team pace (seconds per snap, plays per game)
- Temporarily removed from fast version

---

## How Adjustments Are Applied

### Spread Calculation:
```
adjusted_spread = market_spread + travel_adj + away_split_adj - home_split_adj
```

### Total Calculation:
```
adjusted_total = market_total + travel_adj + away_split_adj + home_split_adj + divisional_adj
```

### Score Calculation:
1. Convert market spread/total to implied scores
2. Round market scores to nearest 0.5
3. Apply total adjustment (split evenly between teams)
4. Apply spread adjustment
5. Round adjusted scores to nearest 0.5
6. Calculate adjusted spread from rounded scores

---

## Backtest Results (2025 Weeks 1-7)

**Test Period:** Weeks 1-7 (108 completed games)
**Minimum Edge Threshold:** 2.0 points

### Results:
- **Total Bets:** 3
- **Spread Bets:** 0
- **Total Bets:** 3

### Performance Metrics:
- **CLV Rate:** 33.3% (1/3) ❌ FAIL (target: ≥55%)
- **Avg CLV:** +0.33 pts ❌ FAIL (target: ≥+0.5 pts)
- **Win Rate:** 66.7% (2/3) ✅ PASS (target: ≥52.4%)
- **ROI:** +27.3% ✅ PASS (target: positive)
- **Profit:** +0.82 units

### Verdict:
❌ **SITUATIONAL FACTORS ALREADY PRICED IN MARKET**

The factors show positive win rate and ROI, but **CLV is below target**, indicating the market already prices these adjustments. The small sample size (only 3 bets) also makes it difficult to draw strong conclusions.

---

## Bets Generated:

1. **Week 2: LAC @ LV - UNDER 46.5**
   - Edge: 2.5 pts | CLV: 0.0 pts | ✅ WON
   - Factors: LAC away dominance (+1.0), LV home struggles (-1.5)

2. **Week 3: DET @ BAL - OVER 53.5**
   - Edge: 2.0 pts | CLV: 0.0 pts | ✅ WON
   - Factors: DET away dominance (+1.0), BAL home dominance (+1.0)

3. **Week 4: NYJ @ MIA - UNDER 45.5**
   - Edge: 4.0 pts | CLV: +1.0 pts | ❌ LOST
   - Factors: Medium travel (-0.5), MIA home struggles (-1.5)

---

## Current Week 9 Games with Adjustments

**12 out of 14 games** have situational adjustments:

### Games with Betting Recommendations (Edge ≥2.0 pts):
1. **JAX @ LV - BET UNDER 45.5** (Edge: 3.5 pts)
2. **BAL @ MIA - BET UNDER 50.5** (Edge: 3.0 pts)
3. **SF @ NYG - BET UNDER 48.5** (Edge: 3.0 pts)
4. **KC @ BUF - BET OVER 52.5** (Edge: 2.0 pts)

---

## What's NOT Included Yet

Based on the original roadmap, these factors are **NOT yet implemented**:

1. ❌ **QB Quality Delta** (starter vs backup, EPA, pressure-to-sack rate)
2. ❌ **OL Continuity** (offensive line stability)
3. ❌ **Weather** (wind, precipitation, temperature) - module exists but not integrated
4. ❌ **Defense Shape** (pressure rate, EPA allowed)
5. ❌ **Pace** (detailed play-by-play pace metrics) - disabled due to performance
6. ❌ **Market Movement** (opening vs closing line deltas)

---

## Recommendations

1. **CLV is below target** - Consider increasing edge threshold to 3.0+ points
2. **Small sample size** - Need more weeks of data to validate
3. **Add QB/injury signals** - LLM injury detection is built but needs batching
4. **Consider 5-year backtest** - Test on historical data to validate approach
5. **Weather integration** - Weather module exists but not yet applied to adjustments

---

## Files:
- **Adjustment Logic:** `edge_hunt/situational_factors_fast.py`
- **Integration:** `edge_hunt/integrate_signals.py`
- **Backtest Script:** `backtest_situational_factors.py`
- **Backtest Results:** `artifacts/backtest_situational_2025.csv`

