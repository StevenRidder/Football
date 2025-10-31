# Weekly Data Update Plan

## Overview

This document outlines how to update all required data each week for making new predictions.

## Data Sources

All data comes from **nflfastR** (nfl_data_py package) - no additional APIs needed!

## Extraction Scripts

All extraction scripts are located in `preprocessing/`:

1. **`extract_yards_per_play.py`** - YPP, YPA (offense and defense)
2. **`extract_early_down_success.py`** - Success rates on 1st/2nd downs
3. **`extract_anya.py`** - Adjusted Net Yards per Attempt
4. **`extract_turnover_regression.py`** - Turnover margins and regression factors
5. **`extract_red_zone.py`** - Red zone trips and conversion rates
6. **`extract_special_teams.py`** - Punt net yards, FG %, return averages
7. **`extract_situational_factors.py`** - Rest days, weather, dome status

## Weekly Update Process

### Option 1: Use Master Update Script (Recommended)

```bash
cd simulation_engine/nflfastR_simulator
python scripts/update_weekly_data.py
```

This script:
- Auto-detects the latest completed week
- Runs all extraction scripts
- Outputs summary of successes/failures

### Option 2: Run All Extractions Manually

```bash
cd preprocessing
python extract_all_metrics.py
```

### Option 3: Run Individual Scripts

```bash
cd preprocessing
python extract_yards_per_play.py
python extract_early_down_success.py
# ... etc
```

## When to Update

**Run the update script:**
- Every Tuesday after Week 1 ends (to get Week 1 data)
- Before making predictions for the upcoming week
- After any week is completed to have latest data for backtests

## Output Files

All data files are saved to `data/nflfastR/`:

### Weekly Files (updated each week)
- `team_yards_per_play_weekly.csv`
- `early_down_success_weekly.csv`
- `team_anya_weekly.csv`
- `turnover_regression_weekly.csv`
- `red_zone_stats_weekly.csv`
- `special_teams_weekly.csv`

### Season Average Files (calculated from weekly)
- `team_yards_per_play_season.csv`
- `early_down_success_season.csv`
- `team_anya_season.csv`
- `turnover_regression_season.csv`
- `red_zone_stats_season.csv`
- `special_teams_season.csv`

### Static Files (updated less frequently)
- `situational_factors.csv` (from schedule)

## Data Usage in Simulator

The `TeamProfile` class automatically loads all these metrics when initialized:

```python
team = TeamProfile('KC', 2025, 8, data_dir)
# Now has:
# - team.off_yards_per_play
# - team.off_yards_per_pass_attempt
# - team.early_down_success_rate
# - team.off_anya
# - team.turnover_regression_factor
# - team.red_zone_trips_per_game
# - team.punt_net_yards
# - etc.
```

## Integration with Existing Data

These new metrics complement existing data already loaded:
- ✅ EPA (from `rolling_epa_2022_2025.csv`)
- ✅ QB Pressure Splits (from `qb_pressure_splits_season.csv`)
- ✅ Playcalling Tendencies (from `playcalling_tendencies_season.csv`)
- ✅ Drive Probabilities (from `drive_probabilities_season.csv`)
- ✅ Pace (from `team_pace.csv`)
- ✅ PFF Grades (from `data/pff_raw/team_grades_*.csv`)

## Future Enhancements

These metrics are loaded but not yet integrated into play simulation logic:
- YPP/YPA - Can adjust yards gained distributions
- Early-Down Success - Can modify drive continuation probability
- ANY/A - Can adjust QB efficiency ratings
- Turnover Regression - Can apply efficiency multiplier
- Red Zone - Can adjust TD probability when inside 20
- Special Teams - Can adjust field position on punts/kickoffs

See `MISSING_SIGNALS_ANALYSIS.md` for implementation priorities.

## Troubleshooting

### Script fails with "No data found"
- Ensure nflfastR has data for the requested season/week
- Check internet connection (nflfastR downloads from GitHub)

### Missing columns in output
- Some metrics may not be available for all teams/weeks
- Scripts fill with season averages automatically

### Slow extraction
- First run extracts all historical data (2022-2025)
- Subsequent runs only add new weeks (much faster)

## Notes

- All scripts use season averages as fallback if weekly data unavailable
- Data is persisted to CSV for fast loading during simulation
- Scripts are idempotent (safe to run multiple times)

