# 🚀 IMPLEMENTATION ROADMAP

**Goal:** Build a profitable NFL betting system with proven CLV edge

---

## ✅ PHASE 1: COMPLETED (Week 9)

### What We Built
1. **Real Market Lines** - Odds API integration
2. **LLM Injury Detection** - OpenAI GPT-4o-mini + NFL.com scraping
3. **Weather Adjustments** - Wind/rain from Open-Meteo
4. **Situational Factors** - Travel, home/away splits, divisional games
5. **Adjusted Recommendations** - Compare ADJUSTED vs MARKET

### Current Results
- **12/14 games** (86%) have adjustments
- **4 betting recommendations** for Week 9
- **Factors:** QB injuries, OL injuries, weather, travel, splits, divisional

---

## 🔄 PHASE 2: OPTIMIZE & CACHE (Next 2 Weeks)

### 2A. Batch LLM Injury Detection ⏰
**Problem:** LLM calls are slow (60+ seconds per week)
**Solution:** Batch detect 2-3x per day, cache to SQLite

**Schedule:**
- **Wednesday 6 PM ET:** First pass (early injury reports)
- **Friday 6 PM ET:** Second pass (updated injury reports)  
- **Sunday 11 AM ET:** Final pass (game day inactives)

**Implementation:**
```bash
# Run batch detection
python batch_injury_detection.py detect 9 wednesday
python batch_injury_detection.py detect 9 friday
python batch_injury_detection.py detect 9 sunday

# View cached injuries
python batch_injury_detection.py summary 9
```

**Benefits:**
- ⚡ Flask loads instantly (reads from DB, not LLM)
- 💰 Saves OpenAI API costs
- 📊 Tracks injury changes over time

**Files Created:**
- `batch_injury_detection.py` - Batch detection script
- `artifacts/injury_cache.db` - SQLite database

---

### 2B. Backtest on 2025 Data (Weeks 1-8)
**Goal:** Measure CLV to validate situational factors aren't already priced

**Metrics:**
- **CLV Rate:** % of bets that beat closing line (target: ≥55%)
- **Avg CLV:** Average points gained (target: ≥+0.5 pts)
- **Win Rate:** % of bets won (target: ≥52.4%)
- **ROI:** Return on investment (target: positive)

**Data Needed:**
1. Opening lines (Monday/Tuesday)
2. Closing lines (Saturday/Sunday)
3. Actual results (final scores)

**Current Status:**
- ✅ Have closing lines for Weeks 1-7
- ❌ Need opening lines for Weeks 1-7
- ❌ Need actual results for Weeks 1-7

**Action Items:**
1. Fetch opening lines from Odds API (historical)
2. Fetch results from ESPN/nflverse
3. Run backtest script
4. Analyze which factors have positive CLV

---

## 📊 PHASE 3: 5-YEAR BACKTEST (Weeks 3-4)

### Goal: Validate Edge Across Multiple Seasons

**Test Each Factor Independently:**
1. QB injuries
2. OL injuries  
3. Weather (wind ≥15 MPH)
4. Travel distance (>1500 miles)
5. Home/away splits
6. Divisional games

**For Each Factor:**
- Backtest on 2020-2024 seasons
- Measure CLV rate, avg CLV, ROI
- Keep only factors with CLV rate ≥55%

**Expected Results:**
| Factor | CLV Rate | Avg CLV | ROI | Keep? |
|--------|----------|---------|-----|-------|
| QB Injuries | 60%+ | +1.0 pts | +5% | ✅ Elite |
| OL Injuries | 55%+ | +0.8 pts | +3% | ✅ Good |
| Weather (wind) | 58%+ | +0.9 pts | +4% | ✅ Good |
| Travel | 52% | +0.3 pts | +1% | ❌ Marginal |
| Home/Away Splits | 48% | -0.1 pts | -2% | ❌ Already priced |
| Divisional | 50% | +0.2 pts | 0% | ❌ Already priced |

