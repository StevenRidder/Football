#!/usr/bin/env python3
"""
Fetch historical odds from The Odds API for Weeks 1-7
This will allow proper backtesting of the residual model
"""
import sys
sys.path.insert(0, '/Users/steveridder/Git/Football')

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY = os.getenv('ODDS_API_KEY')
if not ODDS_API_KEY:
    print("❌ ODDS_API_KEY not set in .env file")
    sys.exit(1)

# Week start dates for 2025 NFL season
WEEK_DATES = {
    1: "2025-09-04",
    2: "2025-09-11",
    3: "2025-09-18",
    4: "2025-09-25",
    5: "2025-10-02",
    6: "2025-10-09",
    7: "2025-10-16",
    8: "2025-10-23",
}

# Team name mapping (Odds API to nflverse abbreviations)
TEAM_MAPPING = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
    "Washington Football Team": "WAS",
}

def fetch_historical_odds_for_date(date_str: str) -> dict:
    """
    Fetch historical odds for a specific date using paid tier historical endpoint
    
    Endpoint: /v4/historical/sports/{sport}/odds
    Docs: https://the-odds-api.com/liveapi/guides/v4/#get-historical-odds
    """
    url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/odds"
    
    # The API expects ISO 8601 format with time: YYYY-MM-DDTHH:MM:SSZ
    # Use noon UTC on the week start date
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals',
        'oddsFormat': 'decimal',  # Try decimal first, easier to parse
        'date': date_str + 'T18:00:00Z',  # 6 PM UTC = ~1 PM ET (typical game time)
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 401:
            print(f"  ❌ 401 Unauthorized - API key may be invalid or out of credits")
            return None
        elif response.status_code == 404:
            print(f"  ⚠️  404 Not Found - No odds data for {date_str}")
            return None
        elif response.status_code != 200:
            print(f"  ❌ Error {response.status_code}: {response.text[:200]}")
            return None
        
        data = response.json()
        
        # Check remaining requests
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        used = response.headers.get('x-requests-used', 'unknown')
        print(f"  API calls: {used} used, {remaining} remaining")
        
        # Debug: Show what we got
        if isinstance(data, list):
            print(f"  Received {len(data)} events")
        elif isinstance(data, dict):
            events = data.get('data', [])
            print(f"  Received {len(events)} events")
        
        return data
        
    except Exception as e:
        print(f"  ❌ Error fetching odds for {date_str}: {e}")
        return None

def parse_odds_data(data: dict, week: int) -> pd.DataFrame:
    """Parse Odds API response into a clean DataFrame"""
    if not data:
        return pd.DataFrame()
    
    # Handle both list and dict responses
    events = data if isinstance(data, list) else data.get('data', [])
    
    if not events:
        return pd.DataFrame()
    
    rows = []
    
    for i, event in enumerate(events):
        # Debug first event
        if i == 0:
            print(f"    DEBUG first event keys: {list(event.keys())[:10]}")
            print(f"    DEBUG home_team: {event.get('home_team', 'N/A')}")
            print(f"    DEBUG away_team: {event.get('away_team', 'N/A')}")
        
        home_team = TEAM_MAPPING.get(event.get('home_team', ''), event.get('home_team', 'UNKNOWN'))
        away_team = TEAM_MAPPING.get(event.get('away_team', ''), event.get('away_team', 'UNKNOWN'))
        
        # Get consensus lines (average across books)
        spread_lines = []
        total_lines = []
        
        bookmakers = event.get('bookmakers', [])
        
        # Debug first event's bookmakers
        if i == 0:
            print(f"    DEBUG bookmakers count: {len(bookmakers)}")
            if bookmakers:
                print(f"    DEBUG first bookmaker keys: {list(bookmakers[0].keys())}")
                markets = bookmakers[0].get('markets', [])
                print(f"    DEBUG markets count: {len(markets)}")
                if markets:
                    print(f"    DEBUG first market: {markets[0].get('key', 'N/A')}")
        
        for bookmaker in bookmakers:
            for market in bookmaker.get('markets', []):
                if market['key'] == 'spreads':
                    for outcome in market['outcomes']:
                        # Match by team name (full name from API)
                        if outcome['name'] == event['home_team']:
                            spread_lines.append(outcome['point'])
                
                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over':
                            total_lines.append(outcome['point'])
        
        if spread_lines and total_lines:
            avg_spread = sum(spread_lines) / len(spread_lines)
            avg_total = sum(total_lines) / len(total_lines)
            
            rows.append({
                'week': week,
                'away': away_team,
                'home': home_team,
                'spread': avg_spread,  # Home spread
                'total': avg_total,
                'commence_time': event.get('commence_time'),
            })
    
    return pd.DataFrame(rows)

def main():
    print("=" * 80)
    print("FETCHING HISTORICAL ODDS FOR WEEKS 1-7")
    print("=" * 80)
    print()
    
    all_odds = []
    
    for week in range(1, 8):
        print(f"\nWeek {week} ({WEEK_DATES[week]}):")
        
        # Try the week start date
        date_str = WEEK_DATES[week]
        data = fetch_historical_odds_for_date(date_str)
        
        if data:
            df = parse_odds_data(data, week)
            if not df.empty:
                print(f"  ✅ Found {len(df)} games")
                all_odds.append(df)
            else:
                print(f"  ⚠️  No games parsed")
        
        # Rate limit: wait between requests
        time.sleep(1)
    
    if not all_odds:
        print("\n❌ No historical odds data retrieved")
        print("\nPossible reasons:")
        print("  1. API key doesn't have access to historical data")
        print("  2. Historical endpoint requires paid tier")
        print("  3. 2025 season data not yet available in historical API")
        print("\nAlternative: Use current odds as proxy for historical")
        return
    
    # Combine all weeks
    combined_df = pd.concat(all_odds, ignore_index=True)
    
    # Save to CSV
    output_dir = Path('/Users/steveridder/Git/Football/artifacts')
    output_file = output_dir / f'historical_odds_weeks_1-7_{datetime.now().strftime("%Y%m%d")}.csv'
    combined_df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal games: {len(combined_df)}")
    print(f"Weeks covered: {combined_df['week'].nunique()}")
    print(f"Saved to: {output_file}")
    print()
    print(combined_df.head(10))

if __name__ == '__main__':
    main()

