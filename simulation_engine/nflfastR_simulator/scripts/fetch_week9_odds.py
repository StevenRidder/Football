"""
Fetch current market lines for Week 9 games from The Odds API.
"""
import requests
import os
import pandas as pd
from pathlib import Path

TEAM_MAPPING = {
    'Arizona Cardinals': 'ARI',
    'Atlanta Falcons': 'ATL',
    'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF',
    'Carolina Panthers': 'CAR',
    'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN',
    'Cleveland Browns': 'CLE',
    'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN',
    'Detroit Lions': 'DET',
    'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU',
    'Indianapolis Colts': 'IND',
    'Jacksonville Jaguars': 'JAX',
    'Kansas City Chiefs': 'KC',
    'Las Vegas Raiders': 'LV',
    'Los Angeles Chargers': 'LAC',
    'Los Angeles Rams': 'LAR',
    'Miami Dolphins': 'MIA',
    'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE',
    'New Orleans Saints': 'NO',
    'New York Giants': 'NYG',
    'New York Jets': 'NYJ',
    'Philadelphia Eagles': 'PHI',
    'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF',
    'Seattle Seahawks': 'SEA',
    'Tampa Bay Buccaneers': 'TB',
    'Tennessee Titans': 'TEN',
    'Washington Commanders': 'WAS',
}

def fetch_week9_odds():
    """Fetch current odds for upcoming games."""
    API_KEY = os.getenv('ODDS_API_KEY', '8349c09e3dae852bd7e9bc724819cdd0')
    
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'spreads,totals',
        'oddsFormat': 'american'
    }
    
    print("📥 Fetching current odds from Odds API...")
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:500])
            return None
        
        games = response.json()
        print(f"✅ Found {len(games)} games")
        
        # Parse into dict keyed by (away, home)
        odds_dict = {}
        
        for game in games:
            away_full = game['away_team']
            home_full = game['home_team']
            
            away = TEAM_MAPPING.get(away_full, away_full.split()[-1].upper()[:3])
            home = TEAM_MAPPING.get(home_full, home_full.split()[-1].upper()[:3])
            
            spread_line = None
            total_line = None
            
            # Get consensus from all books
            spreads = []
            totals = []
            
            for book in game.get('bookmakers', []):
                for market in book.get('markets', []):
                    if market['key'] == 'spreads':
                        # The Odds API gives each team's spread from their perspective
                        # Negative point = that team is favored (giving points)
                        # Positive point = that team is getting points (underdog)
                        # Our convention: spread_line = home_score - away_score
                        # Example: BAL @ MIA, BAL favored by 11.5
                        #   - BAL point = -11.5 (BAL giving 11.5)
                        #   - MIA point = +11.5 (MIA getting 11.5)
                        #   - spread_line = MIA_score - BAL_score = -11.5
                        
                        away_spread = None
                        home_spread = None
                        
                        for outcome in market['outcomes']:
                            if outcome['name'] == away_full or outcome['name'] == away:
                                away_spread = outcome['point']  # BAL: -11.5 means BAL favored
                            elif outcome['name'] == home_full or outcome['name'] == home:
                                home_spread = outcome['point']  # MIA: +11.5 means MIA getting points
                        
                        # Convert to our convention (home - away)
                        if away_spread is not None and home_spread is not None:
                            # The Odds API gives spreads from each team's perspective
                            # away_spread = away team's spread (negative = away favored)
                            # home_spread = home team's spread (positive = home getting points)
                            # Our convention: spread_line = home_score - away_score
                            # If BAL (away) is -11.5, that means BAL_score - MIA_score = 11.5
                            # So MIA_score - BAL_score = -11.5, which is our spread_line
                            # Therefore: spread_line = away_spread (negative = away favored)
                            spreads.append(away_spread)
                    
                    elif market['key'] == 'totals':
                        if market['outcomes']:
                            totals.append(market['outcomes'][0]['point'])
            
            # Use median for consensus
            if spreads:
                spread_line = sorted(spreads)[len(spreads)//2]
            if totals:
                total_line = sorted(totals)[len(totals)//2]
            
            if spread_line is not None and total_line is not None:
                odds_dict[(away, home)] = {
                    'spread_line': spread_line,
                    'total_line': total_line
                }
                print(f"  {away} @ {home}: {home} {spread_line:+.1f}, O/U {total_line:.1f}")
        
        return odds_dict
        
    except Exception as e:
        print(f"❌ Error fetching odds: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    odds = fetch_week9_odds()
    if odds:
        print(f"\n✅ Fetched odds for {len(odds)} games")
        # Save to file for use by generate_week9_predictions.py
        output_file = Path(__file__).parent.parent / "artifacts" / "week9_odds.json"
        import json
        # Convert tuple keys to strings for JSON
        odds_serializable = {f"{k[0]}_{k[1]}": v for k, v in odds.items()}
        with open(output_file, 'w') as f:
            json.dump(odds_serializable, f, indent=2)
        print(f"💾 Saved to: {output_file}")

