"""
Phase 1 - Step 2: Calculate Matchup Metrics

For each game in 2022-2024, calculate:
- pressure_edge_away: away_DL_grade - home_OL_grade
- pressure_edge_home: home_DL_grade - away_OL_grade
- net_pressure_advantage: Overall matchup edge

This is the KEY difference from our Ridge model:
- Ridge uses team averages as features
- Phase 1 calculates matchup-specific edges for THIS game

Using REAL PFF data scraped from premium.pff.com
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PFF_RAW_DIR = SCRIPT_DIR / "pff_raw"
OUTPUT_DIR = SCRIPT_DIR.parent / "data"


def load_pff_team_grades():
    """Load real PFF team grades from scraped data."""
    print("📊 Loading PFF team grades...")
    
    dfs = []
    for year in [2022, 2023, 2024]:
        df = pd.read_csv(PFF_RAW_DIR / f"team_grades_{year}.csv")
        df['season'] = year
        dfs.append(df)
    
    all_grades = pd.concat(dfs, ignore_index=True)
    
    print(f"   Total team-seasons: {len(all_grades)}")
    print(f"   Years: 2022-2024")
    print(f"   Teams per year: {len(all_grades) // 3}")
    
    return all_grades


def load_schedules():
    """Load NFL schedules with results for 2022-2024."""
    print("\n📅 Loading schedules...")
    
    schedule = nfl.import_schedules([2022, 2023, 2024])
    reg_season = schedule[schedule['game_type'] == 'REG'].copy()
    
    print(f"   Total games: {len(reg_season)}")
    print(f"   Completed: {reg_season['away_score'].notna().sum()}")
    
    return reg_season


def calculate_matchup_metrics(schedule, pff_grades):
    """Calculate matchup-specific metrics for each game using real PFF team grades."""
    print("\n🔬 Calculating matchup metrics...")
    
    results = []
    
    for _, game in schedule.iterrows():
        game_id = game['game_id']
        season = game['season']
        week = game['week']
        away_team = game['away_team']
        home_team = game['home_team']
        
        # Get PFF grades for this season
        away_grades = pff_grades[(pff_grades['abbreviation'] == away_team) & (pff_grades['season'] == season)]
        home_grades = pff_grades[(pff_grades['abbreviation'] == home_team) & (pff_grades['season'] == season)]
        
        # Skip if data missing
        if len(away_grades) == 0 or len(home_grades) == 0:
            continue
        
        away_ol_grade = away_grades.iloc[0]['pass_block_grade']
        home_ol_grade = home_grades.iloc[0]['pass_block_grade']
        away_dl_grade = away_grades.iloc[0]['pass_rush_grade']
        home_dl_grade = home_grades.iloc[0]['pass_rush_grade']
        
        # Calculate pressure edges (KEY METRIC)
        # Positive = defense has advantage
        pressure_edge_away = away_dl_grade - home_ol_grade  # Away DL vs Home OL
        pressure_edge_home = home_dl_grade - away_ol_grade  # Home DL vs Away OL
        
        # Net pressure advantage (positive = home has advantage)
        net_pressure_advantage = pressure_edge_home - pressure_edge_away
        
        # Get actual game results
        away_score = game.get('away_score')
        home_score = game.get('home_score')
        spread_line = game.get('spread_line')  # Negative = home favored
        total_line = game.get('total_line')
        
        # Calculate actual outcomes (if game completed)
        actual_spread = None
        point_differential = None
        spread_result = None
        total_result = None
        
        if pd.notna(away_score) and pd.notna(home_score):
            actual_spread = home_score - away_score
            point_differential = actual_spread  # Same thing
            
            if pd.notna(spread_line):
                # Did home team cover?
                home_covered = actual_spread > spread_line
                spread_result = "HOME_COVER" if home_covered else "AWAY_COVER"
            
            if pd.notna(total_line):
                actual_total = away_score + home_score
                total_result = "OVER" if actual_total > total_line else "UNDER"
        
        results.append({
            'game_id': game_id,
            'season': season,
            'week': week,
            'gameday': game.get('gameday'),
            'away_team': away_team,
            'home_team': home_team,
            
            # OL/DL Grades
            'away_ol_grade': away_ol_grade,
            'home_ol_grade': home_ol_grade,
            'away_dl_grade': away_dl_grade,
            'home_dl_grade': home_dl_grade,
            
            # Pressure Edges (KEY METRICS)
            'pressure_edge_away': pressure_edge_away,  # Away DL vs Home OL
            'pressure_edge_home': pressure_edge_home,  # Home DL vs Away OL
            'net_pressure_advantage': net_pressure_advantage,  # Positive = home advantage
            
            # Market Lines
            'spread_line': spread_line,
            'total_line': total_line,
            
            # Actual Results
            'away_score': away_score,
            'home_score': home_score,
            'actual_spread': actual_spread,
            'point_differential': point_differential,
            'spread_result': spread_result,
            'total_result': total_result,
        })
    
    df = pd.DataFrame(results)
    print(f"   Calculated metrics for {len(df)} games")
    
    return df


def analyze_pressure_edges(df):
    """Quick analysis of pressure edges."""
    print("\n📈 Pressure Edge Analysis:")
    
    completed = df[df['away_score'].notna()].copy()
    
    if len(completed) == 0:
        print("   No completed games yet")
        return
    
    # Calculate absolute pressure edges
    completed['abs_pressure_edge_away'] = completed['pressure_edge_away'].abs()
    completed['abs_pressure_edge_home'] = completed['pressure_edge_home'].abs()
    completed['max_pressure_edge'] = completed[['abs_pressure_edge_away', 'abs_pressure_edge_home']].max(axis=1)
    
    print(f"\n   Completed games: {len(completed)}")
    print(f"   Average pressure edge (away): {completed['pressure_edge_away'].mean():.2f}")
    print(f"   Average pressure edge (home): {completed['pressure_edge_home'].mean():.2f}")
    print(f"   Max pressure edge seen: {completed['max_pressure_edge'].max():.2f}")
    
    # Games with big mismatches
    big_mismatch = completed[completed['max_pressure_edge'] > 10]
    print(f"\n   Games with pressure edge > 10: {len(big_mismatch)}")
    
    if len(big_mismatch) > 0:
        print(f"   Average spread in those games: {big_mismatch['actual_spread'].mean():.2f}")


def main():
    """Main execution."""
    print("="*80)
    print("PHASE 1 - STEP 2: CALCULATE MATCHUP METRICS")
    print("Using REAL PFF data from premium.pff.com")
    print("="*80)
    
    # Load data
    pff_grades = load_pff_team_grades()
    schedule = load_schedules()
    
    # Calculate matchup metrics
    matchup_df = calculate_matchup_metrics(schedule, pff_grades)
    
    # Quick analysis
    analyze_pressure_edges(matchup_df)
    
    # Save results
    output_path = OUTPUT_DIR / "matchup_metrics_2022_2024.csv"
    matchup_df.to_csv(output_path, index=False)
    
    print("\n" + "="*80)
    print("✅ MATCHUP METRICS CALCULATED")
    print("="*80)
    print(f"📁 Saved to: {output_path}")
    print(f"📊 Total games: {len(matchup_df)}")
    print(f"📊 Completed games: {matchup_df['away_score'].notna().sum()}")
    
    print("\n🔑 Key Metrics Calculated:")
    print("   - pressure_edge_away: Away DL vs Home OL")
    print("   - pressure_edge_home: Home DL vs Away OL")
    print("   - net_pressure_advantage: Overall pressure advantage")
    
    print("\n🚀 Next: Run correlation tests to see if these metrics predict outcomes!")


if __name__ == "__main__":
    main()

