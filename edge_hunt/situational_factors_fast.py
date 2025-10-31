"""
Fast version of situational factors - uses cached data and simpler calculations.

All adjustment values are ML-learned from 1,343 historical games (2020-2024).
Apply calibration multiplier to amplify/dampen these learned values.
"""

from typing import Dict, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from adjustment_calibration import apply_calibration

# Pre-computed 2025 home/away records (through Week 8)
HOME_AWAY_RECORDS_2025 = {
    # Format: team: {'away_wins': X, 'away_total': Y, 'home_wins': Z, 'home_total': W}
    'BAL': {'away_wins': 0, 'away_total': 2, 'home_wins': 3, 'home_total': 3},
    'MIA': {'away_wins': 1, 'away_total': 3, 'home_wins': 0, 'home_total': 3},
    'ATL': {'away_wins': 2, 'away_total': 4, 'home_wins': 2, 'home_total': 3},
    'NE': {'away_wins': 1, 'away_total': 3, 'home_wins': 1, 'home_total': 4},
    'CAR': {'away_wins': 0, 'away_total': 4, 'home_wins': 1, 'home_total': 3},
    'GB': {'away_wins': 3, 'away_total': 4, 'home_wins': 2, 'home_total': 3},
    'CHI': {'away_wins': 1, 'away_total': 3, 'home_wins': 3, 'home_total': 4},
    'CIN': {'away_wins': 0, 'away_total': 3, 'home_wins': 3, 'home_total': 4},
    'DEN': {'away_wins': 2, 'away_total': 4, 'home_wins': 3, 'home_total': 3},
    'HOU': {'away_wins': 3, 'away_total': 4, 'home_wins': 3, 'home_total': 3},
    'MIN': {'away_wins': 2, 'away_total': 3, 'home_wins': 3, 'home_total': 4},
    'DET': {'away_wins': 3, 'away_total': 4, 'home_wins': 3, 'home_total': 3},
    'IND': {'away_wins': 2, 'away_total': 4, 'home_wins': 2, 'home_total': 3},
    'PIT': {'away_wins': 3, 'away_total': 3, 'home_wins': 3, 'home_total': 4},
    'LAC': {'away_wins': 2, 'away_total': 3, 'home_wins': 2, 'home_total': 4},
    'TEN': {'away_wins': 0, 'away_total': 4, 'home_wins': 1, 'home_total': 3},
    'SF': {'away_wins': 2, 'away_total': 4, 'home_wins': 2, 'home_total': 3},
    'NYG': {'away_wins': 1, 'away_total': 4, 'home_wins': 1, 'home_total': 3},
    'JAX': {'away_wins': 1, 'away_total': 4, 'home_wins': 1, 'home_total': 3},
    'LV': {'away_wins': 1, 'away_total': 3, 'home_wins': 1, 'home_total': 4},
    'NO': {'away_wins': 1, 'away_total': 4, 'home_wins': 1, 'home_total': 3},
    'LA': {'away_wins': 2, 'away_total': 3, 'home_wins': 2, 'home_total': 4},
    'KC': {'away_wins': 4, 'away_total': 4, 'home_wins': 3, 'home_total': 3},
    'BUF': {'away_wins': 3, 'away_total': 3, 'home_wins': 4, 'home_total': 4},
    'SEA': {'away_wins': 2, 'away_total': 4, 'home_wins': 2, 'home_total': 3},
    'WAS': {'away_wins': 3, 'away_total': 4, 'home_wins': 3, 'home_total': 3},
    'ARI': {'away_wins': 2, 'away_total': 4, 'home_wins': 2, 'home_total': 3},
    'DAL': {'away_wins': 1, 'away_total': 3, 'home_wins': 2, 'home_total': 4},
}

