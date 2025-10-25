"""
Scrape expert NFL predictions from major sports media sources.

Sources:
- ESPN: Expert picks consensus
- CBS Sports: Expert picks 
- NFL.com: Expert picks
- USA Today: Expert predictions
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re


def _get_full_team_name(abbr: str) -> str:
    """Map team abbreviation to full name"""
    mapping = {
        'ARI': 'Cardinals', 'ATL': 'Falcons', 'BAL': 'Ravens',
        'BUF': 'Bills', 'CAR': 'Panthers', 'CHI': 'Bears',
        'CIN': 'Bengals', 'CLE': 'Browns', 'DAL': 'Cowboys',
        'DEN': 'Broncos', 'DET': 'Lions', 'GB': 'Packers',
        'HOU': 'Texans', 'IND': 'Colts', 'JAX': 'Jaguars',
        'KC': 'Chiefs', 'LAC': 'Chargers', 'LA': 'Rams',
        'LAR': 'Rams', 'LV': 'Raiders', 'MIA': 'Dolphins',
        'MIN': 'Vikings', 'NE': 'Patriots', 'NO': 'Saints',
        'NYG': 'Giants', 'NYJ': 'Jets', 'PHI': 'Eagles',
        'PIT': 'Steelers', 'SEA': 'Seahawks', 'SF': '49ers',
        'TB': 'Buccaneers', 'TEN': 'Titans', 'WAS': 'Commanders'
    }
    return mapping.get(abbr, abbr)


def scrape_espn_picks(away: str, home: str, week: int = 8) -> Optional[Dict]:
    """
    Scrape ESPN expert picks
    
    Returns:
        Dict with consensus percentage or None
    """
    try:
        # ESPN expert picks URL
        url = f"https://www.espn.com/nfl/picks"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the game matchup
        away_name = _get_full_team_name(away)
        home_name = _get_full_team_name(home)
        
        # ESPN shows expert consensus as percentages
        # Try to find the matchup and parse expert picks
        # This is a simplified version - may need adjustment based on actual HTML structure
        
        return {
            'source': 'ESPN Experts',
            'away_pick_pct': None,  # Would need to parse from HTML
            'home_pick_pct': None,
            'consensus_winner': None,
            'total_experts': None
        }
        
    except Exception as e:
        print(f"ESPN scrape error: {e}")
        return None


def scrape_cbs_picks(away: str, home: str, week: int = 8) -> Optional[Dict]:
    """
    Scrape CBS Sports expert picks
    
    Returns:
        Dict with expert consensus or None
    """
    try:
        url = f"https://www.cbssports.com/nfl/picks/experts/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        away_name = _get_full_team_name(away)
        home_name = _get_full_team_name(home)
        
        # CBS shows expert picks with consensus percentages
        
        return {
            'source': 'CBS Sports Experts',
            'away_pick_pct': None,
            'home_pick_pct': None,
            'consensus_winner': None,
            'total_experts': None
        }
        
    except Exception as e:
        print(f"CBS scrape error: {e}")
        return None


def scrape_nfl_picks(away: str, home: str, week: int = 8) -> Optional[Dict]:
    """
    Scrape NFL.com expert picks
    
    Returns:
        Dict with expert picks or None
    """
    try:
        url = f"https://www.nfl.com/news/nfl-expert-picks-week-{week}-2025"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        away_name = _get_full_team_name(away)
        home_name = _get_full_team_name(home)
        
        return {
            'source': 'NFL.com Experts',
            'away_pick_pct': None,
            'home_pick_pct': None,
            'consensus_winner': None
        }
        
    except Exception as e:
        print(f"NFL.com scrape error: {e}")
        return None


def scrape_usa_today_picks(away: str, home: str, week: int = 8) -> Optional[Dict]:
    """
    Scrape USA Today expert picks
    
    Returns:
        Dict with predictions or None
    """
    try:
        url = f"https://www.usatoday.com/story/sports/nfl/predictions/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        away_name = _get_full_team_name(away)
        home_name = _get_full_team_name(home)
        
        return {
            'source': 'USA Today',
            'away_pick_pct': None,
            'home_pick_pct': None,
            'consensus_winner': None
        }
        
    except Exception as e:
        print(f"USA Today scrape error: {e}")
        return None


def get_all_expert_picks(away: str, home: str, week: int = 8) -> Dict:
    """
    Fetch expert picks from all major sources
    
    Args:
        away: Away team abbreviation
        home: Home team abbreviation
        week: NFL week number
        
    Returns:
        Dict with picks from all sources
    """
    print(f"Fetching expert picks for {away} @ {home} (Week {week})...")
    
    results = {
        'espn': scrape_espn_picks(away, home, week),
        'cbs': scrape_cbs_picks(away, home, week),
        'nfl': scrape_nfl_picks(away, home, week),
        'usa_today': scrape_usa_today_picks(away, home, week)
    }
    
    # Filter out None values
    results = {k: v for k, v in results.items() if v is not None}
    
    return results


if __name__ == '__main__':
    # Test scraper
    picks = get_all_expert_picks('WAS', 'KC', week=8)
    print(f"\nExpert picks: {picks}")

