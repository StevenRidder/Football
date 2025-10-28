#!/usr/bin/env python3
"""
Backfill historical predictions for weeks 1-7 using the actual run_week function
"""
from pathlib import Path
from nfl_edge.main import run_week
import requests


def get_week_schedule(season: int, week: int):
    """Get schedule for a specific week from ESPN"""
    # ESPN to nflverse team abbreviation mapping
    espn_to_nflverse = {
        'WSH': 'WAS',  # Washington
        'LAR': 'LA',   # LA Rams
    }
    
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {'seasontype': 2, 'week': week, 'year': season}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            matchups = []
            
            for event in data.get('events', []):
                competition = event.get('competitions', [{}])[0]
                competitors = competition.get('competitors', [])
                
                if len(competitors) >= 2:
                    home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
                    away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
                    
                    home_abbr = home.get('team', {}).get('abbreviation')
                    away_abbr = away.get('team', {}).get('abbreviation')
                    
                    if home_abbr and away_abbr:
                        # Map ESPN abbreviations to nflverse abbreviations
                        home_abbr = espn_to_nflverse.get(home_abbr, home_abbr)
                        away_abbr = espn_to_nflverse.get(away_abbr, away_abbr)
                        matchups.append((away_abbr, home_abbr))
            
            return matchups
    except Exception as e:
        print(f"Error fetching schedule for week {week}: {e}")
        return []


def main():
    """Generate predictions for weeks 1-7"""
    Path("artifacts").mkdir(exist_ok=True)
    
    print("="*60)
    print("Backfilling predictions for weeks 1-7 of 2025")
    print("="*60)
    
    successful = []
    failed = []
    
    for week in range(1, 8):  # Generate all weeks
        print(f"\n{'='*60}")
        print(f"Week {week}")
        print(f"{'='*60}")
        
        try:
            # Get schedule for this week
            matchups = get_week_schedule(2025, week)
            
            if not matchups:
                failed.append((week, "No games found in schedule"))
                print(f"❌ Week {week}: No games found in schedule")
                continue
            
            print(f"Found {len(matchups)} games: {matchups}")
            
            # Use the actual run_week function
            # run_week returns a tuple of (proj_file, clv_file, dbg_file, bets_file)
            result = run_week(week_number=week, matchups=matchups)
            
            if result is not None:
                proj_file = result[0] if isinstance(result, tuple) else result
                # Read the generated file to count predictions
                import pandas as pd
                df = pd.read_csv(proj_file)
                successful.append(week)
                print(f"✅ Week {week}: Generated {len(df)} predictions → {proj_file}")
            else:
                failed.append((week, "No predictions generated"))
                print(f"❌ Week {week}: No predictions generated")
                
        except Exception as e:
            failed.append((week, str(e)))
            print(f"❌ Week {week}: Error - {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(successful)} weeks - {successful}")
    print(f"❌ Failed: {len(failed)} weeks")
    for week, error in failed:
        print(f"   Week {week}: {error}")
    
    if successful:
        print("\n📁 Files saved in artifacts/ directory")
        print("   Check: ls -lh artifacts/predictions_2025_week*.csv")


if __name__ == "__main__":
    main()

