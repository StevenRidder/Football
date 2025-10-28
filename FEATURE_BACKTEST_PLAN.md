# 🎯 FEATURE BACKTEST PLAN - Edge Hunt System

**Goal:** Only add features that pass ALL THREE tests:
1. ✅ **Known Early** (Mon-Wed)
2. ✅ **Drives Scoring** (causality)
3. ✅ **Market Prices Late** (Thu-Sun)

---

## ✅ CURRENTLY IMPLEMENTED (Week 9)

| Feature | Known When | Market Adjusts | Edge Window | Status |
|---------|-----------|----------------|-------------|--------|
| **QB Injury/Backup** | Mon-Wed | Thu-Sat | 1-3 days | ✅ **LIVE** |
| **OL Injuries (2+ starters)** | Mon-Tue | Fri-Sat | 3-5 days | ✅ **LIVE** |
| **Wind (≥10 MPH)** | Mon-Tue | Sun AM | 4-6 days | ✅ **LIVE** |
| **Precipitation** | Mon-Tue | Sun AM | 4-6 days | ✅ **LIVE** |
| **Dome Flag** | Always | N/A | N/A | ✅ **LIVE** |

**Result:** Only 1/14 games showing adjustments (MIN @ DET)

---

## 🧪 NEWLY ADDED (Need Testing)

| Feature | Known When | Market Adjusts | Edge Window | Status |
|---------|-----------|----------------|-------------|--------|
| **Travel Distance** | Always | Rarely | Every week | 🧪 **TESTING** |
| **Home/Away Splits** | Always | Rarely | Every week | 🧪 **TESTING** |
| **Divisional Game** | Always | Sometimes | Every week | 🧪 **TESTING** |
| **Pace (Fast/Slow)** | Always | Rarely | Every week | 🧪 **TESTING** |
| **Temperature Extremes** | Mon-Tue | Sun AM | 4-6 days | 🧪 **TESTING** |

**Expected:** 8-10 games should show adjustments after adding these

---

## 📊 PROPOSED - HIGH PRIORITY (Add Next)

### 1. **OL Continuity** ⭐⭐⭐ ELITE
**Why:** Market is VERY slow to price new OL combinations

| Metric | Value |
|--------|-------|
| Known When | Mon-Tue (injury reports) |
| Market Adjusts | Fri-Sat |
| Edge Window | **3-5 days** |
| Impact | -2.0 to -3.0 pts per new starter |
| Detection | Compare Week N-1 starting 5 to Week N |

**Implementation:**
```python
def get_ol_continuity_adjustment(team: str, week: int) -> float:
    """
    Compare current week's OL to last week.
    New starters = reduced efficiency.
    """
    # Get Week N-1 starting OL
    prev_starters = get_starting_ol(team, week - 1)
    
    # Get Week N starting OL
    curr_starters = get_starting_ol(team, week)
    
    # Count changes
    changes = len(set(prev_starters) - set(curr_starters))
    
    if changes >= 3:
        return -3.0  # 3+ new starters
    elif changes == 2:
        return -2.0
    elif changes == 1:
        return -1.0
    
    return 0.0
```

---

### 2. **WR1/WR2 Availability** ⭐⭐ STRONG
**Why:** Market underprices WR impact until Friday

| Metric | Value |
|--------|-------|
| Known When | Tue-Wed (practice reports) |
| Market Adjusts | Fri-Sun |
| Edge Window | **2-4 days** |
| Impact | -1.5 to -2.5 pts for WR1 |
| Detection | LLM already detects, need to emphasize |

**Current:** Already in LLM injury detector
**Action:** Increase weight from -0.5/-2.5 to -2.0/-3.0 for "high impact" WRs

---

### 3. **CB1 vs WR1 Matchup** ⭐⭐ STRONG
**Why:** Elite CB shadowing elite WR = scoring drop

| Metric | Value |
|--------|-------|
| Known When | Tue-Wed (game plan leaks) |
| Market Adjusts | Fri-Sun |
| Edge Window | **2-4 days** |
| Impact | -1.5 to -2.0 pts to total |
| Detection | Need PFF grades or snap counts |

**Implementation:**
```python
def get_cb_wr_matchup_adjustment(away: str, home: str) -> float:
    """
    Elite CB shadowing elite WR reduces scoring.
    """
    # Elite CBs (PFF grade >85)
    elite_cbs = {
        'SF': 'Charvarius Ward',
        'NYJ': 'Sauce Gardner',
        'DAL': 'Trevon Diggs',
        # ... etc
    }
    
    # Elite WRs (targets >8/game)
    elite_wrs = {
        'MIA': 'Tyreek Hill',
        'MIN': 'Justin Jefferson',
        # ... etc
    }
    
    # Check if elite CB will shadow elite WR
    if home in elite_cbs and away in elite_wrs:
        return -1.5  # Reduces away team scoring
    
    if away in elite_cbs and home in elite_wrs:
        return -1.5  # Reduces home team scoring
    
    return 0.0
```

---

### 4. **Script/Game Flow Tendency** ⭐ GOOD
**Why:** Teams that run when leading = lower totals

| Metric | Value |
|--------|-------|
| Known When | Always (historical) |
| Market Adjusts | Rarely |
| Edge Window | **Every week** |
| Impact | -1.0 to -2.0 pts to total |
| Detection | Run rate when leading by 7+ |

