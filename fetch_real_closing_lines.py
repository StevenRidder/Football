"""
Fetch Real Closing Lines for Completed Games

This script fetches closing lines from The Odds API for all completed games
in Weeks 1-7, using the actual game kickoff times.
"""

import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ODDS_API_KEY = os.getenv('ODDS_API_KEY', '8349c09e3dae852bd7e9bc724819cdd0')
ARTIFACTS_DIR = Path('/Users/steveridder/Git/Football/artifacts')

# Team mapping (ESPN to canonical)
TEAM_MAPPING = {
    'ARI': 'ARI', 'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF', 'CAR': 'CAR', 'CHI': 'CHI',
    'CIN': 'CIN', 'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN', 'DET': 'DET', 'GB': 'GB',
    'HOU': 'HOU', 'IND': 'IND', 'JAX': 'JAX', 'KC': 'KC', 'LAC': 'LAC', 'LAR': 'LAR',
    'LV': 'LV', 'MIA': 'MIA', 'MIN': 'MIN', 'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG',
    'NYJ': 'NYJ', 'PHI': 'PHI', 'PIT': 'PIT', 'SF': 'SF', 'SEA': 'SEA', 'TB': 'TB',
    'TEN': 'TEN', 'WAS': 'WAS', 'WSH': 'WAS'
}

# Odds API team name mapping
ODDS_API_TEAMS = {
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
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS"
}


def get_completed_games():
    """Fetch all completed games from ESPN for Weeks 1-7."""
    print("\n📥 Fetching completed games from ESPN...")
    
    all_games = []
    
    for week in range(1, 8):
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=2025&seasontype=2&week={week}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            for event in data.get('events', []):
                if event['status']['type']['completed']:
                    comps = event['competitions'][0]
                    away_team = comps['competitors'][1]
                    home_team = comps['competitors'][0]
                    
                    # Get kickoff time
                    kickoff = event.get('date')
                    
                    away_abbr = TEAM_MAPPING.get(away_team['team']['abbreviation'], away_team['team']['abbreviation'])
                    home_abbr = TEAM_MAPPING.get(home_team['team']['abbreviation'], home_team['team']['abbreviation'])
                    
                    all_games.append({
                        'week': week,
                        'away': away_abbr,
                        'home': home_abbr,
                        'kickoff': kickoff,
                        'away_score': int(away_team['score']),
                        'home_score': int(home_team['score'])
                    })
        except Exception as e:
            print(f"⚠️  Week {week}: {e}")
    
    df = pd.DataFrame(all_games)
    df['kickoff'] = pd.to_datetime(df['kickoff'])
    
    print(f"✅ Found {len(df)} completed games")
    return df


def fetch_closing_lines_for_game(week, away, home, kickoff_time):
    """
    Fetch closing lines for a specific game from Odds API.
    
    Uses the kickoff time minus 1 hour as the closing line snapshot.
    """
    # Calculate closing time (1 hour before kickoff)
    closing_time = kickoff_time - timedelta(hours=1)
    closing_time_str = closing_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/odds"
    
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals',
        'oddsFormat': 'american',
        'date': closing_time_str,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 401:
            print(f"❌ API key error (401) - check your Odds API key")
            return None
        
        if response.status_code != 200:
            print(f"⚠️  API error {response.status_code} for {away}@{home}")
            return None
        
        data = response.json()
        events = data.get('data', [])
        
        # Find the matching game
        for event in events:
            event_away = ODDS_API_TEAMS.get(event.get('away_team', ''))
            event_home = ODDS_API_TEAMS.get(event.get('home_team', ''))
            
            if event_away == away and event_home == home:
                # Extract lines from first bookmaker with both markets
                bookmakers = event.get('bookmakers', [])
                
                for book in bookmakers:
                    spread_point = None
                    spread_price_home = None
                    spread_price_away = None
                    total_point = None
                    total_price_over = None
                    total_price_under = None
                    
                    for market in book.get('markets', []):
                        if market['key'] == 'spreads':
                            for outcome in market['outcomes']:
                                if outcome['name'] == event['home_team']:
                                    spread_point = outcome['point']
                                    spread_price_home = outcome['price']
                                elif outcome['name'] == event['away_team']:
                                    spread_price_away = outcome['price']
                        
                        elif market['key'] == 'totals':
                            for outcome in market['outcomes']:
                                if outcome['name'] == 'Over':
                                    total_point = outcome['point']
                                    total_price_over = outcome['price']
                                elif outcome['name'] == 'Under':
                                    total_price_under = outcome['price']
                    
                    # If this book has both markets, use it
                    if spread_point is not None and total_point is not None:
                        return {
                            'week': week,
                            'away': away,
                            'home': home,
                            'closing_spread': spread_point,
                            'closing_total': total_point,
                            'spread_price_home': spread_price_home,
                            'spread_price_away': spread_price_away,
                            'total_price_over': total_price_over,
                            'total_price_under': total_price_under,
                            'book_id': book.get('key', 'unknown'),
                            'closing_time': closing_time_str
                        }
        
        print(f"⚠️  No matching game found for {away}@{home} in API response")
        return None
        
    except Exception as e:
        print(f"❌ Error fetching {away}@{home}: {e}")
        return None


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("FETCHING REAL CLOSING LINES FOR COMPLETED GAMES")
    print("="*80)
    
    # Get completed games
    games_df = get_completed_games()
    
    # Fetch closing lines for each game
    print(f"\n📡 Fetching closing lines from Odds API...")
    print(f"   (This will take ~{len(games_df) * 2} seconds due to rate limits)")
    
    closing_lines = []
    
    for idx, row in games_df.iterrows():
        print(f"\n[{idx+1}/{len(games_df)}] Week {row['week']}: {row['away']} @ {row['home']}")
        print(f"   Kickoff: {row['kickoff']}")
        
        closing = fetch_closing_lines_for_game(
            row['week'],
            row['away'],
            row['home'],
            row['kickoff']
        )
        
        if closing:
            closing_lines.append(closing)
            print(f"   ✅ Spread: {closing['closing_spread']}, Total: {closing['closing_total']}")
        else:
            print(f"   ❌ No closing line found")
        
        # Rate limit: 2 requests per second
        time.sleep(0.5)
    
    # Save results
    if closing_lines:
        closing_df = pd.DataFrame(closing_lines)
        output_file = ARTIFACTS_DIR / f"real_closing_lines_weeks_1-7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        closing_df.to_csv(output_file, index=False)
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"\nTotal games: {len(games_df)}")
        print(f"Closing lines found: {len(closing_lines)}")
        print(f"Success rate: {len(closing_lines)/len(games_df)*100:.1f}%")
        print(f"\n📊 Saved to: {output_file}")
        
        # Show sample
        print("\nSample closing lines:")
        print(closing_df[['week', 'away', 'home', 'closing_spread', 'closing_total']].head(10))
    else:
        print("\n❌ No closing lines found!")
    
    print("\n✅ Done!")


if __name__ == '__main__':
    main()