# Stadium coordinates
STADIUM_COORDS = {
    'ARI': (33.5276, -112.2626), 'ATL': (33.7554, -84.4008), 'BAL': (39.2780, -76.6227),
    'BUF': (42.7738, -78.7870), 'CAR': (35.2258, -80.8530), 'CHI': (41.8623, -87.6167),
    'CIN': (39.0954, -84.5160), 'CLE': (41.5061, -81.6995), 'DAL': (32.7473, -97.0945),
    'DEN': (39.7439, -105.0201), 'DET': (42.3400, -83.0456), 'GB': (44.5013, -88.0622),
    'HOU': (29.6847, -95.4107), 'IND': (39.7601, -86.1639), 'JAX': (30.3240, -81.6373),
    'KC': (39.0490, -94.4839), 'LV': (36.0909, -115.1833), 'LAC': (34.0141, -118.2879),
    'LAR': (34.0141, -118.2879), 'MIA': (25.9580, -80.2389), 'MIN': (44.9738, -93.2577),
    'NE': (42.0909, -71.2643), 'NO': (29.9511, -90.0812), 'NYG': (40.8135, -74.0745),
    'NYJ': (40.8135, -74.0745), 'PHI': (39.9008, -75.1675), 'PIT': (40.4468, -80.0158),
    'SF': (37.4032, -121.9698), 'SEA': (47.5952, -122.3316), 'TB': (27.9759, -82.5033),
    'TEN': (36.1665, -86.7713), 'WAS': (38.9076, -76.8645)
}

# Divisions
DIVISIONS = {
    'AFC_EAST': ['BUF', 'MIA', 'NE', 'NYJ'],
    'AFC_NORTH': ['BAL', 'CIN', 'CLE', 'PIT'],
    'AFC_SOUTH': ['HOU', 'IND', 'JAX', 'TEN'],
    'AFC_WEST': ['DEN', 'KC', 'LAC', 'LV'],
    'NFC_EAST': ['DAL', 'NYG', 'PHI', 'WAS'],
    'NFC_NORTH': ['CHI', 'DET', 'GB', 'MIN'],
    'NFC_SOUTH': ['ATL', 'CAR', 'NO', 'TB'],
    'NFC_WEST': ['ARI', 'LAR', 'SF', 'SEA'],
}


