# Data Source Mapping - Missing Signals

## 📊 Available APIs & Data Sources

### ✅ Currently Have Access To:
1. **nflfastR (nfl_data_py)** - Play-by-play data, schedules, team stats
2. **The Odds API** - Market lines, spreads, totals
3. **ESPN API** - Scores, schedules, injury data
4. **PFF Premium** - Team grades (already collected)

---

## 🎯 Missing Signals → Data Source Mapping

### Phase 1: Highest ROI Signals

#### 1. **Success Rate (Early-Down)** ⭐ CRITICAL
**Data Source:** nflfastR play-by-play  
**API Call:**
```python
import nfl_data_py as nfl
pbp = nfl.import_pbp_data([2022, 2023, 2024, 2025])
```

**Calculate From:**
- Filter to 1st and 2nd downs
- Success = gaining 40% of needed yards on 1st down, 50% on 2nd down
- Group by: team, season, week
- Output: `early_down_success_rate.csv` with columns:
  - `posteam`, `season`, `week`, `early_down_success_rate`, `first_down_success`, `second_down_success`

**Script to Create:** `preprocessing/extract_early_down_success.py`

---

#### 2. **Yards Per Play / Yards Per Pass Attempt** ⭐ CRITICAL
**Data Source:** nflfastR play-by-play  
**API Call:**
```python
pbp = nfl.import_pbp_data([2022, 2023, 2024, 2025])
```

**Calculate From:**
- `yards_gained` per play (run + pass)
- `yards_gained` per pass attempt (`pass_attempt == 1`)
- Group by: team, season, week, offense/defense
- Output: `team_yards_per_play.csv` with columns:
  - `team`, `season`, `week`, `off_yards_per_play`, `off_yards_per_pass_attempt`, `def_yards_per_play_allowed`, `def_yards_per_pass_allowed`

**Script to Create:** `preprocessing/extract_yards_per_play.py`

---

#### 3. **Pace Impact on Totals** ⭐ HIGH VALUE
**Data Source:** ✅ ALREADY HAVE - `team_pace.csv` exists!  
**Status:** Data loaded, just need to **USE IT** in game simulation

**What We Have:**
- `data/nflfastR/team_pace.csv` with `avg_plays_per_drive`

**What to Do:**
- Apply pace in `GameSimulator` to adjust total possessions
- Fast team vs fast team = more drives
- Slow vs slow = fewer drives

**Script to Create:** Update `simulator/game_simulator.py` to use pace

---

#### 4. **ANY/A (Adjusted Net Yards per Attempt)** ⭐ MEDIUM VALUE
**Data Source:** nflfastR play-by-play  
**Formula:**
```
ANY/A = (pass_yards + 20*pass_tds - 45*ints - sack_yards) / (pass_attempts + sacks)
```

**Calculate From:**
- Group by: team, season, week, QB (optional)
- Output: `team_anya.csv` with columns:
  - `team`, `season`, `week`, `off_anya`, `def_anya_allowed`

**Script to Create:** `preprocessing/extract_anya.py`

---

### Phase 2: High ROI Signals

#### 5. **Turnover Regression** ⭐ HIGH VALUE
**Data Source:** nflfastR play-by-play  
**Calculate From:**
- Track turnovers (interceptions + fumbles lost)
- Rolling 8-game window vs last 2 games
- Output: `turnover_regression.csv` with columns:
  - `team`, `season`, `week`, `recent_turnover_margin` (last 2), `rolling_turnover_margin` (8 games), `regression_factor`

**Script to Create:** `preprocessing/extract_turnover_regression.py`

---

#### 6. **Special Teams** ⭐ MEDIUM VALUE
**Data Source Options:**
1. **nflfastR** - Has punt/kick data in play-by-play
2. **ESPN API** - May have special teams rankings

**Calculate From nflfastR:**
- Punt net yards (punt_yards - return_yards)
- Field goal percentage by kicker
- Kick return average
- Output: `special_teams.csv` with columns:
  - `team`, `season`, `week`, `punt_net_yards`, `fg_make_pct`, `kick_return_avg`

**Script to Create:** `preprocessing/extract_special_teams.py`

---

### Phase 3: Medium ROI Signals

#### 7. **Red Zone Regression** ⭐ MEDIUM VALUE
**Data Source:** nflfastR play-by-play  
**Calculate From:**
- Red zone trips (drives reaching opponent 20)
- Red zone TD conversion rate
- Output: `red_zone_stats.csv` with columns:
  - `team`, `season`, `week`, `red_zone_trips_per_game`, `red_zone_td_pct`, `red_zone_trips_regressed`

