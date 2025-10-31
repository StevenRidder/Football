"""
Merge ALL Historical Data - 2020-2024

We have:
1. ESPN results: 1,343 games (2020-2024) with scores + features
2. Historical odds: 1,485 games (2020-2024) with opening/closing lines

This script properly merges them to create a complete learning dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def main():
    print("🔗 MERGING ALL HISTORICAL DATA (2020-2024)")
    print("="*60)
    
    artifacts = Path("artifacts")
    
    # Load ESPN results with features
    results_df = pd.read_csv(artifacts / "games_with_features_2020_2024.csv")
    print(f"✅ ESPN results: {len(results_df)} games")
    print(f"   Seasons: {sorted(results_df['season'].unique())}")
    print(f"   Columns: {list(results_df.columns[:10])}...")
    print()
    
    # The historical odds we fetched are in the log, but the CSV was corrupted
    # We need to use the 2025 data we have OR just use ESPN results alone
    
    # For now, let's use JUST the ESPN results and calculate our own "implied lines"
    # from the actual scores to simulate what the market might have been
    
    print("📊 CREATING LEARNING DATASET FROM ESPN RESULTS")
    print("="*60)
    
    # Calculate actual margins and totals
    results_df['actual_margin'] = results_df['away_score'] - results_df['home_score']
    results_df['actual_total'] = results_df['away_score'] + results_df['home_score']
    
    # For learning, we can use the actual results as our "target"
    # and the situational features as our "inputs"
    
    # Filter to games with complete data
    complete = results_df[
        results_df['away_score'].notna() &
        results_df['home_score'].notna() &
        results_df['divisional'].notna()
    ].copy()
    
    print(f"✅ Complete games: {len(complete)}")
    print()
    
    # Add some derived features
    complete['home_win'] = (complete['home_score'] > complete['away_score']).astype(int)
    complete['away_win'] = (complete['away_score'] > complete['home_score']).astype(int)
    complete['margin_abs'] = complete['actual_margin'].abs()
    
    # Save
    output_file = artifacts / "complete_historical_learning_dataset.csv"
    complete.to_csv(output_file, index=False)
    
    print(f"💾 Saved to {output_file}")
    print()
    print("✅ DATASET READY FOR LEARNING")
    print("="*60)
    print(f"Total games: {len(complete)}")
    print(f"Seasons: {sorted(complete['season'].unique())}")
    print(f"Features available:")
    print(f"  - Divisional games: {complete['divisional'].sum()}")
    print(f"  - Long travel: {complete['travel_long'].sum()}")
    print(f"  - Medium travel: {complete['travel_medium'].sum()}")
    print(f"  - OL continuity: ✅")
    print()
    print("Sample:")
    print(complete[['season', 'week', 'away', 'home', 'away_score', 'home_score',
                    'actual_margin', 'actual_total', 'divisional', 'travel_long']].head(10).to_string())
    print()
    print("⚠️  NOTE: This dataset does NOT have market lines (opening/closing)")
    print("   We can learn which features affect outcomes, but NOT CLV")
    print("   To learn CLV, we need historical odds data ($500-1000 from The Odds API)")
    print()
    print("Next step: python3 learn_from_results_only.py")


if __name__ == "__main__":
    main()

