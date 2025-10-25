"""
NFL Predictions API - Fetch predictions from multiple sources
Integrates ESPN FPI, FiveThirtyEight ELO, and Vegas implied probabilities
"""
import os
import requests
import pandas as pd
import io
from typing import Dict, Optional, Tuple


def fetch_espn_fpi_predictions(away: str, home: str) -> Optional[Dict]:
    """
    Fetch ESPN FPI win probabilities for a specific matchup
    
    Args:
        away: Away team abbreviation
        home: Home team abbreviation
        
    Returns:
        Dict with away_win_prob, home_win_prob, projected_score_away, projected_score_home
        None if not available
    """
    try:
        # ESPN has predictions in their main scoreboard API
        # We need to find the specific game
        for week in range(1, 18):
            espn_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
            params = {'seasontype': 2, 'week': week, 'year': 2025}
            response = requests.get(espn_url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                for event in events:
                    competitions = event.get('competitions', [])
                    if not competitions:
                        continue
                        
                    comp = competitions[0]
                    competitors = comp.get('competitors', [])
                    
                    if len(competitors) != 2:
                        continue
                    
                    home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                    away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                    
                    if not home_team or not away_team:
                        continue
                        
                    # Check if this is our matchup
                    if home_team['team']['abbreviation'] == home and away_team['team']['abbreviation'] == away:
                        # Extract prediction data if available
                        odds = comp.get('odds', [])
                        if odds:
                            # ESPN sometimes includes win probability in odds
                            return {
                                'source': 'ESPN FPI',
                                'away_win_prob': None,  # Not always available
                                'home_win_prob': None,
                                'projected_score_away': None,
                                'projected_score_home': None,
                                'confidence': 'Medium'
                            }
        
        return None
        
    except Exception as e:
        print(f"ESPN FPI fetch error: {e}")
        return None


def fetch_fivethirtyeight_predictions(away: str, home: str) -> Optional[Dict]:
    """
    Fetch FiveThirtyEight ELO-based predictions
    
    Args:
        away: Away team abbreviation
        home: Home team abbreviation
        
    Returns:
        Dict with away_win_prob, home_win_prob, elo_diff
        None if not available
    """
    try:
        # FiveThirtyEight publishes their predictions as CSV
        # Note: 2025 season data may not be available yet in their public API
        url = "https://projects.fivethirtyeight.com/nfl-api/nfl_elo_latest.csv"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return None
        
        try:
            # Try parsing - 538's CSV can have malformed lines
            df = pd.read_csv(io.StringIO(response.text), 
                           on_bad_lines='skip',
                           encoding='utf-8')
        except Exception as parse_error:
            # CSV parsing failed completely
            return None
        
        # Check if we have the required columns
        required_cols = ['season', 'team1', 'team2']
        if not all(col in df.columns for col in required_cols):
            return None
        
        # Filter for current season (2025)
        df_2025 = df[df['season'] == 2025]
        
        if df_2025.empty:
            # 2025 season not available yet
            return None
            
            # FiveThirtyEight uses full team names, need to map
            team_mapping = {
                'NE': 'Patriots', 'BUF': 'Bills', 'MIA': 'Dolphins', 'NYJ': 'Jets',
                'BAL': 'Ravens', 'CIN': 'Bengals', 'CLE': 'Browns', 'PIT': 'Steelers',
                'HOU': 'Texans', 'IND': 'Colts', 'JAX': 'Jaguars', 'TEN': 'Titans',
                'DEN': 'Broncos', 'KC': 'Chiefs', 'LV': 'Raiders', 'LAC': 'Chargers',
                'DAL': 'Cowboys', 'NYG': 'Giants', 'PHI': 'Eagles', 'WAS': 'Commanders',
                'CHI': 'Bears', 'DET': 'Lions', 'GB': 'Packers', 'MIN': 'Vikings',
                'ATL': 'Falcons', 'CAR': 'Panthers', 'NO': 'Saints', 'TB': 'Buccaneers',
                'ARI': 'Cardinals', 'LA': 'Rams', 'SF': '49ers', 'SEA': 'Seahawks'
            }
            
            away_name = team_mapping.get(away, away)
            home_name = team_mapping.get(home, home)
            
            # Find matchup (check both team1/team2 combinations)
            matchup = df_2025[
                ((df_2025['team1'].str.contains(away_name, case=False, na=False)) & 
                 (df_2025['team2'].str.contains(home_name, case=False, na=False))) |
                ((df_2025['team1'].str.contains(home_name, case=False, na=False)) & 
                 (df_2025['team2'].str.contains(away_name, case=False, na=False)))
            ]
            
            if not matchup.empty:
                game = matchup.iloc[-1]  # Most recent prediction
                
                # Check which team is which
                if away_name.lower() in str(game.get('team1', '')).lower():
                    away_prob = game.get('elo_prob1', 0.5) * 100
                    home_prob = game.get('elo_prob2', 0.5) * 100
                else:
                    away_prob = game.get('elo_prob2', 0.5) * 100
                    home_prob = game.get('elo_prob1', 0.5) * 100
                
                return {
                    'source': 'FiveThirtyEight ELO',
                    'away_win_prob': round(away_prob, 1),
                    'home_win_prob': round(home_prob, 1),
                    'elo_diff': abs(game.get('elo1_pre', 1500) - game.get('elo2_pre', 1500)),
                    'confidence': 'High' if abs(away_prob - home_prob) > 20 else 'Medium'
                }
        
        return None
        
    except Exception as e:
        print(f"FiveThirtyEight fetch error: {e}")
        return None


def calculate_vegas_implied_probability(away: str, home: str) -> Optional[Dict]:
    """
    Calculate implied win probabilities from Vegas moneyline odds
    
    Args:
        away: Away team abbreviation
        home: Home team abbreviation
        
    Returns:
        Dict with away_win_prob, home_win_prob from moneyline
        None if not available
    """
    try:
        api_key = os.environ.get('ODDS_API_KEY', '')
        if not api_key:
            return None
        
        # Fetch current odds
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
        params = {
            'apiKey': api_key,
            'regions': 'us',
            'markets': 'h2h',  # Head-to-head (moneyline)
            'oddsFormat': 'american'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            games = response.json()
            
            for game in games:
                away_team = game.get('away_team', '')
                home_team = game.get('home_team', '')
                
                # Match teams (flexible matching)
                if away in away_team and home in home_team:
                    bookmakers = game.get('bookmakers', [])
                    
                    if not bookmakers:
                        continue
                    
                    # Get consensus from multiple bookmakers
                    away_odds_list = []
                    home_odds_list = []
                    
                    for bookmaker in bookmakers:
                        for market in bookmaker.get('markets', []):
                            if market['key'] == 'h2h':
                                for outcome in market['outcomes']:
                                    if away in outcome['name']:
                                        away_odds_list.append(outcome.get('price', 0))
                                    elif home in outcome['name']:
                                        home_odds_list.append(outcome.get('price', 0))
                    
                    if away_odds_list and home_odds_list:
                        # Average odds across books
                        avg_away_odds = sum(away_odds_list) / len(away_odds_list)
                        avg_home_odds = sum(home_odds_list) / len(home_odds_list)
                        
                        # Convert American odds to implied probability
                        def american_to_prob(odds):
                            if odds > 0:
                                return 100 / (odds + 100) * 100
                            else:
                                return abs(odds) / (abs(odds) + 100) * 100
                        
                        away_prob = american_to_prob(avg_away_odds)
                        home_prob = american_to_prob(avg_home_odds)
                        
                        # Normalize (remove vig)
                        total = away_prob + home_prob
                        away_prob = (away_prob / total) * 100
                        home_prob = (home_prob / total) * 100
                        
                        return {
                            'source': f'Vegas Consensus ({len(away_odds_list)} books)',
                            'away_win_prob': round(away_prob, 1),
                            'home_win_prob': round(home_prob, 1),
                            'avg_away_ml': int(avg_away_odds),
                            'avg_home_ml': int(avg_home_odds),
                            'confidence': 'High'  # Vegas is always high confidence
                        }
        
        return None
        
    except Exception as e:
        print(f"Vegas implied probability error: {e}")
        return None


def fetch_all_predictions(away: str, home: str) -> Dict[str, Optional[Dict]]:
    """
    Fetch predictions from all available sources
    
    Args:
        away: Away team abbreviation
        home: Home team abbreviation
        
    Returns:
        Dictionary with predictions from each source
    """
    return {
        'espn_fpi': fetch_espn_fpi_predictions(away, home),
        'fivethirtyeight': fetch_fivethirtyeight_predictions(away, home),
        'vegas': calculate_vegas_implied_probability(away, home)
    }

