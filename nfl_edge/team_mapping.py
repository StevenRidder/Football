"""
Canonical NFL Team Abbreviation Mapping

This module provides a single source of truth for team abbreviations across:
- ESPN API
- Odds API
- nflverse data
- Our prediction files
"""

# Canonical abbreviations (what we use internally)
CANONICAL_TEAMS = {
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE',
    'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC',
    'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
    'NYJ', 'PHI', 'PIT', 'SF', 'SEA', 'TB', 'TEN', 'WAS'
}

# ESPN uses different abbreviations for some teams
ESPN_TO_CANONICAL = {
    'ARI': 'ARI',
    'ATL': 'ATL',
    'BAL': 'BAL',
    'BUF': 'BUF',
    'CAR': 'CAR',
    'CHI': 'CHI',
    'CIN': 'CIN',
    'CLE': 'CLE',
    'DAL': 'DAL',
    'DEN': 'DEN',
    'DET': 'DET',
    'GB': 'GB',
    'HOU': 'HOU',
    'IND': 'IND',
    'JAX': 'JAX',
    'JAC': 'JAX',  # ESPN sometimes uses JAC
    'KC': 'KC',
    'LAC': 'LAC',
    'LAR': 'LAR',
    'LA': 'LAR',   # Old abbreviation
    'LV': 'LV',
    'MIA': 'MIA',
    'MIN': 'MIN',
    'NE': 'NE',
    'NO': 'NO',
    'NYG': 'NYG',
    'NYJ': 'NYJ',
    'PHI': 'PHI',
    'PIT': 'PIT',
    'SF': 'SF',
    'SEA': 'SEA',
    'TB': 'TB',
    'TEN': 'TEN',
    'WAS': 'WAS',
    'WSH': 'WAS',  # ESPN uses WSH
}

# Odds API uses full team names
ODDS_API_TO_CANONICAL = {
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
    "Los Angeles Rams": "LAR",
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

# nflverse uses same as canonical, but just in case
NFLVERSE_TO_CANONICAL = {
    'ARI': 'ARI',
    'ATL': 'ATL',
    'BAL': 'BAL',
    'BUF': 'BUF',
    'CAR': 'CAR',
    'CHI': 'CHI',
    'CIN': 'CIN',
    'CLE': 'CLE',
    'DAL': 'DAL',
    'DEN': 'DEN',
    'DET': 'DET',
    'GB': 'GB',
    'HOU': 'HOU',
    'IND': 'IND',
    'JAX': 'JAX',
    'JAC': 'JAX',
    'KC': 'KC',
    'LAC': 'LAC',
    'LAR': 'LAR',
    'LA': 'LAR',
    'LV': 'LV',
    'MIA': 'MIA',
    'MIN': 'MIN',
    'NE': 'NE',
    'NO': 'NO',
    'NYG': 'NYG',
    'NYJ': 'NYJ',
    'PHI': 'PHI',
    'PIT': 'PIT',
    'SF': 'SF',
    'SEA': 'SEA',
    'TB': 'TB',
    'TEN': 'TEN',
    'WAS': 'WAS',
    'WSH': 'WAS',
}


def normalize_team(team: str, source: str = 'espn') -> str:
    """
    Normalize team abbreviation to canonical format.
    
    Args:
        team: Team abbreviation or full name
        source: Data source ('espn', 'odds_api', 'nflverse')
    
    Returns:
        Canonical team abbreviation
    """
    if source == 'espn':
        return ESPN_TO_CANONICAL.get(team, team)
    elif source == 'odds_api':
        return ODDS_API_TO_CANONICAL.get(team, team)
    elif source == 'nflverse':
        return NFLVERSE_TO_CANONICAL.get(team, team)
    else:
        # Try all mappings
        return (ESPN_TO_CANONICAL.get(team) or 
                ODDS_API_TO_CANONICAL.get(team) or 
                NFLVERSE_TO_CANONICAL.get(team) or 
                team)


def validate_team(team: str) -> bool:
    """Check if team abbreviation is valid."""
    return team in CANONICAL_TEAMS

