"""
Extract Adjusted Net Yards per Attempt (ANY/A) from nflfastR play-by-play data.

Strategy: "ANY/A rolls up yards, TDs, INTs, sacks into one QB efficiency number"

Formula:
ANY/A = (pass_yards + 20*pass_tds - 45*ints - sack_yards) / (pass_attempts + sacks)

Outputs:
- team_anya.csv: ANY/A for offense and defense allowed
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


def calculate_anya(pbp_df):
    """
    Calculate Adjusted Net Yards per Attempt.
    
    Formula:
    ANY/A = (pass_yards + 20*pass_tds - 45*ints - sack_yards) / (pass_attempts + sacks)
    
    Returns DataFrame with:
    - posteam, season, week
    - off_anya (offensive ANY/A)
    - def_anya_allowed (defensive ANY/A allowed)
    """
    print("\n🔬 Calculating ANY/A...")
    
    # Filter to pass attempts (including sacks)
    pass_plays = pbp_df[
        ((pbp_df['pass_attempt'] == 1) | (pbp_df['sack'] == 1)) &
        (pbp_df['posteam'].notna())
    ].copy()
    
    print(f"   Pass plays: {len(pass_plays):,}")
    
    # OFFENSIVE ANY/A
    # Separate pass completions from sacks
    pass_completions = pass_plays[(pass_plays['pass_attempt'] == 1) & (pass_plays['sack'] != 1)].copy()
    sacks = pass_plays[pass_plays['sack'] == 1].copy()
    
    # Pass yards (completions only, no sacks)
    pass_yards = pass_completions.groupby(['posteam', 'season', 'week'])['yards_gained'].sum().reset_index()
    pass_yards.columns = ['posteam', 'season', 'week', 'pass_yards']
    
    # Pass TDs
    pass_tds = pass_completions.groupby(['posteam', 'season', 'week'])['touchdown'].sum().reset_index()
    pass_tds.columns = ['posteam', 'season', 'week', 'pass_tds']
    
    # INTs (on all pass attempts)
    ints = pass_plays.groupby(['posteam', 'season', 'week'])['interception'].sum().reset_index()
    ints.columns = ['posteam', 'season', 'week', 'interceptions']
    
    # Sack yards (negative)
    sack_yards = sacks.groupby(['posteam', 'season', 'week'])['yards_gained'].sum().reset_index()
    sack_yards.columns = ['posteam', 'season', 'week', 'sack_yards']
    
    # Pass attempts and sacks
    pass_attempts = pass_plays.groupby(['posteam', 'season', 'week']).agg({
        'pass_attempt': 'sum',
        'sack': 'sum'
    }).reset_index()
    
    # Merge all components
    off_anya = pass_yards.merge(pass_tds, on=['posteam', 'season', 'week'], how='outer')
    off_anya = off_anya.merge(ints, on=['posteam', 'season', 'week'], how='outer')
    off_anya = off_anya.merge(sack_yards, on=['posteam', 'season', 'week'], how='outer')
    off_anya = off_anya.merge(pass_attempts, on=['posteam', 'season', 'week'], how='outer')
    
    # Fill missing with 0
    for col in ['pass_yards', 'pass_tds', 'interceptions', 'sack_yards', 'pass_attempt', 'sack']:
        off_anya[col] = off_anya[col].fillna(0)
    
    # Calculate ANY/A
    off_anya['off_anya'] = (
        off_anya['pass_yards'] + 
        20 * off_anya['pass_tds'] - 
        45 * off_anya['interceptions'] - 
        abs(off_anya['sack_yards'])
    ) / (off_anya['pass_attempt'] + off_anya['sack'])
    
    # Replace inf/nan with 0
    off_anya['off_anya'] = off_anya['off_anya'].replace([np.inf, -np.inf], 0).fillna(0)
    off_anya = off_anya[['posteam', 'season', 'week', 'off_anya']].copy()
    
    # DEFENSIVE ANY/A ALLOWED
    def_plays = pbp_df[
        ((pbp_df['pass_attempt'] == 1) | (pbp_df['sack'] == 1)) &
        (pbp_df['defteam'].notna())
    ].copy()
    
    def_pass_completions = def_plays[(def_plays['pass_attempt'] == 1) & (def_plays['sack'] != 1)].copy()
    def_sacks = def_plays[def_plays['sack'] == 1].copy()
    
    def_pass_yards = def_pass_completions.groupby(['defteam', 'season', 'week'])['yards_gained'].sum().reset_index()
    def_pass_yards.columns = ['defteam', 'season', 'week', 'pass_yards']
    
    def_pass_tds = def_pass_completions.groupby(['defteam', 'season', 'week'])['touchdown'].sum().reset_index()
    def_pass_tds.columns = ['defteam', 'season', 'week', 'pass_tds']
    
    def_ints = def_plays.groupby(['defteam', 'season', 'week'])['interception'].sum().reset_index()
    def_ints.columns = ['defteam', 'season', 'week', 'interceptions']
    
    def_sack_yards = def_sacks.groupby(['defteam', 'season', 'week'])['yards_gained'].sum().reset_index()
    def_sack_yards.columns = ['defteam', 'season', 'week', 'sack_yards']
    
    def_pass_attempts = def_plays.groupby(['defteam', 'season', 'week']).agg({
        'pass_attempt': 'sum',
        'sack': 'sum'
    }).reset_index()
    
    def_anya = def_pass_yards.merge(def_pass_tds, on=['defteam', 'season', 'week'], how='outer')
    def_anya = def_anya.merge(def_ints, on=['defteam', 'season', 'week'], how='outer')
    def_anya = def_anya.merge(def_sack_yards, on=['defteam', 'season', 'week'], how='outer')
    def_anya = def_anya.merge(def_pass_attempts, on=['defteam', 'season', 'week'], how='outer')
    
    for col in ['pass_yards', 'pass_tds', 'interceptions', 'sack_yards', 'pass_attempt', 'sack']:
        def_anya[col] = def_anya[col].fillna(0)
    
    def_anya['def_anya_allowed'] = (
        def_anya['pass_yards'] + 
        20 * def_anya['pass_tds'] - 
        45 * def_anya['interceptions'] - 
        abs(def_anya['sack_yards'])
    ) / (def_anya['pass_attempt'] + def_anya['sack'])
    
    def_anya['def_anya_allowed'] = def_anya['def_anya_allowed'].replace([np.inf, -np.inf], 0).fillna(0)
    def_anya = def_anya.rename(columns={'defteam': 'posteam'})
    def_anya = def_anya[['posteam', 'season', 'week', 'def_anya_allowed']].copy()
    
    # Merge
    result = off_anya.merge(def_anya, on=['posteam', 'season', 'week'], how='outer')
    
    # Fill missing with season average
    for col in ['off_anya', 'def_anya_allowed']:
        season_avg = result.groupby(['posteam', 'season'])[col].transform('mean')
        result[col] = result[col].fillna(season_avg)
    
    print(f"   Team-weeks: {len(result):,}")
    print(f"   Avg Off ANY/A: {result['off_anya'].mean():.2f}")
    print(f"   Avg Def ANY/A Allowed: {result['def_anya_allowed'].mean():.2f}")
    
    return result


def calculate_season_averages(anya_df):
    """Calculate season-long averages."""
    print("\n📊 Calculating season averages...")
    
    season_avg = anya_df.groupby(['posteam', 'season']).agg({
        'off_anya': 'mean',
        'def_anya_allowed': 'mean'
    }).reset_index()
    
    print(f"   Team-seasons: {len(season_avg):,}")
    
    return season_avg


def main():
    """Extract ANY/A from nflfastR data."""
    print("="*80)
    print("EXTRACT ADJUSTED NET YARDS PER ATTEMPT (ANY/A)")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Calculate ANY/A
    anya = calculate_anya(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(anya)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "team_anya_weekly.csv"
    anya.to_csv(weekly_path, index=False)
    print(f"   Weekly ANY/A: {weekly_path}")
    
    season_path = DATA_DIR / "team_anya_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    print("\n" + "="*80)
    print("✅ ANY/A METRICS EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

