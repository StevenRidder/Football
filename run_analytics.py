"""
Run Analytics Intensity Index (AII) analysis
Completely separate from game prediction model
"""

from pathlib import Path
from datetime import date
from nfl_edge.data_ingest import fetch_teamweeks_live
from nfl_edge.analytics_index import compute_aii

def run_analytics():
    print("=" * 80)
    print("ANALYTICS INTENSITY INDEX (AII) - 2025 SEASON")
    print("=" * 80)
    
    # Fetch current season data
    teamweeks = fetch_teamweeks_live()
    
    # Compute AII scores
    aii_df = compute_aii(teamweeks, season=2025)
    
    # Save results
    dt = date.today().isoformat()
    output_path = Path("artifacts") / f"aii_{dt}.csv"
    aii_df.to_csv(output_path, index=False)
    
    print("\n✅ AII analysis complete")
    print(f"📁 Saved to: {output_path}")
    
    # Display top 10
    print("\n" + "=" * 80)
    print("TOP 10 MOST ANALYTICAL TEAMS")
    print("=" * 80)
    
    print(f"\n{'Rank':<6} {'Team':<6} {'AII Score':<12} {'Proj Wins':<12} {'Tier':<6}")
    print("-" * 50)
    
    for i, row in aii_df.head(10).iterrows():
        print(f"{i+1:<6} {row['team']:<6} {row['aii_normalized']:<11.3f} {row['projected_wins']:<11.1f} {row['analytics_tier']:<6}")
    
    print("\n" + "=" * 80)
    print("BOTTOM 5 LEAST ANALYTICAL TEAMS")
    print("=" * 80)
    
    print(f"\n{'Rank':<6} {'Team':<6} {'AII Score':<12} {'Proj Wins':<12} {'Tier':<6}")
    print("-" * 50)
    
    for i, row in aii_df.tail(5).iterrows():
        print(f"{i+1:<6} {row['team']:<6} {row['aii_normalized']:<11.3f} {row['projected_wins']:<11.1f} {row['analytics_tier']:<6}")
    
    return aii_df

if __name__ == "__main__":
    run_analytics()