def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance between two coordinates in miles."""
    from math import radians, cos, sin, asin, sqrt
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    miles = 3956 * c
    
    return miles


def get_travel_adjustment(away_team: str, home_team: str) -> Tuple[float, str]:
    """
    Calculate travel fatigue adjustment.
    
    LEARNED FROM 1,343 GAMES (2020-2024):
    - travel_distance: +0.058 pts per 1000 miles (spread)
    - travel_long (>2000mi): -0.019 pts (spread)
    - travel_medium (1000-2000mi): +0.030 pts (spread)
    
    NOTE: Effects are VERY SMALL (~0.03-0.06 pts), market already prices this efficiently.
    Using conservative values based on data.
    """
    if away_team not in STADIUM_COORDS or home_team not in STADIUM_COORDS:
        return 0.0, ""
    
    distance = calculate_distance(STADIUM_COORDS[away_team], STADIUM_COORDS[home_team])
    
    # Data-driven adjustments (much smaller than expert guesses)
    # Apply calibration multiplier to amplify these tiny learned values
    if distance > 2000:
        # Long travel shows slight NEGATIVE effect (-0.019 pts)
        adj = apply_calibration(-0.02)
        return adj, f"Cross-country travel ({distance:.0f} miles) → {adj:+.2f} pts to {away_team}"
    elif distance > 1000:
        # Medium travel shows slight POSITIVE effect (+0.030 pts)
        adj = apply_calibration(+0.03)
        return adj, f"Medium distance travel ({distance:.0f} miles) → {adj:+.2f} pts to {away_team}"
    
    return 0.0, ""


def get_home_away_splits(team: str, is_home: bool) -> Tuple[float, str]:
    """
    Calculate home/away performance adjustment.
    
    ⚠️ DISABLED: Home/away splits were NOT in the training data (1,343 games).
    We have NO learned values for this, so we're turning it off.
    
    The market already prices home/away performance efficiently.
    If we want to use this, we need to:
    1. Add home/away win% as features to the training data
    2. Re-train the model to learn the actual impact
    3. Use SHAP values to get data-driven adjustments
    
    For now: RETURNING 0.0 (no adjustment)
    """
    return 0.0, ""
    
    # OLD CODE (DISABLED - NOT DATA-DRIVEN):
    # if team not in HOME_AWAY_RECORDS_2025:
    #     return 0.0, ""
    # 
    # record = HOME_AWAY_RECORDS_2025[team]
    # 
    # if is_home:
    #     wins = record['home_wins']
    #     total = record['home_total']
    #     win_pct = wins / total if total > 0 else 0.5
    #     expected = 0.55
    #     diff = win_pct - expected
    #     
    #     if diff < -0.30:
    #         return -0.5, f"{team} home struggles ({wins}-{total-wins}) → -0.5 pts"
    #     elif diff > 0.30:
    #         return +0.5, f"{team} home dominance ({wins}-{total-wins}) → +0.5 pts"
    # else:
    #     wins = record['away_wins']
    #     total = record['away_total']
    #     win_pct = wins / total if total > 0 else 0.45
    #     expected = 0.45
    #     diff = win_pct - expected
    #     
    #     if diff < -0.30:
    #         return -0.5, f"{team} away struggles ({wins}-{total-wins}) → -0.5 pts"
    #     elif diff > 0.30:
    #         return +0.5, f"{team} away dominance ({wins}-{total-wins}) → +0.5 pts"
    # 
    # return 0.0, ""


def get_divisional_game_adjustment(away_team: str, home_team: str) -> Tuple[float, str]:
    """
    Divisional games adjustment.
    
    LEARNED FROM 1,343 GAMES (2020-2024):
    - divisional: -0.027 pts (spread), -0.033 pts (total)
    
    Effect is TINY (~0.03 pts), essentially noise.
    Keeping minimal adjustment for divisional games.
    """
    for division, teams in DIVISIONS.items():
        if away_team in teams and home_team in teams:
            # Data shows ~0.03 pts lower scoring in divisional games
            # Apply calibration multiplier
            adj = apply_calibration(-0.03)
            return adj, f"Divisional game → {adj:+.2f} pts to total (data-driven)"
    
    return 0.0, ""


def get_all_situational_adjustments_fast(away_team: str, home_team: str) -> Dict:
    """Get all situational adjustments (fast version without nflverse)."""
    adjustments = {
        'travel': get_travel_adjustment(away_team, home_team),
        'away_split': get_home_away_splits(away_team, is_home=False),
        'home_split': get_home_away_splits(home_team, is_home=True),
        'divisional': get_divisional_game_adjustment(away_team, home_team),
    }
    
    # Track adjustments per team
    away_adj = 0.0
    home_adj = 0.0
    explanations = []
    
    # Travel - only affects away team
    if adjustments['travel'][0] != 0:
        away_adj += adjustments['travel'][0]
        explanations.append(adjustments['travel'][1])
    
    # Away splits - only affects away team
    if adjustments['away_split'][0] != 0:
        away_adj += adjustments['away_split'][0]
        explanations.append(adjustments['away_split'][1])
    
    # Home splits - only affects home team
    if adjustments['home_split'][0] != 0:
        home_adj += adjustments['home_split'][0]
        explanations.append(adjustments['home_split'][1])
    
    # Divisional - affects both teams equally (lower scoring game overall)
    if adjustments['divisional'][0] != 0:
        divisional_adj = adjustments['divisional'][0] / 2  # Split between teams
        away_adj += divisional_adj
        home_adj += divisional_adj
        explanations.append(adjustments['divisional'][1])
    
    # Calculate spread and total from team adjustments
    spread_adj = away_adj - home_adj  # Positive = away team favored more
    total_adj = away_adj + home_adj   # Sum of both adjustments
    
    return {
        'away_adjustment': away_adj,
        'home_adjustment': home_adj,
        'spread_adjustment': spread_adj,
        'total_adjustment': total_adj,
        'explanations': explanations,
        'has_adjustment': len(explanations) > 0
    }


if __name__ == "__main__":
    # Test all Week 9 games
    games = [
        ('BAL', 'MIA'), ('ATL', 'NE'), ('CAR', 'GB'), ('CHI', 'CIN'),
        ('DEN', 'HOU'), ('MIN', 'DET'), ('IND', 'PIT'), ('LAC', 'TEN'),
        ('SF', 'NYG'), ('JAX', 'LV'), ('NO', 'LA'), ('KC', 'BUF'),
        ('SEA', 'WAS'), ('ARI', 'DAL'),
    ]
    
    print('=' * 80)
    print('FAST SITUATIONAL FACTORS TEST - WEEK 9')
    print('=' * 80)
    print()
    
    total_with_adjustments = 0
    
    for away, home in games:
        result = get_all_situational_adjustments_fast(away, home)
        
        if result['has_adjustment']:
            total_with_adjustments += 1
            print(f'{away} @ {home}:')
            print(f'  Spread Adj: {result["spread_adjustment"]:+.1f} pts')
            print(f'  Total Adj: {result["total_adjustment"]:+.1f} pts')
            for exp in result['explanations']:
                print(f'    • {exp}')
            print()
    
    print('=' * 80)
    print(f'SUMMARY: {total_with_adjustments}/{len(games)} games have situational adjustments')
    print('=' * 80)

