"""
Extract Early-Down Success Rate from nflfastR play-by-play data.

Strategy: "Early-down passing success rate is particularly powerful because it 
          filters out the noise of desperate third-down plays"

Outputs:
- early_down_success_rate.csv: Success rates on 1st and 2nd downs
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


def is_successful_play(yards_gained, ydstogo, down):
    """
    Determine if a play was successful.
    
    1st down: Success = gaining 40% of needed yards
    2nd down: Success = gaining 50% of needed yards
    """
    if pd.isna(ydstogo) or ydstogo == 0:
        return False
    
    if down == 1:
        return yards_gained >= (0.4 * ydstogo)
    elif down == 2:
        return yards_gained >= (0.5 * ydstogo)
    else:
        return False


def extract_early_down_success(pbp_df):
    """
    Extract early-down success rates.
    
    Returns DataFrame with:
    - posteam, season, week
    - first_down_success_rate
    - second_down_success_rate
    - early_down_success_rate (combined)
    """
    print("\n🔬 Extracting early-down success rates...")
    
    # Filter to 1st and 2nd downs only
    early_downs = pbp_df[
        (pbp_df['down'].isin([1, 2])) &
        (pbp_df['play_type'].isin(['pass', 'run'])) &
        (pbp_df['posteam'].notna()) &
        (pbp_df['yards_gained'].notna()) &
        (pbp_df['ydstogo'].notna())
    ].copy()
    
    print(f"   Early-down plays: {len(early_downs):,}")
    
    # Determine success
    early_downs['success'] = early_downs.apply(
        lambda row: is_successful_play(row['yards_gained'], row['ydstogo'], row['down']),
        axis=1
    )
    
    # Group by team, season, week, down
    success_by_down = early_downs.groupby(['posteam', 'season', 'week', 'down']).agg({
        'success': ['sum', 'count']
    }).reset_index()
    
    success_by_down.columns = ['posteam', 'season', 'week', 'down', 'successful_plays', 'total_plays']
    success_by_down['success_rate'] = success_by_down['successful_plays'] / success_by_down['total_plays']
    
    # Pivot to get 1st and 2nd down separately
    success_pivot = success_by_down.pivot_table(
        index=['posteam', 'season', 'week'],
        columns='down',
        values='success_rate',
        aggfunc='mean'
    ).reset_index()
    
    success_pivot.columns = ['posteam', 'season', 'week', 'first_down_success_rate', 'second_down_success_rate']
    
    # Calculate combined early-down success
    early_downs_all = early_downs.groupby(['posteam', 'season', 'week']).agg({
        'success': ['sum', 'count']
    }).reset_index()
    early_downs_all.columns = ['posteam', 'season', 'week', 'successful_plays', 'total_plays']
    early_downs_all['early_down_success_rate'] = early_downs_all['successful_plays'] / early_downs_all['total_plays']
    
    # Merge
    result = success_pivot.merge(
        early_downs_all[['posteam', 'season', 'week', 'early_down_success_rate']],
        on=['posteam', 'season', 'week'],
        how='left'
    )
    
    # Fill missing with season average
    for col in ['first_down_success_rate', 'second_down_success_rate', 'early_down_success_rate']:
        season_avg = result.groupby(['posteam', 'season'])[col].transform('mean')
        result[col] = result[col].fillna(season_avg)
    
    print(f"   Team-weeks: {len(result):,}")
    print(f"   Avg 1st Down Success: {result['first_down_success_rate'].mean():.1%}")
    print(f"   Avg 2nd Down Success: {result['second_down_success_rate'].mean():.1%}")
    print(f"   Avg Early-Down Success: {result['early_down_success_rate'].mean():.1%}")
    
    return result


def calculate_season_averages(success_df):
    """Calculate season-long averages."""
    print("\n📊 Calculating season averages...")
    
    season_avg = success_df.groupby(['posteam', 'season']).agg({
        'first_down_success_rate': 'mean',
        'second_down_success_rate': 'mean',
        'early_down_success_rate': 'mean'
    }).reset_index()
    
    print(f"   Team-seasons: {len(season_avg):,}")
    
    return season_avg


def main():
    """Extract early-down success rates from nflfastR data."""
    print("="*80)
    print("EXTRACT EARLY-DOWN SUCCESS RATES")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024, 2025]
    pbp = load_pbp_data(seasons)
    
    # Extract success rates
    success = extract_early_down_success(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(success)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "early_down_success_weekly.csv"
    success.to_csv(weekly_path, index=False)
    print(f"   Weekly success rates: {weekly_path}")
    
    season_path = DATA_DIR / "early_down_success_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    print("\n" + "="*80)
    print("✅ EARLY-DOWN SUCCESS RATES EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

