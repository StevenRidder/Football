"""
Extract Turnover Regression factors from nflfastR play-by-play data.

Strategy: "Turnovers are notoriously random... teams with +3 turnover game 
          may be overvalued. Fade teams with unsustainable turnover luck."

Outputs:
- turnover_regression.csv: Recent vs rolling turnover margins
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


def extract_turnover_margins(pbp_df):
    """
    Calculate turnover margins and regression factors.
    
    Returns DataFrame with:
    - posteam, season, week
    - turnovers_forced (INTs + fumbles recovered)
    - turnovers_lost (INTs thrown + fumbles lost)
    - turnover_margin
    - recent_margin (last 2 games)
    - rolling_margin (8-game window)
    - regression_factor (fade if recent >> rolling)
    """
    print("\n🔬 Extracting turnover margins...")
    
    # Get all plays with turnovers
    plays = pbp_df[
        (pbp_df['posteam'].notna()) &
        (pbp_df['defteam'].notna())
    ].copy()
    
    # OFFENSIVE TURNOVERS LOST
    off_turnovers = plays.groupby(['posteam', 'season', 'week']).agg({
        'interception': lambda x: (x == 1).sum(),  # INTs thrown
        'fumble_lost': lambda x: (x == 1).sum() if 'fumble_lost' in plays.columns else 0
    }).reset_index()
    
    # Check if fumble_lost column exists, otherwise use fumble + fumble_recovery logic
    if 'fumble_lost' not in plays.columns:
        # Use fumble and fumble_recovery to determine lost
        plays['is_fumble_lost'] = (plays['fumble'] == 1) & (plays['fumble_recovery_1_team'] != plays['posteam'])
        off_turnovers['fumbles_lost'] = plays.groupby(['posteam', 'season', 'week'])['is_fumble_lost'].sum().reset_index()['is_fumble_lost']
    else:
        off_turnovers['fumbles_lost'] = off_turnovers['fumble_lost']
    
    off_turnovers['turnovers_lost'] = off_turnovers['interception'] + off_turnovers['fumbles_lost']
    off_turnovers = off_turnovers[['posteam', 'season', 'week', 'turnovers_lost']].copy()
    
    # DEFENSIVE TURNOVERS FORCED
    def_turnovers = plays.groupby(['defteam', 'season', 'week']).agg({
        'interception': lambda x: (x == 1).sum(),  # INTs forced
    }).reset_index()
    
    if 'fumble_lost' not in plays.columns:
        def_plays = plays.copy()
        def_plays['is_fumble_recovered'] = (def_plays['fumble'] == 1) & (def_plays['fumble_recovery_1_team'] == def_plays['defteam'])
        def_turnovers['fumbles_recovered'] = def_plays.groupby(['defteam', 'season', 'week'])['is_fumble_recovered'].sum().reset_index()['is_fumble_recovered']
    else:
        def_turnovers['fumbles_recovered'] = plays.groupby(['defteam', 'season', 'week'])['fumble_lost'].sum().reset_index()['fumble_lost']
    
    def_turnovers['turnovers_forced'] = def_turnovers['interception'] + def_turnovers['fumbles_recovered']
    def_turnovers = def_turnovers.rename(columns={'defteam': 'posteam'})
    def_turnovers = def_turnovers[['posteam', 'season', 'week', 'turnovers_forced']].copy()
    
    # Merge and calculate margin
    turnovers = off_turnovers.merge(def_turnovers, on=['posteam', 'season', 'week'], how='outer')
    turnovers['turnover_margin'] = turnovers['turnovers_forced'] - turnovers['turnovers_lost']
    
    # Fill missing with 0
    turnovers = turnovers.fillna(0)
    
    # Sort by team, season, week
    turnovers = turnovers.sort_values(['posteam', 'season', 'week']).reset_index(drop=True)
    
    # Calculate recent margin (last 2 games) and rolling margin (8-game window)
    turnovers['recent_margin'] = np.nan
    turnovers['rolling_margin'] = np.nan
    turnovers['regression_factor'] = 1.0
    
    for team in turnovers['posteam'].unique():
        team_data = turnovers[turnovers['posteam'] == team].copy()
        
        for i in range(len(team_data)):
            if i >= 1:
                # Recent margin (last 2 games)
                recent = team_data.iloc[max(0, i-1):i+1]['turnover_margin'].mean()
                turnovers.loc[team_data.index[i], 'recent_margin'] = recent
            
            if i >= 7:
                # Rolling margin (8-game window)
                rolling = team_data.iloc[i-7:i+1]['turnover_margin'].mean()
                turnovers.loc[team_data.index[i], 'rolling_margin'] = rolling
                
                # Regression factor: if recent >> rolling, fade (reduce efficiency)
                # If recent << rolling, boost (regression opportunity)
                recent = turnovers.loc[team_data.index[i], 'recent_margin']
                if not pd.isna(rolling) and not pd.isna(recent):
                    diff = recent - rolling
                    # Cap regression factor between 0.95 and 1.05 (5% adjustment max)
                    regression_factor = 1.0 - (diff * 0.02)  # Each +1 margin diff = -2% efficiency
                    regression_factor = np.clip(regression_factor, 0.95, 1.05)
                    turnovers.loc[team_data.index[i], 'regression_factor'] = regression_factor
    
    # Fill missing rolling/recent with overall average
    turnovers['recent_margin'] = turnovers['recent_margin'].fillna(turnovers['turnover_margin'])
    turnovers['rolling_margin'] = turnovers['rolling_margin'].fillna(turnovers['turnover_margin'])
    
    print(f"   Team-weeks: {len(turnovers):,}")
    print(f"   Avg Turnover Margin: {turnovers['turnover_margin'].mean():.2f}")
    print(f"   Teams with regression factor < 1.0 (should fade): {(turnovers['regression_factor'] < 1.0).sum()}")
    print(f"   Teams with regression factor > 1.0 (regression opportunity): {(turnovers['regression_factor'] > 1.0).sum()}")
    
    return turnovers[['posteam', 'season', 'week', 'turnovers_forced', 'turnovers_lost', 
                      'turnover_margin', 'recent_margin', 'rolling_margin', 'regression_factor']].copy()


def calculate_season_averages(turnovers_df):
    """Calculate season-long averages."""
    print("\n📊 Calculating season averages...")
    
    season_avg = turnovers_df.groupby(['posteam', 'season']).agg({
        'turnovers_forced': 'mean',
        'turnovers_lost': 'mean',
        'turnover_margin': 'mean'
    }).reset_index()
    
    print(f"   Team-seasons: {len(season_avg):,}")
    
    return season_avg


def main():
    """Extract turnover regression from nflfastR data."""
    print("="*80)
    print("EXTRACT TURNOVER REGRESSION")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Extract turnover margins
    turnovers = extract_turnover_margins(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(turnovers)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "turnover_regression_weekly.csv"
    turnovers.to_csv(weekly_path, index=False)
    print(f"   Weekly turnover margins: {weekly_path}")
    
    season_path = DATA_DIR / "turnover_regression_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    print("\n" + "="*80)
    print("✅ TURNOVER REGRESSION EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

