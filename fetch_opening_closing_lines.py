#!/usr/bin/env python3
"""
Fetch opening and closing lines for each game
This is critical for calculating true CLV (Closing Line Value)

Strategy:
- Opening lines: Monday/Tuesday before game week
- Closing lines: 1 hour before kickoff (or as close as possible)
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

# Team name mapping
TEAM_MAPPING = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS", "Washington Football Team": "WAS",
}

def fetch_lines_at_timestamp(date_str: str, hour_offset: int = 0, target_timestamp: str = None) -> dict:
    """
    Fetch odds at a specific timestamp
    
    Args:
        date_str: Week start date (YYYY-MM-DD)
        hour_offset: Hours to add (0 = Monday 6PM UTC, 96 = Friday 6PM UTC for closing)
    """
    url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/odds"
    
    # Use target_timestamp if provided, otherwise calculate from offset
    if target_timestamp:
        date_param = target_timestamp
    else:
        base_date = datetime.strptime(date_str, "%Y-%m-%d")
        target_date = base_date + timedelta(hours=18 + hour_offset)  # 6 PM UTC + offset
        date_param = target_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals',
        'oddsFormat': 'american',  # American odds for accurate pricing
        'date': date_param,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"    ❌ Error {response.status_code}")
            return None
        
        data = response.json()
        
        # Check remaining requests
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        print(f"    API calls remaining: {remaining}")
        
        return data
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None

def parse_lines(data: dict, week: int, line_type: str) -> pd.DataFrame:
    """
    Parse odds data into DataFrame with line_type (opening/closing)
    
    Now captures:
    - book_id for consistency
    - prices (American odds) for accurate grading
    - spread/total points
    """
    if not data:
        return pd.DataFrame()
    
    events = data if isinstance(data, list) else data.get('data', [])
    if not events:
        return pd.DataFrame()
    
    rows = []
    
    for event in events:
        home_team = TEAM_MAPPING.get(event.get('home_team', ''), event.get('home_team', 'UNKNOWN'))
        away_team = TEAM_MAPPING.get(event.get('away_team', ''), event.get('away_team', 'UNKNOWN'))
        
        bookmakers = event.get('bookmakers', [])
        
        # Find a book that has BOTH spreads AND totals (same book for both markets)
        if not bookmakers:
            continue
        
        book_id = None
        spread_point = None
        spread_price_home = None
        spread_price_away = None
        total_point = None
        total_price_over = None
        total_price_under = None
        
        # Iterate through books to find one with both markets
        for book in bookmakers:
            temp_spread_point = None
            temp_spread_price_home = None
            temp_spread_price_away = None
            temp_total_point = None
            temp_total_price_over = None
            temp_total_price_under = None
            
            for market in book.get('markets', []):
                if market['key'] == 'spreads':
                    for outcome in market['outcomes']:
                        if outcome['name'] == event['home_team']:
                            temp_spread_point = outcome['point']
                            temp_spread_price_home = outcome['price']
                        elif outcome['name'] == event['away_team']:
                            temp_spread_price_away = outcome['price']
                
                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over':
                            temp_total_point = outcome['point']
                            temp_total_price_over = outcome['price']
                        elif outcome['name'] == 'Under':
                            temp_total_price_under = outcome['price']
            
            # If this book has both markets, use it
            if temp_spread_point is not None and temp_total_point is not None:
                book_id = book.get('key', 'unknown')
                spread_point = temp_spread_point
                spread_price_home = temp_spread_price_home
                spread_price_away = temp_spread_price_away
                total_point = temp_total_point
                total_price_over = temp_total_price_over
                total_price_under = temp_total_price_under
                break  # Use first book with both markets
        
        if spread_point is not None and total_point is not None and book_id:
            rows.append({
                'week': week,
                'away': away_team,
                'home': home_team,
                'book_id': book_id,
                'spread': spread_point,
                'spread_price_home': spread_price_home,
                'spread_price_away': spread_price_away,
                'total': total_point,
                'total_price_over': total_price_over,
                'total_price_under': total_price_under,
                'line_type': line_type,
                'timestamp': event.get('commence_time'),
            })
    
    return pd.DataFrame(rows)

def main():
    print("=" * 80)
    print("FETCHING OPENING AND CLOSING LINES")
    print("=" * 80)
    print()
    
    all_lines = []
    
    for week in range(1, 8):
        print(f"\nWeek {week}:")
        
        # Opening lines (Monday 6PM UTC = week start)
        print(f"  Fetching opening lines...")
        opening_data = fetch_lines_at_timestamp(WEEK_DATES[week], hour_offset=0)
        if opening_data:
            opening_df = parse_lines(opening_data, week, 'opening')
            if not opening_df.empty:
                print(f"    ✅ {len(opening_df)} games")
                all_lines.append(opening_df)
        
        time.sleep(1)
        
        # Closing lines - try multiple times to get closer to kickoff
        # Most games are Sunday, so try Saturday evening and Sunday morning
        print(f"  Fetching closing lines (Saturday evening)...")
        closing_data_sat = fetch_lines_at_timestamp(WEEK_DATES[week], hour_offset=120)  # Saturday 6PM
        if closing_data_sat:
            closing_df_sat = parse_lines(closing_data_sat, week, 'closing')
            if not closing_df_sat.empty:
                print(f"    ✅ {len(closing_df_sat)} games")
                all_lines.append(closing_df_sat)
        
        time.sleep(1)
        
        print(f"  Fetching closing lines (Sunday morning)...")
        closing_data_sun = fetch_lines_at_timestamp(WEEK_DATES[week], hour_offset=144)  # Sunday 6AM
        if closing_data_sun:
            closing_df_sun = parse_lines(closing_data_sun, week, 'closing')
            if not closing_df_sun.empty:
                print(f"    ✅ {len(closing_df_sun)} games")
                all_lines.append(closing_df_sun)
        
        time.sleep(1)
    
    if not all_lines:
        print("\n❌ No line data retrieved")
        return
    
    # Combine and save
    combined_df = pd.concat(all_lines, ignore_index=True)
    
    output_dir = Path('/Users/steveridder/Git/Football/artifacts')
    output_file = output_dir / f'opening_closing_lines_weeks_1-7_{datetime.now().strftime("%Y%m%d")}.csv'
    combined_df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal snapshots: {len(combined_df)}")
    print(f"Opening lines: {len(combined_df[combined_df['line_type'] == 'opening'])}")
    print(f"Closing lines: {len(combined_df[combined_df['line_type'] == 'closing'])}")
    print(f"\nSaved to: {output_file}")
    print()
    
    # Show line movement example
    print("Example line movements:")
    for week in [1, 2]:
        week_data = combined_df[combined_df['week'] == week]
        if len(week_data) >= 2:
            game = week_data.iloc[0]
            print(f"\nWeek {week}: {game['away']} @ {game['home']}")
            opening = week_data[(week_data['away'] == game['away']) & 
                               (week_data['home'] == game['home']) & 
                               (week_data['line_type'] == 'opening')]
            closing = week_data[(week_data['away'] == game['away']) & 
                               (week_data['home'] == game['home']) & 
                               (week_data['line_type'] == 'closing')]
            if not opening.empty and not closing.empty:
                print(f"  Opening: Spread {opening.iloc[0]['spread']:+.1f}, Total {opening.iloc[0]['total']:.1f}")
                print(f"  Closing: Spread {closing.iloc[0]['spread']:+.1f}, Total {closing.iloc[0]['total']:.1f}")
                print(f"  Movement: Spread {closing.iloc[0]['spread'] - opening.iloc[0]['spread']:+.1f}, "
                      f"Total {closing.iloc[0]['total'] - opening.iloc[0]['total']:+.1f}")

if __name__ == '__main__':
    main()