**Script to Create:** `preprocessing/extract_red_zone.py`

---

#### 8. **Strength of Schedule** ⭐ MEDIUM VALUE
**Data Source:** nflfastR play-by-play (already calculating opponent-adjusted EPA)  
**Status:** We have `opponent_adjusted_epa_2024.csv`

**What We Have:**
- `data/opponent_adjusted_epa_2024.csv`

**What to Do:**
- Load opponent-adjusted EPA in TeamProfile
- Use instead of raw EPA when available

**Script to Create:** Update `simulator/team_profile.py` to load opponent-adjusted EPA

---

#### 9. **Situational Angles** ⭐ LOW-MEDIUM VALUE
**Data Sources:**
1. **nflfastR schedules** - Rest days, travel
2. **ESPN API** - Weather data
3. **Open-Meteo API** - Weather (if we want historical)

**Calculate From:**
- Rest days: `nfl.import_schedules()` has `away_rest`, `home_rest`
- Weather: ESPN or schedule data
- Output: `situational_factors.csv` with columns:
  - `game_id`, `season`, `week`, `home_rest_days`, `away_rest_days`, `weather_wind`, `weather_rain`, `dome`

**Script to Create:** `preprocessing/extract_situational_factors.py`

---

## 📥 Data Download Scripts Needed

### Priority 1 (Can Calculate from nflfastR - No API Needed):
1. ✅ `extract_yards_per_play.py` - YPP, YPA from play-by-play
2. ✅ `extract_early_down_success.py` - Success rate from play-by-play
3. ✅ `extract_anya.py` - ANY/A from play-by-play
4. ✅ `extract_turnover_regression.py` - Turnover rates from play-by-play
5. ✅ `extract_red_zone.py` - Red zone stats from play-by-play
6. ✅ `extract_special_teams.py` - Special teams from play-by-play

### Priority 2 (May Need Additional API):
7. ⚠️ `extract_situational_factors.py` - Rest, weather (ESPN or schedule)

### Priority 3 (Already Have - Just Need to Use):
8. ✅ Pace - Already in `team_pace.csv` - just apply it
9. ✅ Opponent-adjusted EPA - Already have - just load it

---

## 🔧 Implementation Plan

### Step 1: Create Extraction Scripts (nflfastR)
All these can use `nfl.import_pbp_data()` which we already use:

1. **YPP/YPA Script** - Calculate yards per play metrics
2. **Success Rate Script** - Calculate early-down success
3. **ANY/A Script** - Calculate adjusted net yards
4. **Turnover Script** - Track turnover regression
5. **Red Zone Script** - Red zone trips vs conversion
6. **Special Teams Script** - Punt, kick, return stats

### Step 2: Load into TeamProfile
Update `TeamProfile.__init__()` to load:
- `off_yards_per_play`, `off_yards_per_pass_attempt`
- `def_yards_per_play_allowed`, `def_yards_per_pass_allowed`
- `early_down_success_rate`
- `anya_off`, `anya_def_allowed`
- `turnover_regression_factor`
- `special_teams` (punt net, FG%, return avg)

### Step 3: Use in Simulator
- **PlaySimulator**: Use YPP/YPA for yardage distributions
- **PlaySimulator**: Use success rate for down/distance adjustments
- **GameSimulator**: Use pace for total possessions
- **PlaySimulator**: Use turnover regression to adjust expectations

---

## 📋 Quick Start: First Script to Create

Let's start with **YPP/YPA** since it's the most critical and easiest:

```python
# preprocessing/extract_yards_per_play.py
import nfl_data_py as nfl
import pandas as pd
from pathlib import Path

# Download play-by-play for all needed seasons
pbp = nfl.import_pbp_data([2022, 2023, 2024, 2025])

# Calculate offensive YPP
off_ypp = pbp.groupby(['posteam', 'season', 'week']).agg({
    'yards_gained': 'mean',  # YPP
    'pass': lambda x: (x == 1).sum(),  # Pass attempts
    'yards_gained': lambda x: x[pbp['pass'] == 1].mean()  # YPA
})
```

---

## 🎯 Action Items

1. **Create extraction scripts** for nflfastR data (YPP, success rate, ANY/A, etc.)
2. **Update TeamProfile** to load all new metrics
3. **Update PlaySimulator** to use new metrics
4. **Apply pace** in GameSimulator
5. **Add situational factors** (rest, weather) if time permits

