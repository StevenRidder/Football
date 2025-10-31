# Missing Signals from Strategy Document

## 🔍 Signals Analysis - What We're Using vs. What We're Missing

### ✅ Currently Using:
1. **OL/DL Pass Mismatch** - `ol_grade` vs `dl_grade` for pressure rates
2. **OL/DL Run Mismatch** - `ol_run_grade` vs `dl_run_grade` for run success
3. **WR/CB Matchup** - `passing_grade` vs `coverage_grade` for completions
4. **QB Pressure Splits** - Clean vs pressure performance
5. **EPA per Play** - Team strength baseline
6. **Play-calling Tendencies** - Situational pass rates
7. **Explosive Plays** - Based on passing/coverage matchup

### ❌ Missing High-Value Signals (Per Strategy Doc):

#### 1. **Success Rate (Early-Down)** ⭐ CRITICAL
**Strategy Quote:** *"Early-down passing success rate is particularly powerful because it filters out the noise of desperate third-down plays"*

**What to Add:**
- Track 1st/2nd down success rate (gaining 40% of needed on 1st, 50% on 2nd)
- Adjust completion/yards probabilities based on down and success rate
- Teams with high early-down success = more sustainable drives
- **Impact:** Most predictive factor for drive sustainability

**Implementation:**
- Add `early_down_success_rate` to TeamProfile
- Adjust pass/run outcomes on 1st/2nd down based on this metric
- Filter out 3rd-down conversion luck

---

#### 2. **Yards Per Play / Yards Per Pass Attempt** ⭐ CRITICAL
**Strategy Quote:** *"Teams winning YPA win ~97% of games outright and ~80% ATS"*

**What to Add:**
- Explicitly use YPP/YPA as predictor, not just via EPA
- Compare offense YPP vs defense YPP allowed
- More predictive than points scored (which can be lucky)
- **Impact:** Single most predictive passing metric

**Implementation:**
- Add `off_yards_per_play`, `def_yards_per_play_allowed` to TeamProfile
- Add `off_yards_per_pass_attempt`, `def_yards_per_pass_allowed` 
- Use for baseline yardage distributions, not just EPA
- Adjust expected yards on completions based on YPA vs opponent

---

#### 3. **Pace Impact on Totals** ⭐ HIGH VALUE
**Strategy Quote:** *"Two up-tempo teams can combine for higher totals... pace is invaluable when betting totals"*

**Current State:** Pace is loaded but NOT affecting game flow

**What to Add:**
- Fast teams = more possessions per game
- Slow teams = fewer possessions, lower totals
- Combine pace of both teams to predict total possessions
- **Impact:** Directly affects over/under predictions

**Implementation:**
- Use `home_profile.pace` and `away_profile.pace` in GameSimulator
- Adjust clock/time between plays based on pace
- Increase total drives for fast vs fast matchups
- Decrease total drives for slow vs slow matchups

---

#### 4. **Turnover Regression** ⭐ HIGH VALUE
**Strategy Quote:** *"Turnovers are notoriously random... teams with +3 turnover game may be overvalued"*

**What to Add:**
- Don't weight recent turnover margins heavily
- Fade teams coming off unsustainable turnover luck
- Use longer-term turnover rates, not recent variance
- **Impact:** Prevents betting on teams with unsustainable edges

**Implementation:**
- Track rolling turnover rate (e.g., 8-game window) vs recent (last 2 games)
- If recent turnover margin is >+2 above rolling average, reduce expected efficiency slightly
- If recent turnover margin is <-2 below rolling average, boost slightly (regression opportunity)

---

#### 5. **Special Teams** ⭐ MEDIUM VALUE
**Strategy Quote:** *"Special teams is one of the most overlooked phases but can provide hidden yardage"*

**What to Add:**
- Field position from punts (net yards)
- Kicker reliability (affects 4th down decisions)
- Kick return average
- **Impact:** Can swing close games by 1-2 points

**Implementation:**
- Add special teams metrics to TeamProfile
- Adjust starting field position based on punt coverage
- Adjust 4th down decision thresholds based on kicker accuracy
- Add special teams scores (rare but impactful)

---

#### 6. **Red Zone Regression Approach** ⭐ MEDIUM VALUE
**Strategy Quote:** *"Best red zone teams are the ones that get there, not ones with high conversion %"*

**Current State:** We have red zone logic but may over-weight conversion rates

**What to Add:**
- Focus on red zone opportunities (drives to 20) vs conversion %
- Regress extreme red zone TD rates toward mean
- Use overall offensive efficiency to predict red zone trips
- **Impact:** Prevents overvaluing teams with unsustainable red zone luck

**Implementation:**
- Track red zone opportunities per game (more stable)
- Don't boost red zone TD rates for teams with unsustainably high recent conversion %
- Use offensive EPA/play to predict red zone trip frequency

---

#### 7. **ANY/A (Adjusted Net Yards per Attempt)** ⭐ MEDIUM VALUE
**Strategy Quote:** *"ANY/A rolls up yards, TDs, INTs, sacks into one QB efficiency number"*

**What to Add:**
- Use ANY/A as explicit QB efficiency metric
- Compare offense ANY/A vs defense ANY/A allowed
- More comprehensive than YPA alone
- **Impact:** Better QB/offense evaluation

**Implementation:**
- Calculate ANY/A from QB stats or load from nflfastR
- Use to adjust pass play success rates
- Compare offense ANY/A vs defense ANY/A allowed

---

#### 8. **Strength of Schedule Adjustments** ⭐ MEDIUM VALUE
**Strategy Quote:** *"Adjust stats for opponent quality... teams with great numbers vs weak defenses may be inflated"*

**What to Add:**
- Opponent-adjusted EPA/YPP/YPA
- Remove garbage time plays
- Common opponent analysis
- **Impact:** Prevents overvaluing teams with easy schedules

**Implementation:**
- Use opponent-adjusted EPA (may already be in rolling_epa file)
- Filter garbage time (score differential >17 in Q4)
- Common opponent lookup for head-to-head comparisons

---

#### 9. **Situational Angles** ⭐ LOW-MEDIUM VALUE
**Strategy Quote:** *"Factors like travel, rest, weather, coaching aggression can tip games"*

**What to Add:**
- Rest days (short week penalty)
- Travel distance
- Weather (wind, rain - affects passing)
- Coaching 4th down aggression
- **Impact:** Small but measurable edges

**Implementation:**
- Add situational features to game setup
- Adjust pass rate/efficiency in bad weather
- Reduce efficiency for teams on short rest
- Boost 4th down conversion for aggressive coaches

---

## 🎯 Priority Order for Implementation:

### Phase 1 (Highest ROI):
1. **Success Rate (Early-Down)** - Most predictive, filters noise
2. **Yards Per Play/YPA** - Explicit usage (currently only implicit via EPA)
3. **Pace Impact** - Directly affects totals, already have data

### Phase 2 (High ROI):
4. **Turnover Regression** - Prevents betting on unsustainable luck
5. **Special Teams** - Field position matters in close games

### Phase 3 (Medium ROI):
6. **Red Zone Regression** - Better approach to red zone
7. **ANY/A** - Comprehensive QB metric
8. **Strength of Schedule** - Opponent adjustments

### Phase 4 (Situational):
9. **Situational Angles** - Rest, weather, coaching (small edges)

---

## 💡 Quick Wins:

1. **Add YPP/YPA explicitly** - Data likely available in nflfastR
2. **Use pace for possession count** - Already loaded, just need to apply it
3. **Track early-down success** - Calculate from play-by-play data
4. **Add turnover regression** - Simple filter on recent turnover margins

