"""
Extract drive outcome probabilities from nflfastR play-by-play data.

Outputs:
- drive_probabilities.csv: Drive outcome probabilities by starting field position
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "nflfastR"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_pbp_data(seasons):
    """Load play-by-play data for given seasons."""
    print(f"📊 Loading play-by-play data for {seasons}...")
    pbp = nfl.import_pbp_data(seasons)
    print(f"   Loaded {len(pbp):,} plays")
    return pbp


def extract_drive_probabilities(pbp_df):
    """
    Extract drive outcome probabilities by starting field position.
    
    Field position buckets:
    - own_10: 0-10 yards (own 10 or worse)
    - own_20: 11-20 yards
    - own_35: 21-35 yards
    - midfield: 36-50 yards
    - opp_35: 51-65 yards
    - opp_20: 66-80 yards
    - opp_10: 81-100 yards (opponent 20 or better)
    
    Outcomes:
    - TD: Touchdown
    - FG: Field goal
    - Punt: Punt
    - Turnover: Interception or fumble lost
    - Downs: Turnover on downs
    - End of half: Drive ends due to time
    
    Returns DataFrame with:
    - posteam, season, week
    - start_yardline_bucket
    - td_prob, fg_prob, punt_prob, turnover_prob, downs_prob, end_half_prob
    """
    print("\n🔬 Extracting drive probabilities...")
    
    # Get all drives
    drives = pbp_df[
        (pbp_df['posteam'].notna()) &
        (pbp_df['drive'].notna())
    ].copy()
    
    # Get first play of each drive (for starting field position)
    drive_starts = drives.groupby(['game_id', 'drive']).first().reset_index()
    
    # Get last play of each drive (for outcome)
    drive_ends = drives.groupby(['game_id', 'drive']).last().reset_index()
    
    # Merge start and end
    drive_data = pd.merge(
        drive_starts[['game_id', 'drive', 'posteam', 'season', 'week', 'yardline_100']],
        drive_ends[['game_id', 'drive', 'touchdown', 'field_goal_result', 'punt_attempt', 
                    'interception', 'fumble_lost', 'fourth_down_failed', 'game_half']],
        on=['game_id', 'drive'],
        how='inner'
    )
    
    print(f"   Total drives: {len(drive_data):,}")
    
    # Bucket starting field position
    drive_data['start_yardline_bucket'] = pd.cut(
        drive_data['yardline_100'],
        bins=[0, 10, 20, 35, 50, 65, 80, 100],
        labels=['opp_10', 'opp_20', 'opp_35', 'midfield', 'own_35', 'own_20', 'own_10'],
        include_lowest=True
    )
    
    # Determine drive outcome
    def get_drive_outcome(row):
        if row['touchdown'] == 1:
            return 'TD'
        elif row['field_goal_result'] == 'made':
            return 'FG'
        elif row['punt_attempt'] == 1:
            return 'Punt'
        elif row['interception'] == 1 or row['fumble_lost'] == 1:
            return 'Turnover'
        elif row['fourth_down_failed'] == 1:
            return 'Downs'
        else:
            return 'End_Half'
    
    drive_data['outcome'] = drive_data.apply(get_drive_outcome, axis=1)
    
    # Group by team, season, week, starting field position
    drive_probs = drive_data.groupby([
        'posteam', 'season', 'week', 'start_yardline_bucket'
    ])['outcome'].value_counts(normalize=True).unstack(fill_value=0).reset_index()
    
    # Ensure all outcome columns exist
    for outcome in ['TD', 'FG', 'Punt', 'Turnover', 'Downs', 'End_Half']:
        if outcome not in drive_probs.columns:
            drive_probs[outcome] = 0
    
    # Rename columns
    drive_probs.rename(columns={
        'TD': 'td_prob',
        'FG': 'fg_prob',
        'Punt': 'punt_prob',
        'Turnover': 'turnover_prob',
        'Downs': 'downs_prob',
        'End_Half': 'end_half_prob'
    }, inplace=True)
    
    # Count total drives per situation
    drive_counts = drive_data.groupby([
        'posteam', 'season', 'week', 'start_yardline_bucket'
    ]).size().reset_index(name='total_drives')
    
    # Merge counts
    drive_probs = pd.merge(drive_probs, drive_counts, on=['posteam', 'season', 'week', 'start_yardline_bucket'])
    
    # Filter to situations with at least 3 drives
    drive_probs = drive_probs[drive_probs['total_drives'] >= 3].copy()
    
    print(f"   Team-week-field positions: {len(drive_probs):,}")
    
    return drive_probs


def calculate_season_averages(drive_probs):
    """Calculate season-long averages for teams."""
    print("\n📊 Calculating season averages...")
    
    # Group by team, season, field position
    season_avg = drive_probs.groupby([
        'posteam', 'season', 'start_yardline_bucket'
    ]).agg({
        'td_prob': 'mean',
        'fg_prob': 'mean',
        'punt_prob': 'mean',
        'turnover_prob': 'mean',
        'downs_prob': 'mean',
        'end_half_prob': 'mean',
        'total_drives': 'sum'
    }).reset_index()
    
    # Filter to situations with at least 10 drives
    season_avg = season_avg[season_avg['total_drives'] >= 10].copy()
    
    print(f"   Team-season-field positions: {len(season_avg):,}")
    
    return season_avg


def calculate_league_averages(drive_probs):
    """Calculate league-wide averages by field position."""
    print("\n🏈 Calculating league averages...")
    
    league_avg = drive_probs.groupby('start_yardline_bucket').agg({
        'td_prob': 'mean',
        'fg_prob': 'mean',
        'punt_prob': 'mean',
        'turnover_prob': 'mean',
        'downs_prob': 'mean',
        'end_half_prob': 'mean',
        'total_drives': 'sum'
    }).reset_index()
    
    print(f"   Field position buckets: {len(league_avg)}")
    
    return league_avg


def main():
    """Extract drive probabilities from nflfastR data."""
    print("="*80)
    print("EXTRACT DRIVE PROBABILITIES FROM nflfastR")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Extract drive probabilities
    drive_probs = extract_drive_probabilities(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(drive_probs)
    
    # Calculate league averages
    league_avg = calculate_league_averages(drive_probs)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "drive_probabilities_weekly.csv"
    drive_probs.to_csv(weekly_path, index=False)
    print(f"   Weekly probabilities: {weekly_path}")
    
    season_path = DATA_DIR / "drive_probabilities_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    league_path = DATA_DIR / "drive_probabilities_league.csv"
    league_avg.to_csv(league_path, index=False)
    print(f"   League averages: {league_path}")
    
    # Summary stats
    print("\n" + "="*80)
    print("📊 SUMMARY - LEAGUE AVERAGES BY FIELD POSITION")
    print("="*80)
    
    print(f"\n{'Field Position':<15} {'TD%':<10} {'FG%':<10} {'Punt%':<10} {'TO%':<10} {'Drives':<10}")
    print("-"*65)
    
    for _, row in league_avg.iterrows():
        print(f"{row['start_yardline_bucket']:<15} "
              f"{row['td_prob']:<10.1%} "
              f"{row['fg_prob']:<10.1%} "
              f"{row['punt_prob']:<10.1%} "
              f"{row['turnover_prob']:<10.1%} "
              f"{int(row['total_drives']):<10,}")
    
    print("\n" + "="*80)
    print("✅ DRIVE PROBABILITIES EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

