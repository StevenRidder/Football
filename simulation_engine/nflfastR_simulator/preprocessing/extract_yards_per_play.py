"""
Extract Yards Per Play and Yards Per Pass Attempt from nflfastR play-by-play data.

Strategy: "Teams winning YPA win ~97% of games outright and ~80% ATS"

Outputs:
- team_yards_per_play.csv: YPP and YPA for offense and defense
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


def extract_yards_per_play(pbp_df):
    """
    Extract yards per play and yards per pass attempt for all teams.
    
    Returns DataFrame with:
    - posteam, season, week
    - off_yards_per_play, off_yards_per_pass_attempt
    - def_yards_per_play_allowed, def_yards_per_pass_allowed
    """
    print("\n🔬 Extracting yards per play metrics...")
    
    # Filter to offensive plays
    off_plays = pbp_df[
        (pbp_df['play_type'].isin(['pass', 'run'])) &
        (pbp_df['posteam'].notna()) &
        (pbp_df['yards_gained'].notna())
    ].copy()
    
    print(f"   Offensive plays: {len(off_plays):,}")
    
    # OFFENSIVE YPP (yards per play)
    off_ypp = off_plays.groupby(['posteam', 'season', 'week']).agg({
        'yards_gained': ['mean', 'count'],
        'pass': 'sum',  # Pass attempts
        'rush': 'sum'   # Rush attempts
    }).reset_index()
    
    off_ypp.columns = ['posteam', 'season', 'week', 'off_yards_per_play', 'off_plays', 'off_pass_attempts', 'off_rush_attempts']
    
    # OFFENSIVE YPA (yards per pass attempt)
    pass_plays = off_plays[off_plays['pass'] == 1].copy()
    off_ypa = pass_plays.groupby(['posteam', 'season', 'week']).agg({
        'yards_gained': 'mean'
    }).reset_index()
    off_ypa.columns = ['posteam', 'season', 'week', 'off_yards_per_pass_attempt']
    
    # DEFENSIVE (allowed to opponent)
    def_plays = pbp_df[
        (pbp_df['play_type'].isin(['pass', 'run'])) &
        (pbp_df['defteam'].notna()) &
        (pbp_df['yards_gained'].notna())
    ].copy()
    
    # DEFENSIVE YPP ALLOWED
    def_ypp = def_plays.groupby(['defteam', 'season', 'week']).agg({
        'yards_gained': 'mean'
    }).reset_index()
    def_ypp.columns = ['posteam', 'season', 'week', 'def_yards_per_play_allowed']
    
    # DEFENSIVE YPA ALLOWED
    def_pass_plays = def_plays[def_plays['pass'] == 1].copy()
    def_ypa = def_pass_plays.groupby(['defteam', 'season', 'week']).agg({
        'yards_gained': 'mean'
    }).reset_index()
    def_ypa.columns = ['posteam', 'season', 'week', 'def_yards_per_pass_allowed']
    
    # Merge all metrics
    result = off_ypp[['posteam', 'season', 'week', 'off_yards_per_play']].copy()
    result = result.merge(off_ypa[['posteam', 'season', 'week', 'off_yards_per_pass_attempt']], 
                          on=['posteam', 'season', 'week'], how='left')
    result = result.merge(def_ypp[['posteam', 'season', 'week', 'def_yards_per_play_allowed']], 
                          on=['posteam', 'season', 'week'], how='left')
    result = result.merge(def_ypa[['posteam', 'season', 'week', 'def_yards_per_pass_allowed']], 
                          on=['posteam', 'season', 'week'], how='left')
    
    # Fill missing values with season average for that team
    for col in ['off_yards_per_pass_attempt', 'def_yards_per_play_allowed', 'def_yards_per_pass_allowed']:
        season_avg = result.groupby(['posteam', 'season'])[col].transform('mean')
        result[col] = result[col].fillna(season_avg)
    
    print(f"   Team-weeks: {len(result):,}")
    print(f"   Avg Off YPP: {result['off_yards_per_play'].mean():.2f}")
    print(f"   Avg Off YPA: {result['off_yards_per_pass_attempt'].mean():.2f}")
    print(f"   Avg Def YPP Allowed: {result['def_yards_per_play_allowed'].mean():.2f}")
    print(f"   Avg Def YPA Allowed: {result['def_yards_per_pass_allowed'].mean():.2f}")
    
    return result


def calculate_season_averages(ypp_df):
    """Calculate season-long averages for teams."""
    print("\n📊 Calculating season averages...")
    
    season_avg = ypp_df.groupby(['posteam', 'season']).agg({
        'off_yards_per_play': 'mean',
        'off_yards_per_pass_attempt': 'mean',
        'def_yards_per_play_allowed': 'mean',
        'def_yards_per_pass_allowed': 'mean'
    }).reset_index()
    
    print(f"   Team-seasons: {len(season_avg):,}")
    
    return season_avg


def main():
    """Extract yards per play metrics from nflfastR data."""
    print("="*80)
    print("EXTRACT YARDS PER PLAY / YARDS PER PASS ATTEMPT")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Extract YPP/YPA
    ypp = extract_yards_per_play(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(ypp)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "team_yards_per_play_weekly.csv"
    ypp.to_csv(weekly_path, index=False)
    print(f"   Weekly YPP/YPA: {weekly_path}")
    
    season_path = DATA_DIR / "team_yards_per_play_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    print("\n" + "="*80)
    print("✅ YARDS PER PLAY METRICS EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