**Hypothesis:**
- **QB/OL injuries** = Elite (market slow to price)
- **Weather** = Good (forecasts change, market lags)
- **Travel/Splits** = Already priced (everyone knows this)

---

## 🎯 PHASE 4: PRODUCTION SYSTEM (Week 5)

### Final Feature Set (After Backtest)
Keep ONLY features with proven CLV edge:
1. ✅ QB injuries (if CLV ≥55%)
2. ✅ OL injuries (if CLV ≥55%)
3. ✅ Weather (if CLV ≥55%)
4. ❌ Remove factors that fail backtest

### Automated Workflow
```
Monday:
  - Fetch opening lines (Odds API)
  - Detect injuries (batch LLM, cache to DB)
  - Calculate situational adjustments
  - Generate Week N predictions

Wednesday 6 PM:
  - Refresh injury detection (batch LLM)
  - Update predictions
  - Email/Slack alert if new edges

Friday 6 PM:
  - Final injury detection (batch LLM)
  - Update predictions
  - Lock in bets for weekend

Sunday 11 AM:
  - Game day injury check (batch LLM)
  - Final adjustments
  - Display on web UI

Monday (next week):
  - Fetch closing lines
  - Calculate CLV for Week N bets
  - Update CLV tracking dashboard
```

### Success Metrics (Track Weekly)
- **CLV Rate:** Rolling 50-bet average ≥55%
- **Avg CLV:** Rolling 50-bet average ≥+0.5 pts
- **ROI:** Rolling 50-bet average >0%

### Stop Rule
If CLV rate drops below 50% over 50 bets:
1. Stop betting immediately
2. Re-analyze factors
3. Market has adapted, need new edge

---

## 💡 PHASE 5: ADVANCED FEATURES (Weeks 6-8)

### OL Continuity (HIGH PRIORITY)
**Why:** Market is VERY slow to price new OL combinations

**Implementation:**
- Track starting OL (LT, LG, C, RG, RT) per team per week
- Count changes from Week N-1 to Week N
- Penalty: -1.0 pts per new starter

**Data Source:** PFF or nflverse snap counts

**Expected CLV:** 58%+ (elite edge)

---

### WR1/CB1 Matchups (MEDIUM PRIORITY)
**Why:** Elite CB shadowing elite WR reduces scoring

**Implementation:**
- Identify elite CBs (PFF grade >85)
- Identify elite WRs (targets >8/game)
- Penalty: -1.5 pts to total if matchup

**Data Source:** PFF grades + snap counts

**Expected CLV:** 55%+ (good edge)

---

### Script/Game Flow (LOW PRIORITY)
**Why:** Teams that run when leading = lower totals

**Implementation:**
- Calculate run rate when leading by 7+ in 2nd half
- If both teams >65% run rate when leading → -2.0 pts to total

**Data Source:** nflverse play-by-play

**Expected CLV:** 52%+ (marginal edge)

---

## 🚫 FEATURES TO AVOID

### Already Priced by Market
- Overall EPA/SR (everyone has this)
- Team record (public information)
- Coaching history (small sample, narrative)
- Primetime games (weak effect)
- Revenge games (narrative, not causal)

### Why These Fail
- ❌ Known early? Yes
- ❌ Drives scoring? Sometimes
- ❌ Market prices late? **NO** ← This is the killer

**Rule:** If casual bettors know it, the market already prices it.

---

## 📈 EXPECTED FINAL SYSTEM

### Feature Set (After 5-Year Backtest)
1. **QB Injuries** (CLV: 60%+)
2. **OL Continuity** (CLV: 58%+)
3. **Weather** (CLV: 58%+)
4. **OL Injuries** (CLV: 55%+)
5. **WR1/CB1 Matchups** (CLV: 55%+)

### Betting Volume
- **10-15 bets per week** (down from current 14)
- **Only bet when edge ≥2.0 pts**
- **$100 per bet** = $1,000-$1,500 exposure per week

