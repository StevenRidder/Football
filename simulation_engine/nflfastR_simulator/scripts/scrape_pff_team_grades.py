#!/usr/bin/env python3
"""
Scrape PFF Team Grades from Premium API
Extracts OL/DL grades and other position-level team data
"""

import requests
import pandas as pd
import json
from pathlib import Path
import time

# You'll need to get your session cookie from the browser
# After logging in to PFF, open DevTools > Application > Cookies
# Copy the value of the cookie (usually named something like 'pff_session' or '_pff_session')
SESSION_COOKIE = input("Paste your PFF session cookie here: ").strip()

def fetch_pff_team_overview(season: int, weeks: str = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,28,29,30,32"):
    """
    Fetch team overview data from PFF API
    
    Args:
        season: NFL season year (e.g., 2024)
        weeks: Comma-separated week numbers (28,29,30,32 are playoffs)
    
    Returns:
        dict: JSON response from PFF API
    """
    url = f"https://premium.pff.com/api/v1/teams/overview"
    
    params = {
        'league': 'nfl',
        'season': season,
        'week': weeks
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Cookie': f'_pff_session={SESSION_COOKIE}'
    }
    
    print(f"Fetching {season} data...")
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Successfully fetched {season} data")
        return response.json()
    else:
        print(f"❌ Failed to fetch {season} data: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None

def parse_team_grades(data):
    """
    Parse the PFF API response into a clean DataFrame
    
    Returns:
        pd.DataFrame with columns:
        - team: Team abbreviation
        - season: Season year
        - week: Week number (or 'REGPO' for full season)
        - off_grade: Overall offensive grade
        - pass_grade: Passing grade
        - pass_block_grade: Pass blocking grade (OL)
        - recv_grade: Receiving grade
        - run_grade: Running grade
        - run_block_grade: Run blocking grade (OL)
        - def_grade: Overall defensive grade
        - run_def_grade: Run defense grade
        - tackle_grade: Tackling grade
        - pass_rush_grade: Pass rush grade (DL)
        - coverage_grade: Coverage grade
        - special_grade: Special teams grade
    """
    if not data or 'teams' not in data:
        return pd.DataFrame()
    
    rows = []
    for team in data['teams']:
        row = {
            'team': team.get('franchise_id'),
            'season': data.get('season'),
            'week': data.get('week', 'REGPO'),
            'record': team.get('record'),
            'points_for': team.get('points_for'),
            'points_against': team.get('points_against'),
            'overall_grade': team.get('grades', {}).get('overall'),
            'off_grade': team.get('grades', {}).get('offense'),
            'pass_grade': team.get('grades', {}).get('pass'),
            'pass_block_grade': team.get('grades', {}).get('pass_block'),  # KEY: OL pass blocking
            'recv_grade': team.get('grades', {}).get('receiving'),
            'run_grade': team.get('grades', {}).get('run'),
            'run_block_grade': team.get('grades', {}).get('run_block'),  # OL run blocking
            'def_grade': team.get('grades', {}).get('defense'),
            'run_def_grade': team.get('grades', {}).get('run_defense'),
            'tackle_grade': team.get('grades', {}).get('tackle'),
            'pass_rush_grade': team.get('grades', {}).get('pass_rush'),  # KEY: DL pass rush
            'coverage_grade': team.get('grades', {}).get('coverage'),
            'special_grade': team.get('grades', {}).get('special_teams'),
        }
        rows.append(row)
    
    return pd.DataFrame(rows)

def main():
    """
    Scrape PFF team grades for multiple seasons
    """
    output_dir = Path(__file__).parent.parent / "data" / "pff"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch data for 2022-2024 seasons
    seasons = [2022, 2023, 2024]
    all_data = []
    
    for season in seasons:
        data = fetch_pff_team_overview(season)
        if data:
            # Save raw JSON
            json_file = output_dir / f"pff_team_overview_{season}.json"
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"   Saved raw JSON to {json_file}")
            
            # Parse and save CSV
            df = parse_team_grades(data)
            if not df.empty:
                csv_file = output_dir / f"pff_team_grades_{season}.csv"
                df.to_csv(csv_file, index=False)
                print(f"   Saved CSV to {csv_file}")
                print(f"   {len(df)} teams extracted\n")
                all_data.append(df)
            
            # Be nice to the API
            time.sleep(2)
    
    # Combine all seasons
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined_file = output_dir / "pff_team_grades_2022_2024.csv"
        combined.to_csv(combined_file, index=False)
        print(f"\n✅ Combined file saved to {combined_file}")
        print(f"   Total rows: {len(combined)}")
        
        # Show sample
        print("\n📊 Sample data:")
        print(combined.head(10).to_string())
        
        # Show key columns
        print("\n🔑 Key columns for OL/DL analysis:")
        key_cols = ['team', 'season', 'pass_block_grade', 'pass_rush_grade']
        print(combined[key_cols].head(10).to_string())
    
    print("\n✅ Done! You can now use this data in your simulator.")

if __name__ == "__main__":
    main()

