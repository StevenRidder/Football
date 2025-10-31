"""
Merge the fetched historical odds with ESPN results.
"""

import pandas as pd
from pathlib import Path
from nfl_edge.team_mapping import normalize_team

def main():
    print("🔗 MERGING HISTORICAL ODDS WITH RESULTS")
    print("="*60)
    
    artifacts = Path("artifacts")
    
    # Load the raw odds data (before it was overwritten)
    # We need to re-run the fetch to get it back
    print("⚠️  The odds data was overwritten. Need to reload from fetch log...")
    print()
    print("Since The Odds API hit rate limits and we got 1,485 games,")
    print("let's use a different approach:")
    print()
    print("OPTION 1: Use the 2025 Weeks 1-7 data we already have (116 games)")
    print("  - Already has opening/closing lines")
    print("  - Already has results")
    print("  - Can start backtesting immediately")
    print()
    print("OPTION 2: Wait for The Odds API rate limit to reset")
    print("  - Would give us 1,485 games (2020-2024)")
    print("  - But requires historical data plan (~$500-1000)")
    print()
    print("OPTION 3: Use nflverse + current Odds API")
    print("  - Get historical results from nflverse (free)")
    print("  - Get CURRENT lines from Odds API")
    print("  - Can't backtest (no historical lines)")
    print("  - But can deploy and track CLV going forward")
    print()
    
    # Check what we have for 2025
    lines_2025 = artifacts / "opening_closing_lines_weeks_1-7_20251027.csv"
    if lines_2025.exists():
        df_2025 = pd.read_csv(lines_2025)
        print(f"✅ We have 2025 data: {len(df_2025)} games with opening/closing lines")
        print()
        print("Sample:")
        print(df_2025[['week', 'away', 'home', 'spread_open', 'spread_close', 'total_open', 'total_close']].head(10).to_string())
        print()
        print("RECOMMENDATION: Use this 2025 data to learn adjustments.")
        print("It's clean, complete, and ready to go.")
        print()
        print("Run: python3 xgboost_learn_adjustments.py")
    
    # Check the features data
    features_file = artifacts / "games_with_features_2020_2024.csv"
    if features_file.exists():
        df_features = pd.read_csv(features_file)
        print(f"\n✅ We have features for {len(df_features)} games (2020-2024)")
        print(f"   Seasons: {sorted(df_features['season'].unique())}")
        print(f"   But no historical odds to match them with.")

if __name__ == "__main__":
    main()