### Expected Performance
- **CLV Rate:** 58%
- **Avg CLV:** +0.8 pts
- **Win Rate:** 54%
- **ROI:** +4% to +6%

### Annual Return (52 weeks)
- **Total bets:** ~650
- **Total wagered:** ~$65,000
- **Expected profit:** $2,600 to $3,900 (4-6% ROI)

---

## 🔧 TECHNICAL DEBT

### High Priority
1. ✅ Batch LLM injury detection (saves time + money)
2. ❌ Fetch historical opening lines (needed for backtest)
3. ❌ Fetch historical results (needed for backtest)
4. ❌ Build CLV tracking dashboard

### Medium Priority
5. ❌ Add OL continuity detection
6. ❌ Add WR1/CB1 matchup detection
7. ❌ Implement automated email/Slack alerts

### Low Priority
8. ❌ Add script/game flow detection
9. ❌ Build mobile-friendly UI
10. ❌ Add bet tracking/logging

---

## 📝 NEXT STEPS (This Week)

### Day 1-2: Batch Injury Detection
- [x] Create `batch_injury_detection.py`
- [ ] Test batch detection on Week 9
- [ ] Set up cron jobs (Wed/Fri/Sun)
- [ ] Update Flask to read from DB

### Day 3-4: Backtest 2025
- [ ] Fetch opening lines for Weeks 1-7
- [ ] Fetch results for Weeks 1-7
- [ ] Run backtest on situational factors
- [ ] Analyze CLV by factor

### Day 5-7: Remove Bad Factors
- [ ] If travel/splits have CLV <50%, remove them
- [ ] Keep only factors with CLV ≥55%
- [ ] Re-deploy to production
- [ ] Track Week 9 results

---

## ✅ SUCCESS CRITERIA

### Week 9 (Current)
- [x] 12/14 games have adjustments
- [x] 4 betting recommendations
- [ ] Track actual CLV after games complete

### Week 10 (After Backtest)
- [ ] CLV rate ≥55% on 2025 backtest
- [ ] Remove factors that fail
- [ ] Deploy optimized system

### Week 12 (After 5-Year Backtest)
- [ ] CLV rate ≥55% on 5-year backtest
- [ ] Final feature set locked
- [ ] Automated workflow running

### Week 16 (Mid-Season Check)
- [ ] 50+ bets placed
- [ ] CLV rate ≥55% on actual bets
- [ ] ROI positive
- [ ] Continue or pivot

---

## 💰 BUSINESS MODEL

### Conservative Projection (Year 1)
- **Bets per week:** 10
- **Weeks:** 18 (Weeks 1-18)
- **Total bets:** 180
- **Stake per bet:** $100
- **Total wagered:** $18,000
- **ROI:** 4%
- **Profit:** $720

### Aggressive Projection (Year 2+)
- **Bets per week:** 15
- **Weeks:** 52 (NFL + college)
- **Total bets:** 780
- **Stake per bet:** $200
- **Total wagered:** $156,000
- **ROI:** 5%
- **Profit:** $7,800

### Key Assumptions
- ✅ CLV rate stays ≥55% (market doesn't adapt)
- ✅ Bankroll management (Kelly criterion)
- ✅ Discipline (only bet when edge ≥2.0 pts)
- ❌ Risk: Market adapts, edge disappears

---

## 🎯 THE EDGE

**What separates winners from losers:**

### Winners (Sharp Bettors)
- ✅ Bet early (Monday-Wednesday)
- ✅ Use information market hasn't priced yet
- ✅ Measure CLV religiously
- ✅ Stop betting when edge disappears

### Losers (Casual Bettors)
- ❌ Bet late (Saturday-Sunday)
- ❌ Use information everyone knows
- ❌ Chase wins, ignore CLV
- ❌ Keep betting even when losing

**Our system is designed to be a winner.**

We bet early. We use fresh information. We measure CLV. We have a stop rule.

**That's the edge.**

