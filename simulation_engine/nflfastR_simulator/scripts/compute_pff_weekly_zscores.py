"""
Compute PFF z-scores within each week for all 2024 games.
This creates a lookup table for zero-mean adjustments.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from scipy import stats

# Load PFF data
pff_file = Path("data/pff_raw/team_grades_2024.csv")
if not pff_file.exists():
    print(f"❌ PFF file not found: {pff_file}")
    sys.exit(1)

pff = pd.read_csv(pff_file)
print(f"✅ Loaded {len(pff)} PFF team records")

# Load 2024 games
sys.path.insert(0, str(Path(__file__).parent.parent))
from backtest_ultra_fast import load_games_2024

games = load_games_2024()
print(f"✅ Loaded {len(games)} games from 2024 weeks 1-8")

# Prepare PFF data - use abbreviation for matching
# Don't rename to avoid conflicts

# For each week, compute z-scores
results = []

for week in range(1, 9):
    week_games = games[games['week'] == week]
    if len(week_games) == 0:
        continue
    
    print(f"\n📊 Week {week}: {len(week_games)} games")
    
    # Get all teams playing this week
    teams_this_week = set(week_games['home_team'].tolist() + week_games['away_team'].tolist())
    
    # Get PFF grades for these teams (use abbreviation column)
    week_pff = pff[pff['abbreviation'].isin(teams_this_week)].copy().reset_index(drop=True)
    
    if len(week_pff) == 0:
        print(f"   ⚠️  No PFF data for week {week}")
        continue
    
    # Compute z-scores within this week's slate
    for col in ['pass_block_grade', 'pass_rush_grade', 'run_block_grade', 'run_defense_grade']:
        if col in week_pff.columns:
            week_pff[f'{col}_z'] = stats.zscore(week_pff[col], nan_policy='omit')
    
    # For each game, compute matchup z-scores
    for _, game in week_games.iterrows():
        home = game['home_team']
        away = game['away_team']
        
        home_pff = week_pff[week_pff['abbreviation'] == home]
        away_pff = week_pff[week_pff['abbreviation'] == away]
        
        if len(home_pff) == 0 or len(away_pff) == 0:
            continue
        
        # Home offense vs Away defense
        home_ol_z = home_pff['pass_block_grade_z'].values[0] if 'pass_block_grade_z' in home_pff.columns else 0
        away_dl_z = away_pff['pass_rush_grade_z'].values[0] if 'pass_rush_grade_z' in away_pff.columns else 0
        home_pass_mismatch_z = home_ol_z - away_dl_z
        
        # Away offense vs Home defense
        away_ol_z = away_pff['pass_block_grade_z'].values[0] if 'pass_block_grade_z' in away_pff.columns else 0
        home_dl_z = home_pff['pass_rush_grade_z'].values[0] if 'pass_rush_grade_z' in home_pff.columns else 0
        away_pass_mismatch_z = away_ol_z - home_dl_z
        
        # Run game
        home_run_ol_z = home_pff['run_block_grade_z'].values[0] if 'run_block_grade_z' in home_pff.columns else 0
        away_run_dl_z = away_pff['run_defense_grade_z'].values[0] if 'run_defense_grade_z' in away_pff.columns else 0
        home_run_mismatch_z = home_run_ol_z - away_run_dl_z
        
        away_run_ol_z = away_pff['run_block_grade_z'].values[0] if 'run_block_grade_z' in away_pff.columns else 0
        home_run_dl_z = home_pff['run_defense_grade_z'].values[0] if 'run_defense_grade_z' in home_pff.columns else 0
        away_run_mismatch_z = away_run_ol_z - home_run_dl_z
        
        results.append({
            'season': 2024,
            'week': week,
            'home_team': home,
            'away_team': away,
            'home_pass_mismatch_z': home_pass_mismatch_z,
            'away_pass_mismatch_z': away_pass_mismatch_z,
            'home_run_mismatch_z': home_run_mismatch_z,
            'away_run_mismatch_z': away_run_mismatch_z,
        })

# Save results
results_df = pd.DataFrame(results)

# Verify zero-mean by week
print("\n📊 ZERO-MEAN VERIFICATION:")
for week in range(1, 9):
    week_data = results_df[results_df['week'] == week]
    if len(week_data) == 0:
        continue
    
    # Combine home and away mismatches
    all_pass = list(week_data['home_pass_mismatch_z']) + list(week_data['away_pass_mismatch_z'])
    all_run = list(week_data['home_run_mismatch_z']) + list(week_data['away_run_mismatch_z'])
    
    print(f"   Week {week}: pass_mismatch mean={np.mean(all_pass):.4f}, run_mismatch mean={np.mean(all_run):.4f}")

# Save
output_file = Path("data/pff_raw/pff_weekly_zscores_2024.csv")
results_df.to_csv(output_file, index=False)
print(f"\n✅ Saved {len(results_df)} game matchup z-scores to {output_file}")

