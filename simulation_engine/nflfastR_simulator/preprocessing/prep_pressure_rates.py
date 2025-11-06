"""
Prep Pressure Rates: Compute weekly team pressure baselines from nflfastR.

This script:
1. Loads play-by-play data from nflfastR
2. Computes off_pr_allowed and def_pr_created per team-week
3. Applies rolling EMA to get current form
4. Outputs CSV for pressure calibration

Usage:
    python3 preprocessing/prep_pressure_rates.py --season 2025 --week 9
    python3 preprocessing/prep_pressure_rates.py --season 2025 --week 9 --output data/nflfastR/pressure_rates_weekly.csv
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import nfl_data_py as nfl
except ImportError:
    print("❌ nfl-data-py not installed. Install with: pip install nfl-data-py")
    sys.exit(1)


def compute_weekly_pressure_rates(season: int, week: int) -> pd.DataFrame:
    """
    Compute weekly pressure rates from nflfastR play-by-play data.
    
    Returns DataFrame with columns:
        team, season, week, off_pr_allowed, def_pr_created
    """
    print(f"📥 Loading nflfastR play-by-play data for {season}...")
    
    # Load play-by-play data
    pbp = nfl.import_pbp_data([season], downcast=True)
    
    # Filter to requested week(s)
    if week:
        pbp = pbp[pbp['week'] <= week].copy()
        print(f"   Filtered to weeks 1-{week}")
    
    print(f"   Loaded {len(pbp):,} plays")
    
    # Filter to dropbacks only
    dropbacks = pbp[
        (pbp['qb_dropback'] == 1) | 
        (pbp['pass'] == 1)
    ].copy()
    
    print(f"   Found {len(dropbacks):,} dropbacks")
    
    # Define pressure: sack OR qb_hit
    # Note: nflfastR has qb_hit, but pressure is more comprehensive
    # We'll use sack + qb_hit as proxy (can enhance with hurry data if available)
    dropbacks['is_pressure'] = (
        (dropbacks['sack'] == 1) | 
        (dropbacks['qb_hit'] == 1)
    ).astype(int)
    
    # Offensive pressure allowed (when team is on offense)
    off_pressure = dropbacks.groupby(['posteam', 'season', 'week']).agg({
        'is_pressure': ['sum', 'count'],
        'sack': 'sum',
        'qb_hit': 'sum'
    }).reset_index()
    
    off_pressure.columns = ['team', 'season', 'week', 'pressures_allowed', 'dropbacks', 'sacks', 'qb_hits']
    
    # Calculate pressure rate
    off_pressure['off_pr_allowed'] = off_pressure['pressures_allowed'] / off_pressure['dropbacks']
    off_pressure['off_pr_allowed'] = off_pressure['off_pr_allowed'].fillna(0.0)
    
    # Defensive pressure created (when team is on defense)
    # We need to map posteam to defteam
    def_pressure = dropbacks.groupby(['defteam', 'season', 'week']).agg({
        'is_pressure': ['sum', 'count'],
        'sack': 'sum',
        'qb_hit': 'sum'
    }).reset_index()
    
    def_pressure.columns = ['team', 'season', 'week', 'pressures_created', 'opp_dropbacks', 'sacks', 'qb_hits']
    
    # Calculate pressure rate
    def_pressure['def_pr_created'] = def_pressure['pressures_created'] / def_pressure['opp_dropbacks']
    def_pressure['def_pr_created'] = def_pressure['def_pr_created'].fillna(0.0)
    
    # Merge offensive and defensive stats
    result = off_pressure[['team', 'season', 'week', 'off_pr_allowed', 'dropbacks', 'pressures_allowed']].merge(
        def_pressure[['team', 'season', 'week', 'def_pr_created', 'opp_dropbacks', 'pressures_created']],
        on=['team', 'season', 'week'],
        how='outer'
    )
    
    # Fill missing values
    result['off_pr_allowed'] = result['off_pr_allowed'].fillna(0.0)
    result['def_pr_created'] = result['def_pr_created'].fillna(0.0)
    result['dropbacks'] = result['dropbacks'].fillna(0)
    result['opp_dropbacks'] = result['opp_dropbacks'].fillna(0)
    result['pressures_allowed'] = result['pressures_allowed'].fillna(0)
    result['pressures_created'] = result['pressures_created'].fillna(0)
    
    # Sort by season, week, team
    result = result.sort_values(['season', 'week', 'team']).reset_index(drop=True)
    
    print(f"\n✅ Computed pressure rates for {len(result)} team-weeks")
    print(f"   Average off_pr_allowed: {result['off_pr_allowed'].mean():.3f}")
    print(f"   Average def_pr_created: {result['def_pr_created'].mean():.3f}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Compute weekly pressure rates from nflfastR")
    parser.add_argument('--season', type=int, required=True, help='Season (e.g., 2025)')
    parser.add_argument('--week', type=int, default=None, help='Week number (default: all weeks)')
    parser.add_argument('--output', type=str, default=None, 
                       help='Output CSV path (default: data/nflfastR/pressure_rates_weekly.csv)')
    
    args = parser.parse_args()
    
    # Compute pressure rates
    df = compute_weekly_pressure_rates(args.season, args.week)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).parent.parent / "data" / "nflfastR" / "pressure_rates_weekly.csv"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"\n💾 Saved to: {output_path}")
    
    # Show sample
    print("\n📊 Sample data:")
    print(df.head(10).to_string(index=False))
    
    # Show team summary for latest week
    if args.week:
        latest = df[df['week'] == args.week].copy()
        if len(latest) > 0:
            print(f"\n📈 Teams in week {args.week}:")
            latest_sorted = latest.sort_values('off_pr_allowed', ascending=False)
            print(latest_sorted[['team', 'off_pr_allowed', 'def_pr_created', 'dropbacks']].to_string(index=False))


if __name__ == "__main__":
    main()

