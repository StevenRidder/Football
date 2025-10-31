"""
Extract Red Zone statistics from nflfastR play-by-play data.

Strategy: "Best red zone teams are the ones that get there, not ones with 
          high conversion %. Focus on opportunities, regress conversion rates."

Outputs:
- red_zone_stats.csv: Red zone trips and conversion rates
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


def extract_red_zone_stats(pbp_df):
    """
    Extract red zone opportunities and conversion rates.
    
    Red zone = opponent's 20-yard line or closer
    Focus on trips (opportunities) more than conversion %
    
    Returns DataFrame with:
    - posteam, season, week
    - red_zone_trips (drives reaching opponent 20)
    - red_zone_td_pct
    - red_zone_fg_pct
    - red_zone_trips_per_game
    """
    print("\n🔬 Extracting red zone statistics...")
    
    # Get drives
    drives = pbp_df[
        (pbp_df['posteam'].notna()) &
        (pbp_df['drive'].notna())
    ].copy()
    
    # Identify red zone trips (any play inside opponent 20)
    drives['is_redzone'] = drives['yardline_100'] <= 20
    
    # Group by drive to count trips
    drive_summary = drives.groupby(['posteam', 'season', 'week', 'game_id', 'drive']).agg({
        'is_redzone': 'max',  # Did drive reach red zone?
        'touchdown': 'sum',   # TDs in drive
        'field_goal_result': lambda x: (x == 'made').sum() if 'field_goal_result' in drives.columns else 0
    }).reset_index()
    
    # Count red zone trips per game
    redzone_trips = drive_summary[drive_summary['is_redzone'] == True].groupby(['posteam', 'season', 'week']).size().reset_index(name='red_zone_trips')
    
    # Count TDs and FGs in red zone drives
    redzone_tds = drive_summary[drive_summary['is_redzone'] == True].groupby(['posteam', 'season', 'week'])['touchdown'].sum().reset_index(name='red_zone_tds')
    
    redzone_fgs = drive_summary[
        (drive_summary['is_redzone'] == True) &
        (drive_summary['field_goal_result'].notna() if 'field_goal_result' in drive_summary.columns else pd.Series([False] * len(drive_summary)))
    ].groupby(['posteam', 'season', 'week']).size().reset_index(name='red_zone_fgs')
    
    # Merge
    redzone = redzone_trips.merge(redzone_tds, on=['posteam', 'season', 'week'], how='left')
    redzone = redzone.merge(redzone_fgs, on=['posteam', 'season', 'week'], how='left')
    
    # Fill missing
    redzone = redzone.fillna(0)
    
    # Calculate rates
    redzone['red_zone_td_pct'] = redzone['red_zone_tds'] / redzone['red_zone_trips']
    redzone['red_zone_td_pct'] = redzone['red_zone_td_pct'].fillna(0)
    
    redzone['red_zone_fg_pct'] = redzone['red_zone_fgs'] / redzone['red_zone_trips']
    redzone['red_zone_fg_pct'] = redzone['red_zone_fg_pct'].fillna(0)
    
    # Calculate trips per game (need game count)
    games = drives.groupby(['posteam', 'season', 'week'])['game_id'].nunique().reset_index()
    games.columns = ['posteam', 'season', 'week', 'games']
    redzone = redzone.merge(games, on=['posteam', 'season', 'week'], how='left')
    redzone['games'] = redzone['games'].fillna(1)
    redzone['red_zone_trips_per_game'] = redzone['red_zone_trips'] / redzone['games']
    
    # Drop intermediate columns
    result = redzone[['posteam', 'season', 'week', 'red_zone_trips', 'red_zone_trips_per_game', 
                      'red_zone_td_pct', 'red_zone_fg_pct']].copy()
    
    print(f"   Team-weeks: {len(result):,}")
    print(f"   Avg Red Zone Trips/Game: {result['red_zone_trips_per_game'].mean():.2f}")
    print(f"   Avg Red Zone TD %: {result['red_zone_td_pct'].mean():.1%}")
    
    return result


def calculate_season_averages(redzone_df):
    """Calculate season-long averages."""
    print("\n📊 Calculating season averages...")
    
    season_avg = redzone_df.groupby(['posteam', 'season']).agg({
        'red_zone_trips_per_game': 'mean',
        'red_zone_td_pct': 'mean',
        'red_zone_fg_pct': 'mean'
    }).reset_index()
    
    print(f"   Team-seasons: {len(season_avg):,}")
    
    return season_avg


def main():
    """Extract red zone stats from nflfastR data."""
    print("="*80)
    print("EXTRACT RED ZONE STATISTICS")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Extract red zone stats
    redzone = extract_red_zone_stats(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(redzone)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "red_zone_stats_weekly.csv"
    redzone.to_csv(weekly_path, index=False)
    print(f"   Weekly red zone stats: {weekly_path}")
    
    season_path = DATA_DIR / "red_zone_stats_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    print("\n" + "="*80)
    print("✅ RED ZONE STATISTICS EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

