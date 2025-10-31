"""
Extract team play-calling tendencies from nflfastR play-by-play data.

Outputs:
- playcalling_tendencies.csv: Pass/run rates by situation
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


def extract_playcalling_tendencies(pbp_df):
    """
    Extract team play-calling tendencies by situation.
    
    Situations:
    - Down (1, 2, 3, 4)
    - Distance (short: 1-3, medium: 4-7, long: 8+)
    - Score differential (down 14+, down 7-13, down 1-6, tied, up 1-6, up 7-13, up 14+)
    - Time remaining (Q1, Q2, Q3, Q4-early, Q4-late, 2min)
    
    Returns DataFrame with:
    - posteam, season, week
    - down, distance_bucket, score_diff_bucket, time_bucket
    - pass_rate, run_rate, plays
    """
    print("\n🔬 Extracting play-calling tendencies...")
    
    # Filter to offensive plays (pass or run)
    plays = pbp_df[
        (pbp_df['play_type'].isin(['pass', 'run'])) &
        (pbp_df['posteam'].notna()) &
        (pbp_df['down'].notna())
    ].copy()
    
    print(f"   Offensive plays: {len(plays):,}")
    
    # Bucket distance
    plays['distance_bucket'] = pd.cut(
        plays['ydstogo'], 
        bins=[0, 3, 7, 100], 
        labels=['short', 'medium', 'long'],
        include_lowest=True
    )
    
    # Bucket score differential
    plays['score_diff_bucket'] = pd.cut(
        plays['score_differential'],
        bins=[-100, -14, -7, -1, 1, 7, 14, 100],
        labels=['down_14+', 'down_7-13', 'down_1-6', 'tied', 'up_1-6', 'up_7-13', 'up_14+'],
        include_lowest=True
    )
    
    # Bucket time remaining
    def time_bucket(seconds):
        if seconds < 120:
            return '2min'
        elif seconds < 900:
            return 'Q4_late'
        elif seconds < 1800:
            return 'Q3-Q4'
        elif seconds < 2700:
            return 'Q2-Q3'
        else:
            return 'Q1-Q2'
    
    plays['time_bucket'] = plays['game_seconds_remaining'].apply(time_bucket)
    
    # Group by team, situation
    tendencies = plays.groupby([
        'posteam', 'season', 'week', 
        'down', 'distance_bucket', 'score_diff_bucket', 'time_bucket'
    ]).agg({
        'play_type': [
            lambda x: (x == 'pass').sum(),  # Pass count
            lambda x: (x == 'run').sum(),   # Run count
            'count'                         # Total plays
        ]
    }).reset_index()
    
    # Flatten column names
    tendencies.columns = [
        'posteam', 'season', 'week', 
        'down', 'distance_bucket', 'score_diff_bucket', 'time_bucket',
        'pass_count', 'run_count', 'total_plays'
    ]
    
    # Calculate rates
    tendencies['pass_rate'] = tendencies['pass_count'] / tendencies['total_plays']
    tendencies['run_rate'] = tendencies['run_count'] / tendencies['total_plays']
    
    # Filter to situations with at least 2 plays (lowered for early season)
    # Week 1 data is sparse, but we need at least some data for simulation
    tendencies = tendencies[tendencies['total_plays'] >= 2].copy()
    
    print(f"   Team-week-situations: {len(tendencies):,}")
    
    return tendencies


def calculate_season_averages(tendencies):
    """Calculate season-long averages for teams."""
    print("\n📊 Calculating season averages...")
    
    season_avg = tendencies.groupby([
        'posteam', 'season',
        'down', 'distance_bucket', 'score_diff_bucket', 'time_bucket'
    ]).agg({
        'pass_count': 'sum',
        'run_count': 'sum',
        'total_plays': 'sum'
    }).reset_index()
    
    # Recalculate rates
    season_avg['pass_rate'] = season_avg['pass_count'] / season_avg['total_plays']
    season_avg['run_rate'] = season_avg['run_count'] / season_avg['total_plays']
    
    # Filter to situations with at least 20 plays
    season_avg = season_avg[season_avg['total_plays'] >= 20].copy()
    
    print(f"   Team-season-situations: {len(season_avg):,}")
    
    return season_avg


def calculate_pace(pbp_df):
    """Calculate team pace (plays per drive)."""
    print("\n⏱️  Calculating team pace...")
    
    # Get drives
    drives = pbp_df[
        (pbp_df['posteam'].notna()) &
        (pbp_df['play_type'].isin(['pass', 'run', 'punt', 'field_goal']))
    ].copy()
    
    # Group by team, season, week, drive
    pace = drives.groupby(['posteam', 'season', 'week', 'game_id', 'drive']).size().reset_index(name='plays_in_drive')
    
    # Average plays per drive
    team_pace = pace.groupby(['posteam', 'season', 'week']).agg({
        'plays_in_drive': 'mean',
        'drive': 'count'  # Total drives
    }).reset_index()
    
    team_pace.rename(columns={
        'plays_in_drive': 'avg_plays_per_drive',
        'drive': 'total_drives'
    }, inplace=True)
    
    print(f"   Team-weeks: {len(team_pace):,}")
    print(f"   Average plays per drive: {team_pace['avg_plays_per_drive'].mean():.1f}")
    
    return team_pace


def main():
    """Extract play-calling tendencies from nflfastR data."""
    print("="*80)
    print("EXTRACT PLAY-CALLING TENDENCIES FROM nflfastR")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Extract play-calling tendencies
    tendencies = extract_playcalling_tendencies(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(tendencies)
    
    # Calculate pace
    pace = calculate_pace(pbp)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "playcalling_tendencies_weekly.csv"
    tendencies.to_csv(weekly_path, index=False)
    print(f"   Weekly tendencies: {weekly_path}")
    
    season_path = DATA_DIR / "playcalling_tendencies_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    pace_path = DATA_DIR / "team_pace.csv"
    pace.to_csv(pace_path, index=False)
    print(f"   Team pace: {pace_path}")
    
    # Summary stats
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    print(f"\nPass Rate by Down (Season Averages):")
    down_summary = season_avg.groupby('down')['pass_rate'].mean()
    for down, rate in down_summary.items():
        print(f"   {down}st/nd/rd/th down: {rate:.1%}")
    
    print(f"\nPass Rate by Score Differential (Season Averages):")
    score_summary = season_avg.groupby('score_diff_bucket')['pass_rate'].mean().sort_index()
    for score_diff, rate in score_summary.items():
        print(f"   {score_diff}: {rate:.1%}")
    
    print(f"\nPass Rate by Time Remaining (Season Averages):")
    time_summary = season_avg.groupby('time_bucket')['pass_rate'].mean()
    for time_bucket, rate in time_summary.items():
        print(f"   {time_bucket}: {rate:.1%}")
    
    print("\n" + "="*80)
    print("✅ PLAY-CALLING TENDENCIES EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

