"""
Extract Special Teams statistics from nflfastR play-by-play data.

Strategy: "Special teams is one of the most overlooked phases but can 
          provide hidden yardage that decides games"

Outputs:
- special_teams.csv: Punt net yards, FG %, kick return averages
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


def extract_special_teams(pbp_df):
    """
    Extract special teams performance metrics.
    
    Returns DataFrame with:
    - posteam, season, week
    - punt_net_yards (punt distance - return yards)
    - field_goal_make_pct
    - kick_return_avg
    - punt_return_avg
    """
    print("\n🔬 Extracting special teams statistics...")
    
    # PUNTS
    punts = pbp_df[
        (pbp_df['punt_attempt'] == 1) &
        (pbp_df['posteam'].notna())
    ].copy()
    
    if len(punts) > 0:
        punt_stats = punts.groupby(['posteam', 'season', 'week']).agg({
            'kick_distance': 'mean',  # Punt distance
        }).reset_index()
        punt_stats.columns = ['posteam', 'season', 'week', 'punt_distance']
        
        # Punt returns (opponent returning our punts)
        punt_returns = pbp_df[
            (pbp_df['punt_attempt'] == 1) &
            (pbp_df['return_team'].notna())
        ].copy()
        
        if len(punt_returns) > 0 and 'return_yards' in punt_returns.columns:
            return_yards = punt_returns.groupby(['return_team', 'season', 'week'])['return_yards'].mean().reset_index()
            return_yards.columns = ['posteam', 'season', 'week', 'punt_return_yards_allowed']
            
            # Calculate net (punt distance - return yards)
            punt_stats = punt_stats.merge(return_yards, on=['posteam', 'season', 'week'], how='left')
            punt_stats['punt_return_yards_allowed'] = punt_stats['punt_return_yards_allowed'].fillna(0)
            punt_stats['punt_net_yards'] = punt_stats['punt_distance'] - punt_stats['punt_return_yards_allowed']
        else:
            punt_stats['punt_net_yards'] = punt_stats['punt_distance']
    else:
        punt_stats = pd.DataFrame(columns=['posteam', 'season', 'week', 'punt_net_yards'])
    
    # FIELD GOALS
    fgs = pbp_df[
        (pbp_df['field_goal_attempt'] == 1) &
        (pbp_df['posteam'].notna())
    ].copy()
    
    if len(fgs) > 0 and 'field_goal_result' in fgs.columns:
        fg_stats = fgs.groupby(['posteam', 'season', 'week']).agg({
            'field_goal_result': lambda x: (x == 'made').sum() / len(x) if len(x) > 0 else 0
        }).reset_index()
        fg_stats.columns = ['posteam', 'season', 'week', 'field_goal_make_pct']
    else:
        fg_stats = pd.DataFrame(columns=['posteam', 'season', 'week', 'field_goal_make_pct'])
    
    # KICK RETURNS
    kickoffs = pbp_df[
        (pbp_df['kickoff_attempt'] == 1) &
        (pbp_df['return_team'].notna())
    ].copy()
    
    if len(kickoffs) > 0 and 'return_yards' in kickoffs.columns:
        kick_return = kickoffs.groupby(['return_team', 'season', 'week'])['return_yards'].mean().reset_index()
        kick_return.columns = ['posteam', 'season', 'week', 'kick_return_avg']
    else:
        kick_return = pd.DataFrame(columns=['posteam', 'season', 'week', 'kick_return_avg'])
    
    # PUNT RETURNS
    punt_returns_off = pbp_df[
        (pbp_df['punt_attempt'] == 1) &
        (pbp_df['return_team'].notna()) &
        (pbp_df['return_yards'].notna())
    ].copy()
    
    if len(punt_returns_off) > 0:
        punt_return = punt_returns_off.groupby(['return_team', 'season', 'week'])['return_yards'].mean().reset_index()
        punt_return.columns = ['posteam', 'season', 'week', 'punt_return_avg']
    else:
        punt_return = pd.DataFrame(columns=['posteam', 'season', 'week', 'punt_return_avg'])
    
    # Merge all
    result = punt_stats[['posteam', 'season', 'week', 'punt_net_yards']].copy()
    
    if len(fg_stats) > 0:
        result = result.merge(fg_stats, on=['posteam', 'season', 'week'], how='outer')
    else:
        result['field_goal_make_pct'] = np.nan
    
    if len(kick_return) > 0:
        result = result.merge(kick_return, on=['posteam', 'season', 'week'], how='outer')
    else:
        result['kick_return_avg'] = np.nan
    
    if len(punt_return) > 0:
        result = result.merge(punt_return, on=['posteam', 'season', 'week'], how='outer')
    else:
        result['punt_return_avg'] = np.nan
    
    # Fill missing with season average
    for col in ['punt_net_yards', 'field_goal_make_pct', 'kick_return_avg', 'punt_return_avg']:
        season_avg = result.groupby(['posteam', 'season'])[col].transform('mean')
        result[col] = result[col].fillna(season_avg)
    
    print(f"   Team-weeks: {len(result):,}")
    if 'punt_net_yards' in result.columns:
        print(f"   Avg Punt Net Yards: {result['punt_net_yards'].mean():.1f}")
    if 'field_goal_make_pct' in result.columns:
        print(f"   Avg FG Make %: {result['field_goal_make_pct'].mean():.1%}")
    
    return result


def calculate_season_averages(st_df):
    """Calculate season-long averages."""
    print("\n📊 Calculating season averages...")
    
    cols = ['punt_net_yards', 'field_goal_make_pct', 'kick_return_avg', 'punt_return_avg']
    cols = [c for c in cols if c in st_df.columns]
    
    season_avg = st_df.groupby(['posteam', 'season'])[cols].mean().reset_index()
    
    print(f"   Team-seasons: {len(season_avg):,}")
    
    return season_avg


def main():
    """Extract special teams from nflfastR data."""
    print("="*80)
    print("EXTRACT SPECIAL TEAMS STATISTICS")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Extract special teams
    st = extract_special_teams(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(st)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "special_teams_weekly.csv"
    st.to_csv(weekly_path, index=False)
    print(f"   Weekly special teams: {weekly_path}")
    
    season_path = DATA_DIR / "special_teams_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    print("\n" + "="*80)
    print("✅ SPECIAL TEAMS STATISTICS EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

