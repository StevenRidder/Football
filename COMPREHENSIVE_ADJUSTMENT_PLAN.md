# Comprehensive Adjustment Plan

## Current Adjustments (IMPLEMENTED ✅)

### 1. Situational Factors
- **Home/Away Splits** ✅
  - Teams with strong home records get +1.0 to +1.5 pts at home
  - Teams with poor away records get -1.0 to -1.5 pts on road
  
- **Travel Distance** ✅
  - Cross-country travel (>2000 miles): -1.0 pts
  - Moderate travel (1000-2000 miles): -0.5 pts
  
- **Divisional Games** ✅
  - -2.0 pts to total (split -1.0 each team)
  - More conservative, defensive games

### 2. Injury Detection (LLM-Powered) ✅
- **QB Injuries** ✅
  - Starter to backup: -3.0 to -5.0 pts
  - Backup to 3rd string: -5.0 to -7.0 pts
  
- **OL Injuries** ✅
  - Per starter out: -1.5 to -2.0 pts
  - Multiple OL out: cumulative penalty
  
- **Skill Position** ✅
  - WR1 out: -1.5 to -2.0 pts
  - WR2 out: -0.5 to -1.0 pts

### 3. Weather (Basic) ✅
- **Wind** ✅
  - >20 MPH: -3.0 pts to total
  - 15-20 MPH: -1.5 pts to total
  - 10-15 MPH: -0.7 pts to total
  
- **Precipitation** ✅
  - Heavy rain (>3mm/hr): -1.0 pts to total
  - Moderate rain (1-3mm/hr): -0.5 pts to total

---

## NEW Adjustments to Implement (PRIORITY)

### 4. OL Continuity (MISSING ❌)
**Why:** Market is slow to price OL shuffles; affects pass protection immediately
**Implementation:**
- Track OL starting lineup last 3 games
- **Penalty:** -0.5 pts per position change from last week
- **Penalty:** -1.0 pts if 3+ changes in last 3 games
- **Data source:** ESPN depth charts, injury reports

### 5. QB Pressure Metrics (MISSING ❌)
**Why:** QB under pressure performs worse; market underprices pressure matchups
**Implementation:**
- Track QB pressure-to-sack rate (nflverse)
- Track opposing defense pressure rate (nflverse)
- **Adjustment:** If QB has high pressure-to-sack rate AND facing high-pressure defense:
  - -1.0 to -2.0 pts for that offense
- **Data source:** nflverse play-by-play data

### 6. WR1/CB1 Matchup Quality (MISSING ❌)
**Why:** Elite CB shadowing WR1 changes game script; market prices late
**Implementation:**
- Track WR1 availability (already have)
- Track CB1 shadow coverage rate
- **Adjustment:** Elite CB (e.g., Sauce Gardner) shadowing WR1:
  - -1.0 to -1.5 pts to offense
- **Data source:** PFF (if available) or manual tracking of elite CBs

### 7. Pace & Script Tendencies (MISSING ❌)
**Why:** Teams with extreme pace affect totals; market underprices early week
**Implementation:**
- Track seconds per snap when leading by 7+ (nflverse)
- Track seconds per snap when trailing by 7+ (nflverse)
- **Adjustment for totals:**
  - Both teams fast pace: +2.0 to +3.0 pts
  - Both teams slow pace: -2.0 to -3.0 pts
  - Mixed: +/-1.0 pts
- **Data source:** nflverse play-by-play data

### 8. Red Zone Efficiency (MISSING ❌)
**Why:** Red zone EPA predicts scoring better than overall EPA
**Implementation:**
- Track red zone EPA/play last 4 games (nflverse)
- Track opponent red zone EPA allowed last 4 games
- **Adjustment:**
  - Elite RZ offense vs poor RZ defense: +1.0 to +1.5 pts
  - Poor RZ offense vs elite RZ defense: -1.0 to -1.5 pts
- **Data source:** nflverse play-by-play data

### 9. Rest Advantage (MISSING ❌)
**Why:** Extra rest (Thursday → Sunday, bye week) affects performance
**Implementation:**
- Track days of rest for each team
- **Adjustment:**
  - Coming off bye week: +1.0 to +1.5 pts
  - Short rest (Thursday game): -1.0 pts
  - Rest differential (e.g., 10 days vs 6 days): +/-0.5 to 1.0 pts
- **Data source:** ESPN schedule

### 10. Altitude Adjustment (MISSING ❌)
**Why:** Denver altitude affects visiting teams; market prices it but not fully early
**Implementation:**
- **Denver home games:** Visiting team -0.5 to -1.0 pts
- **Data source:** Stadium location

### 11. Temperature Extremes (MISSING ❌)
**Why:** Extreme cold/heat affects ball handling, stamina
**Implementation:**
- **Cold (<20°F):** -1.0 to -2.0 pts to total
- **Extreme heat (>95°F):** -0.5 to -1.0 pts to total
- **Data source:** Open-Meteo API (already have)

### 12. Prime Time Performance (MISSING ❌)
**Why:** Some teams consistently over/underperform in prime time
**Implementation:**
- Track team record in prime time games (SNF, MNF, TNF)
- **Adjustment:** If team has strong prime time record (>60% ATS):
  - +0.5 to +1.0 pts
- **Data source:** Historical game data

---

## Implementation Priority

### Phase 1: High-Impact, Easy to Implement (THIS WEEK)
1. ✅ Fix injury adjustments (apply to scores)
2. **OL Continuity** - Use ESPN depth charts
3. **Rest Advantage** - Use schedule data
4. **Altitude** - Simple Denver flag
5. **Temperature Extremes** - Already have weather API

### Phase 2: Medium-Impact, Requires nflverse Data (NEXT WEEK)
6. **QB Pressure Metrics** - nflverse play-by-play
7. **Pace & Script** - nflverse play-by-play
8. **Red Zone Efficiency** - nflverse play-by-play

### Phase 3: Lower-Impact or Harder to Source (LATER)
9. **WR1/CB1 Matchup** - Requires PFF or manual tracking
10. **Prime Time Performance** - Requires historical ATS data

---

## Backtest Plan

For each new adjustment:

1. **Add to model**
2. **Backtest on 2025 data (Weeks 1-8)**
   - Measure CLV improvement
   - Measure ROI improvement
   - Measure spread/total bet win rate
3. **If positive impact:**
   - Backtest on 5 years of data (2020-2024)
   - Validate CLV is consistent
4. **If validated:**
   - Add to production model
   - Display on main page

---

## Success Metrics

For each adjustment to be included:
- **CLV Rate:** ≥55% of bets beat closing line
- **Average CLV:** ≥+0.5 points
- **ROI:** Positive over 30+ bets
- **Consistency:** Works across multiple seasons

---

## Current Status

**Implemented:** 3 categories (Situational, Injuries, Weather)
**To Implement:** 9 new categories
**Target:** 12 total adjustment categories by end of month

