"""
Fetch current market lines from The Odds API and merge into predictions.

This ensures we're using REAL market lines, not model predictions.
"""

import pandas as pd
import requests
import os
from datetime import datetime
from pathlib import Path

# Odds API configuration
API_KEY = os.getenv('ODDS_API_KEY', 'YOUR_KEY_HERE')  # Set this!
SPORT = 'americanfootball_nfl'
REGIONS = 'us'
MARKETS = 'spreads,totals'
ODDS_FORMAT = 'american'

# Team name mapping (Odds API → Our abbreviations)
TEAM_MAPPING = {
    'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
    'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
    'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
    'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
    'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'
}


def fetch_current_lines():
    """Fetch current lines from Odds API."""
    url = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds/'
    
    params = {
        'apiKey': API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
        'oddsFormat': ODDS_FORMAT
    }
    
    print(f"📥 Fetching current lines from Odds API...")
    response = requests.get(url, params=params, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    print(f"✅ Found {len(data)} games")
    
    # Parse into DataFrame
    games = []
    for game in data:
        away_team = TEAM_MAPPING.get(game['away_team'], game['away_team'])
        home_team = TEAM_MAPPING.get(game['home_team'], game['home_team'])
        
        # Get first bookmaker with both spreads and totals
        spread_home = None
        total = None
        
        for book in game.get('bookmakers', []):
            markets = book.get('markets', [])
            
            # Find spread
            spread_market = next((m for m in markets if m['key'] == 'spreads'), None)
            if spread_market:
                for outcome in spread_market['outcomes']:
                    if outcome['name'] == home_team or outcome['name'] == game['home_team']:
                        spread_home = outcome['point']
            
            # Find total
            total_market = next((m for m in markets if m['key'] == 'totals'), None)
            if total_market and total_market['outcomes']:
                total = total_market['outcomes'][0]['point']
            
            # If we have both, we're done
            if spread_home is not None and total is not None:
                break
        
        if spread_home is not None and total is not None:
            games.append({
                'away': away_team,
                'home': home_team,
                'market_spread': spread_home,
                'market_total': total,
                'commence_time': game['commence_time']
            })
    
    return pd.DataFrame(games)


def merge_market_lines_into_predictions(predictions_file):
    """Merge market lines into predictions CSV."""
    # Load predictions
    df_pred = pd.read_csv(predictions_file)
    print(f"\n📊 Loaded {len(df_pred)} games from predictions")
    
    # Fetch current market lines
    df_market = fetch_current_lines()
    
    if df_market is None or len(df_market) == 0:
        print("❌ No market lines fetched")
        return False
    
    # Merge on away/home
    df_merged = df_pred.merge(
        df_market[['away', 'home', 'market_spread', 'market_total']],
        on=['away', 'home'],
        how='left'
    )
    
    # Update the "Spread used" and "Total used" columns with market data
    df_merged['Spread used (home-)'] = df_merged['market_spread'].fillna(df_merged['Spread used (home-)'])
    df_merged['Total used'] = df_merged['market_total'].fillna(df_merged['Total used'])
    
    # Count how many got real market data
    market_count = df_merged['market_spread'].notna().sum()
    print(f"✅ Updated {market_count}/{len(df_pred)} games with real market lines")
    
    # Save back
    df_merged.to_csv(predictions_file, index=False)
    print(f"💾 Saved updated predictions to {predictions_file}")
    
    return True


if __name__ == "__main__":
    # Find latest predictions file
    artifacts = Path("artifacts")
    csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
    
    # Get the most recent file that doesn't have 'week' in the name
    current_week_files = [f for f in csvs if '_week' not in f.name]
    if current_week_files:
        latest = current_week_files[-1]
    else:
        latest = csvs[-1]
    
    print(f"📁 Using predictions file: {latest.name}")
    
    success = merge_market_lines_into_predictions(latest)
    
    if success:
        print("\n✅ Market lines updated successfully!")
        print("   Run: python3 precompute_edge_hunt_signals.py")
        print("   Then restart Flask")
    else:
        print("\n❌ Failed to update market lines")
        print("   Check your ODDS_API_KEY environment variable")

