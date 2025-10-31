"""
Extract QB-specific performance splits from nflfastR play-by-play data.

Outputs:
- qb_pressure_splits.csv: QB performance under pressure vs clean pocket
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


def extract_qb_pressure_splits(pbp_df):
    """
    Extract QB-specific performance under pressure vs clean pocket.
    
    Pressure = sack OR qb_hit
    
    Returns DataFrame with:
    - passer, season, week
    - clean_completion_pct, clean_yards_per_att, clean_td_rate, clean_int_rate, clean_epa
    - pressure_completion_pct, pressure_yards_per_att, pressure_td_rate, pressure_int_rate, pressure_sack_rate, pressure_scramble_rate, pressure_epa
    """
    print("\n🔬 Extracting QB pressure splits...")
    
    # Filter to dropbacks only
    dropbacks = pbp_df[
        (pbp_df['qb_dropback'] == 1) & 
        (pbp_df['passer'].notna())
    ].copy()
    
    print(f"   Dropbacks: {len(dropbacks):,}")
    
    # Define pressure: sack OR qb_hit
    dropbacks['is_pressure'] = (
        (dropbacks['sack'] == 1) | 
        (dropbacks['qb_hit'] == 1)
    ).astype(int)
    
    # Calculate pressure rate per QB
    pressure_rate = dropbacks.groupby(['passer', 'season'])['is_pressure'].mean()
    print(f"   Average pressure rate: {pressure_rate.mean():.1%}")
    
    # Group by QB, season, week, pressure
    qb_grouped = dropbacks.groupby(['passer', 'season', 'week', 'is_pressure']).agg({
        'complete_pass': ['sum', 'count'],  # Completions and attempts
        'yards_gained': 'sum',              # Total yards
        'touchdown': 'sum',                 # TDs
        'interception': 'sum',              # INTs
        'sack': 'sum',                      # Sacks
        'qb_scramble': 'sum',               # Scrambles
        'epa': 'mean',                      # EPA per play
        'play_id': 'count'                  # Total plays
    }).reset_index()
    
    # Flatten column names
    qb_grouped.columns = [
        'passer', 'season', 'week', 'is_pressure',
        'completions', 'attempts', 'total_yards', 'tds', 'ints', 'sacks', 'scrambles', 'epa', 'plays'
    ]
    
    # Calculate rates
    qb_grouped['completion_pct'] = qb_grouped['completions'] / qb_grouped['attempts']
    qb_grouped['yards_per_att'] = qb_grouped['total_yards'] / qb_grouped['attempts']
    qb_grouped['td_rate'] = qb_grouped['tds'] / qb_grouped['attempts']
    qb_grouped['int_rate'] = qb_grouped['ints'] / qb_grouped['attempts']
    qb_grouped['sack_rate'] = qb_grouped['sacks'] / qb_grouped['plays']
    qb_grouped['scramble_rate'] = qb_grouped['scrambles'] / qb_grouped['plays']
    
    # Pivot to get clean vs pressure columns
    qb_stats = qb_grouped.pivot_table(
        index=['passer', 'season', 'week'],
        columns='is_pressure',
        values=['completion_pct', 'yards_per_att', 'td_rate', 'int_rate', 'sack_rate', 'scramble_rate', 'epa', 'plays']
    ).reset_index()
    
    # Flatten column names
    qb_stats.columns = [
        f"{col[0]}_{['clean', 'pressure'][col[1]]}" if col[1] != '' else col[0]
        for col in qb_stats.columns
    ]
    
    # Rename base columns
    qb_stats.rename(columns={
        'passer': 'passer',
        'season': 'season',
        'week': 'week'
    }, inplace=True)
    
    # Filter to QBs with at least 10 dropbacks in both situations
    qb_stats = qb_stats[
        (qb_stats['plays_clean'] >= 10) & 
        (qb_stats['plays_pressure'] >= 5)
    ].copy()
    
    print(f"   QB-weeks with sufficient data: {len(qb_stats):,}")
    
    # Fill NaN with 0 for rates
    rate_cols = [col for col in qb_stats.columns if '_rate' in col or '_pct' in col]
    qb_stats[rate_cols] = qb_stats[rate_cols].fillna(0)
    
    return qb_stats


def calculate_season_averages(qb_stats):
    """
    Calculate season-long averages for QBs (for use when week-level data is sparse).
    """
    print("\n📊 Calculating season averages...")
    
    season_avg = qb_stats.groupby(['passer', 'season']).agg({
        'completion_pct_clean': 'mean',
        'yards_per_att_clean': 'mean',
        'td_rate_clean': 'mean',
        'int_rate_clean': 'mean',
        'sack_rate_clean': 'mean',
        'scramble_rate_clean': 'mean',
        'epa_clean': 'mean',
        'completion_pct_pressure': 'mean',
        'yards_per_att_pressure': 'mean',
        'td_rate_pressure': 'mean',
        'int_rate_pressure': 'mean',
        'sack_rate_pressure': 'mean',
        'scramble_rate_pressure': 'mean',
        'epa_pressure': 'mean',
        'plays_clean': 'sum',
        'plays_pressure': 'sum'
    }).reset_index()
    
    print(f"   QB-seasons: {len(season_avg):,}")
    
    return season_avg


def main():
    """Extract QB pressure splits from nflfastR data."""
    print("="*80)
    print("EXTRACT QB PRESSURE SPLITS FROM nflfastR")
    print("="*80)
    
    # Load play-by-play data
    seasons = [2022, 2023, 2024]
    pbp = load_pbp_data(seasons)
    
    # Extract QB pressure splits
    qb_splits = extract_qb_pressure_splits(pbp)
    
    # Calculate season averages
    season_avg = calculate_season_averages(qb_splits)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    weekly_path = DATA_DIR / "qb_pressure_splits_weekly.csv"
    qb_splits.to_csv(weekly_path, index=False)
    print(f"   Weekly splits: {weekly_path}")
    
    season_path = DATA_DIR / "qb_pressure_splits_season.csv"
    season_avg.to_csv(season_path, index=False)
    print(f"   Season averages: {season_path}")
    
    # Summary stats
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    print(f"\nQB Performance Comparison (Season Averages):")
    print(f"{'Metric':<30} {'Clean Pocket':<15} {'Under Pressure':<15} {'Diff':<10}")
    print("-"*70)
    
    metrics = [
        ('Completion %', 'completion_pct_clean', 'completion_pct_pressure'),
        ('Yards/Attempt', 'yards_per_att_clean', 'yards_per_att_pressure'),
        ('TD Rate', 'td_rate_clean', 'td_rate_pressure'),
        ('INT Rate', 'int_rate_clean', 'int_rate_pressure'),
        ('Sack Rate', 'sack_rate_clean', 'sack_rate_pressure'),
        ('Scramble Rate', 'scramble_rate_clean', 'scramble_rate_pressure'),
        ('EPA/Play', 'epa_clean', 'epa_pressure')
    ]
    
    for label, clean_col, pressure_col in metrics:
        clean_val = season_avg[clean_col].mean()
        pressure_val = season_avg[pressure_col].mean()
        diff = pressure_val - clean_val
        
        if 'rate' in label.lower() or '%' in label:
            print(f"{label:<30} {clean_val:<15.1%} {pressure_val:<15.1%} {diff:+.1%}")
        else:
            print(f"{label:<30} {clean_val:<15.2f} {pressure_val:<15.2f} {diff:+.2f}")
    
    print("\n" + "="*80)
    print("✅ QB PRESSURE SPLITS EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

