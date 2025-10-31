# PFF Data Collection Summary

## Data Successfully Collected

### Team Overview Data (OL/DL Grades)
Successfully extracted **6 complete datasets** with full PFF grades:

1. **2020 Full Season** - 32 teams, all weeks + playoffs
2. **2021 Full Season** - 32 teams, all weeks + playoffs
3. **2022 Full Season** - 32 teams, all weeks + playoffs
4. **2023 Full Season** - 32 teams, all weeks + playoffs
5. **2024 Full Season** - 32 teams, all weeks + playoffs
6. **2025 Weeks 1-8** - 32 teams, weeks 1-8 only

## Key Metrics Included

Each dataset contains the following PFF grades for all 32 NFL teams:

### Offensive Line Grades
- `grades_pass_block` - Pass blocking grade (PBLK)
- `grades_run_block` - Run blocking grade (RBLK)

### Defensive Line Grades
- `grades_pass_rush_defense` - Pass rush grade (PRSH)
- `grades_run_defense` - Run defense grade (RDEF)

### Additional Grades
- `grades_offense` - Overall offensive grade
- `grades_defense` - Overall defensive grade
- `grades_coverage_defense` - Coverage grade (COV)
- `grades_tackle` - Tackling grade (TACK)
- `grades_pass` - Passing grade
- `grades_pass_route` - Route running grade (RECV)
- `grades_run` - Rushing grade
- `grades_misc_st` - Special teams grade (SPEC)
- `grades_overall` - Overall team grade

### Team Statistics
- Win-loss records
- Points scored
- Points allowed
- Team abbreviations and full names

## Data Source

All data extracted from PFF Premium API:
- **Endpoint**: `https://premium.pff.com/api/v1/teams/overview`
- **Authentication**: Premium subscription required
- **Date Collected**: October 30, 2024

## File Format

JSON format with structure:
```json
{
  "team_overview": [
    {
      "abbreviation": "BUF",
      "name": "Buffalo Bills",
      "grades_pass_block": 73.7,
      "grades_pass_rush_defense": 78.8,
      "grades_coverage_defense": 68.5,
      ...
    }
  ]
}
```

## Usage in Betting Model

This data will be integrated into the NFL betting simulator to:

1. **Model OL vs DL Matchups**
   - Compare offensive line pass blocking vs defensive line pass rush
   - Adjust QB pressure rates based on matchup quality
   - Model sack rates and QB performance under pressure

2. **Improve Run Game Modeling**
   - OL run blocking vs DL run defense matchups
   - Adjust yards per carry based on line quality
   - Model goal-line and short-yardage situations

3. **Enhance Game Script Modeling**
   - Use overall team grades for game flow predictions
   - Adjust play-calling based on team strengths/weaknesses
   - Model coaching tendencies based on personnel quality

4. **Historical Validation**
   - 5 years of data (2020-2024) for backtesting
   - Test if OL/DL grades improve betting model performance
   - Measure "module rent" - does PFF data beat baseline?

## Next Steps

1. ✅ **Data Collection Complete** - All 6 datasets collected
2. ⏭️ **Parse and Structure** - Convert JSON to usable format
3. ⏭️ **Integrate into Simulator** - Add PFF grades to `TeamProfile`
4. ⏭️ **Backtest** - Test on 2020-2023, validate on 2024
5. ⏭️ **Measure Impact** - Does PFF data improve ROI vs baseline?

## Data Quality

- ✅ All 32 teams present in each dataset
- ✅ All key grade fields populated
- ✅ No missing or null values
- ✅ Consistent data structure across all years
- ✅ Authenticated API access (not scraped/restricted data)

## Storage

- **Location**: `/Users/steveridder/Git/Football/simulation_engine/nflfastR_simulator/data/pff_raw/`
- **Total Size**: ~350KB (6 JSON files)
- **Format**: Pretty-printed JSON for readability