**Implementation:**
```python
def get_script_adjustment(away: str, home: str) -> float:
    """
    Teams that run clock when leading = lower totals.
    """
    # Get run rate when leading by 7+ in 2nd half
    away_run_rate_leading = get_run_rate_when_leading(away)
    home_run_rate_leading = get_run_rate_when_leading(home)
    
    # If both teams are run-heavy when leading
    if away_run_rate_leading > 0.65 and home_run_rate_leading > 0.65:
        return -2.0  # Game will slow down in 4th quarter
    
    return 0.0
```

---

## ❌ REJECTED FEATURES (Fail Tests)

| Feature | Known Early? | Drives Scoring? | Market Prices Late? | Verdict |
|---------|:------------:|:---------------:|:-------------------:|---------|
| **Overall EPA** | ✅ | ✅ | ❌ (already priced) | ❌ **REJECT** |
| **Team Record** | ✅ | ❌ (narrative) | ❌ (already priced) | ❌ **REJECT** |
| **Coaching History** | ✅ | ❌ (sample size) | ⚠️ (sometimes) | ❌ **REJECT** |
| **Primetime Games** | ✅ | ❌ (weak effect) | ⚠️ (sometimes) | ❌ **REJECT** |
| **Revenge Games** | ✅ | ❌ (narrative) | ❌ (already priced) | ❌ **REJECT** |

---

## 🧪 BACKTEST PROTOCOL

### Step 1: Baseline (Current System)
```bash
# Run current system on Weeks 1-8
python3 backtest_edge_hunt.py --weeks 1-8 --features current

# Measure:
# - Win Rate
# - CLV Rate (% of bets that beat closing line)
# - Average CLV (points)
# - ROI
```

**Expected Results:**
- Win Rate: ~60-65%
- CLV Rate: ~50% (coin flip)
- Avg CLV: ~0 pts
- ROI: ~0% (break even)

---

### Step 2: Add Situational Factors
```bash
# Add travel, home/away, divisional, pace, temperature
python3 backtest_edge_hunt.py --weeks 1-8 --features situational

# Measure same metrics
```

**Success Criteria:**
- CLV Rate: ≥55% (improvement)
- Avg CLV: ≥+0.5 pts
- ROI: Positive

**If fails:** Remove situational factors, they're already priced

---

### Step 3: Add OL Continuity
```bash
# Add OL continuity detection
python3 backtest_edge_hunt.py --weeks 1-8 --features ol_continuity

# Measure same metrics
```

**Success Criteria:**
- CLV Rate: ≥58%
- Avg CLV: ≥+0.8 pts
- Additional 2-3 games per week with signals

---

### Step 4: Add WR/CB Matchups
```bash
# Add WR1/CB1 matchup detection
python3 backtest_edge_hunt.py --weeks 1-8 --features matchups

# Measure same metrics
```

**Success Criteria:**
- CLV Rate: ≥60%
- Avg CLV: ≥+1.0 pts
- Additional 1-2 games per week with signals

---

## 📈 SUCCESS METRICS

### Tier 1: ELITE (Keep Forever)
- CLV Rate: ≥60%
- Avg CLV: ≥+1.0 pts
- ROI: ≥5% over 50+ bets

### Tier 2: GOOD (Keep for Now)
- CLV Rate: 55-60%
- Avg CLV: +0.5 to +1.0 pts
- ROI: 2-5%

### Tier 3: NOISE (Remove)
- CLV Rate: <55%
- Avg CLV: <+0.5 pts
- ROI: <2%

---

## 🎯 IMPLEMENTATION PRIORITY

### Week 9 (Current)
1. ✅ Test situational factors (travel, splits, pace, divisional, temp)
2. ✅ Measure CLV on current week
3. ✅ Display adjustments on UI

### Week 10
1. Add OL continuity detection
2. Backtest Weeks 1-9
3. If positive CLV → deploy to UI

### Week 11
1. Add WR1/CB1 matchup detection
2. Backtest Weeks 1-10
3. If positive CLV → deploy to UI

### Week 12
1. Add script/game flow detection
2. Full backtest Weeks 1-11
3. Final feature set locked

---

## 📊 EXPECTED RESULTS AFTER ALL FEATURES

| Metric | Current | After Situational | After OL | After WR/CB | Target |
|--------|---------|------------------|----------|-------------|--------|
| Games with Signals | 1/14 (7%) | 8/14 (57%) | 10/14 (71%) | 12/14 (86%) | 10-12/14 |
| CLV Rate | ~50% | ~55% | ~58% | ~60% | ≥60% |
| Avg CLV | ~0 pts | ~+0.5 pts | ~+0.8 pts | ~+1.0 pts | ≥+1.0 pts |
| ROI | ~0% | ~2% | ~4% | ~6% | ≥5% |

---

## 🚀 NEXT STEPS

1. **Run situational factors on Week 9** (already implemented)
2. **Check how many games now show adjustments**
3. **If 8+ games → good signal**
4. **If <5 games → features already priced, remove them**
5. **Backtest on Weeks 1-8 to measure CLV**
6. **Add OL continuity next week if CLV positive**

---

## 💡 KEY INSIGHT

**You don't need 50 features.**
**You need 5-8 features that the market prices LATE.**

That's the entire edge.

- QB backup: Market prices Thu-Sat → We know Mon-Wed → **3-day edge**
- OL continuity: Market prices Fri-Sat → We know Mon-Tue → **4-day edge**
- Wind forecast: Market prices Sun AM → We know Mon-Tue → **5-day edge**

**This is where sharp bettors make money.**

