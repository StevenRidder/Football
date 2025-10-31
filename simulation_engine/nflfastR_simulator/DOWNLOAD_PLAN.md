# Data Download Plan - Missing Signals

## ✅ Great News: All Data Available from nflfastR!

**No additional APIs needed** - everything can be calculated from `nfl_data_py` which we already use.

---

## 📥 Scripts to Create (All Use nflfastR)

### 1. **extract_yards_per_play.py** ⭐ CRITICAL
**Purpose:** Calculate YPP, YPA for all teams  
**Data Source:** `nfl.import_pbp_data([2022, 2023, 2024, 2025])`  
**Output:** `data/nflfastR/team_yards_per_play.csv`

**Columns:**
- `posteam`, `season`, `week`
- `off_yards_per_play`
- `off_yards_per_pass_attempt`
- `def_yards_per_play_allowed`
- `def_yards_per_pass_allowed`

**Formula:**
- YPP = `yards_gained.mean()` (all plays)
- YPA = `yards_gained[pass==1].mean()` (pass attempts only)

---

### 2. **extract_early_down_success.py** ⭐ CRITICAL
**Purpose:** Calculate early-down success rate  
**Data Source:** `nfl.import_pbp_data([2022, 2023, 2024, 2025])`  
**Output:** `data/nflfastR/early_down_success_rate.csv`

**Columns:**
- `posteam`, `season`, `week`
- `first_down_success_rate` (gained 40% of needed)
- `second_down_success_rate` (gained 50% of needed)
- `early_down_success_rate` (combined 1st+2nd)

**Formula:**
- Filter `down == 1`, success = `yards_gained >= 0.4 * ydstogo`
- Filter `down == 2`, success = `yards_gained >= 0.5 * ydstogo`

---

### 3. **extract_anya.py** ⭐ MEDIUM VALUE
**Purpose:** Calculate Adjusted Net Yards per Attempt  
**Data Source:** `nfl.import_pbp_data([2022, 2023, 2024, 2025])`  
**Output:** `data/nflfastR/team_anya.csv`

**Columns:**
- `posteam`, `season`, `week`
- `off_anya` (offensive ANY/A)
- `def_anya_allowed` (defensive ANY/A allowed)

**Formula:**
```
ANY/A = (pass_yards + 20*pass_tds - 45*ints - sack_yards) / (pass_attempts + sacks)
```

**From nflfastR:**
- `pass_yards`: `yards_gained[pass_attempt==1].sum()`
- `pass_tds`: `touchdown[pass_attempt==1].sum()`
- `ints`: `interception.sum()`
- `sack_yards`: `yards_gained[sack==1].sum()` (negative)
- `pass_attempts`: `pass_attempt.sum()`
- `sacks`: `sack.sum()`

---

### 4. **extract_turnover_regression.py** ⭐ HIGH VALUE
**Purpose:** Track turnover margins for regression  
**Data Source:** `nfl.import_pbp_data([2022, 2023, 2024, 2025])`  
**Output:** `data/nflfastR/turnover_regression.csv`

**Columns:**
- `posteam`, `season`, `week`
- `turnovers_forced` (interceptions + fumbles recovered)
- `turnovers_lost` (interceptions thrown + fumbles lost)
- `turnover_margin`
- `recent_margin` (last 2 games)
- `rolling_margin` (8-game window)
- `regression_factor` (should fade if recent >> rolling)

---

### 5. **extract_red_zone.py** ⭐ MEDIUM VALUE
**Purpose:** Red zone opportunities vs conversion %  
**Data Source:** `nfl.import_pbp_data([2022, 2023, 2024, 2025])`  
**Output:** `data/nflfastR/red_zone_stats.csv`

**Columns:**
- `posteam`, `season`, `week`
- `red_zone_trips` (drives reaching opponent 20)
- `red_zone_td_pct` (TDs / trips)
- `red_zone_fg_pct` (FGs / trips)
- `red_zone_trips_per_game` (more stable than conversion %)

---

### 6. **extract_special_teams.py** ⭐ MEDIUM VALUE
**Purpose:** Special teams performance  
**Data Source:** `nfl.import_pbp_data([2022, 2023, 2024, 2025])`  
**Output:** `data/nflfastR/special_teams.csv`

**Columns:**
- `posteam`, `season`, `week`
- `punt_net_yards` (punt distance - return yards)
- `field_goal_make_pct`
- `kick_return_avg`
- `punt_return_avg`

**From nflfastR:**
- Punt: `punts`, `punt_blocked`, `punt_in_endzone`
- FG: `field_goal_result` (made/missed)
- Returns: `kickoff_return`, `punt_return` with `yards_gained`

---

### 7. **extract_situational_factors.py** ⭐ LOW-MEDIUM VALUE
**Purpose:** Rest, weather, dome factors  
**Data Source:** `nfl.import_schedules([2022, 2023, 2024, 2025])`  
**Output:** `data/nflfastR/situational_factors.csv`

**Columns:**
- `game_id`, `season`, `week`, `home_team`, `away_team`
- `home_rest_days` (from `home_rest`)
- `away_rest_days` (from `away_rest`)
- `roof` (dome/outdoors)
- `temp` (temperature)
- `wind` (wind speed)
- `surface` (grass/turf)

**Note:** Already in schedule data! Just need to extract.

---

## 🚀 Execution Order

### Step 1: Create All Extraction Scripts
All scripts should follow the pattern of existing ones:
- `preprocessing/extract_playcalling.py` (example)
- `preprocessing/extract_qb_splits.py` (example)

**Template:**
```python
import nfl_data_py as nfl
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "nflfastR"

def extract_metric(seasons=[2022, 2023, 2024, 2025]):
    pbp = nfl.import_pbp_data(seasons)
    # Calculate metric
    # Save to CSV
```

### Step 2: Run All Extraction Scripts
```bash
cd preprocessing
python3 extract_yards_per_play.py
python3 extract_early_down_success.py
python3 extract_anya.py
python3 extract_turnover_regression.py
python3 extract_red_zone.py
python3 extract_special_teams.py
python3 extract_situational_factors.py
```

### Step 3: Update TeamProfile
Load all new CSV files in `TeamProfile.__init__()`

### Step 4: Update Simulator
Use new metrics in `PlaySimulator` and `GameSimulator`

---

## 📋 Quick Start: First Script

Let's create `extract_yards_per_play.py` as the first one since YPP/YPA is most critical:

**Should I create this script now?**

