"""
Extract Situational Factors from nflfastR schedule data.

Strategy: "Factors like travel, rest, weather, coaching aggression can tip games"

Outputs:
- situational_factors.csv: Rest days, weather, dome status
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "nflfastR"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_schedule_data(seasons):
    """Load schedule data for given seasons."""
    print(f"📊 Loading schedule data for {seasons}...")
    schedule = nfl.import_schedules(seasons)
    print(f"   Loaded {len(schedule)} games")
    return schedule


def extract_situational_factors(schedule_df):
    """
    Extract situational factors from schedule.
    
    Returns DataFrame with:
    - game_id, season, week, home_team, away_team
    - home_rest_days, away_rest_days
    - roof (dome/outdoors)
    - temp, wind
    - surface (grass/turf)
    """
    print("\n🔬 Extracting situational factors...")
    
    # Select relevant columns
    cols = ['game_id', 'season', 'week', 'home_team', 'away_team', 
            'home_rest', 'away_rest', 'roof', 'surface', 'temp', 'wind']
    
    available_cols = [c for c in cols if c in schedule_df.columns]
    result = schedule_df[available_cols].copy()
    
    # Rename rest columns
    if 'home_rest' in result.columns:
        result = result.rename(columns={'home_rest': 'home_rest_days'})
    if 'away_rest' in result.columns:
        result = result.rename(columns={'away_rest': 'away_rest_days'})
    
    # Ensure rest days are numeric
    if 'home_rest_days' in result.columns:
        result['home_rest_days'] = pd.to_numeric(result['home_rest_days'], errors='coerce').fillna(7)
    if 'away_rest_days' in result.columns:
        result['away_rest_days'] = pd.to_numeric(result['away_rest_days'], errors='coerce').fillna(7)
    
    # Convert temp and wind to numeric
    if 'temp' in result.columns:
        result['temp'] = pd.to_numeric(result['temp'], errors='coerce')
    if 'wind' in result.columns:
        result['wind'] = pd.to_numeric(result['wind'], errors='coerce')
    
    # Identify dome games
    if 'roof' in result.columns:
        result['is_dome'] = result['roof'].str.contains('dome', case=False, na=False)
    else:
        result['is_dome'] = False
    
    print(f"   Games: {len(result):,}")
    if 'home_rest_days' in result.columns:
        print(f"   Avg Home Rest: {result['home_rest_days'].mean():.1f} days")
        print(f"   Avg Away Rest: {result['away_rest_days'].mean():.1f} days")
    if 'is_dome' in result.columns:
        print(f"   Dome Games: {result['is_dome'].sum()}")
    
    return result


def main():
    """Extract situational factors from nflfastR schedule."""
    print("="*80)
    print("EXTRACT SITUATIONAL FACTORS")
    print("="*80)
    
    # Load schedule data
    seasons = [2022, 2023, 2024, 2025]
    schedule = load_schedule_data(seasons)
    
    # Extract situational factors
    factors = extract_situational_factors(schedule)
    
    # Save to CSV
    print("\n💾 Saving data...")
    
    output_path = DATA_DIR / "situational_factors.csv"
    factors.to_csv(output_path, index=False)
    print(f"   Situational factors: {output_path}")
    
    print("\n" + "="*80)
    print("✅ SITUATIONAL FACTORS EXTRACTED")
    print("="*80)


if __name__ == "__main__":
    main()

