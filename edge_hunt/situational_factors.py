"""
Situational factors for NFL betting edge detection.

Four Feature Buckets:
1. Matchups - Strength vs weakness (EPA/SR)
2. Weather - Wind/rain effects on scoring
3. Travel/Environment - Fatigue, timezone, temperature
4. Coaching Pace - Fast/slow pace effects on totals
"""

import pandas as pd
import nfl_data_py as nfl
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import numpy as np

# Stadium coordinates for travel distance
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

# Dome/retractable roof stadiums
DOME_STADIUMS = {'ARI', 'ATL', 'DAL', 'DET', 'HOU', 'IND', 'LAC', 'LAR', 'LV', 'MIN', 'NO'}


def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance between two coordinates in miles."""
    from math import radians, cos, sin, asin, sqrt
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Haversine formula
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    miles = 3956 * c  # Radius of earth in miles
    
    return miles


def get_travel_adjustment(away_team: str, home_team: str) -> Tuple[float, str]:
    """
    Calculate travel fatigue adjustment.
    
    Returns:
        (adjustment_pts, explanation)
    """
    if away_team not in STADIUM_COORDS or home_team not in STADIUM_COORDS:
        return 0.0, ""
    
    away_coord = STADIUM_COORDS[away_team]
    home_coord = STADIUM_COORDS[home_team]
    
    distance = calculate_distance(away_coord, home_coord)
    
    # Cross-country travel (>2000 miles)
    if distance > 2000:
        return -1.5, f"Cross-country travel ({distance:.0f} miles) → -1.5 pts to {away_team}"
    
    # Long distance (1500-2000 miles)
    elif distance > 1500:
        return -1.0, f"Long distance travel ({distance:.0f} miles) → -1.0 pts to {away_team}"
    
    # Medium distance (1000-1500 miles)
    elif distance > 1000:
        return -0.5, f"Medium distance travel ({distance:.0f} miles) → -0.5 pts to {away_team}"
    
    return 0.0, ""


def get_home_away_splits(team: str, is_home: bool, season: int = 2025) -> Tuple[float, str]:
    """
    Calculate home/away performance adjustment based on 2025 splits.
    
    Returns:
        (adjustment_pts, explanation)
    """
    try:
        # Fetch 2025 schedule
        schedule = nfl.import_schedules([season])
        schedule = schedule[schedule['week'] <= 8]  # Only completed games
        
        if is_home:
            team_games = schedule[schedule['home_team'] == team].copy()
            if len(team_games) == 0:
                return 0.0, ""
            
            wins = (team_games['home_score'] > team_games['away_score']).sum()
            total = len(team_games)
            win_pct = wins / total if total > 0 else 0.5
            
            # Home teams expected to win ~55%
            expected = 0.55
            diff = win_pct - expected
            
            if diff < -0.20:  # e.g., 0% vs 55% expected
                return -1.5, f"{team} home struggles (0-{total}) → -1.5 pts"
            elif diff < -0.10:
                return -1.0, f"{team} home struggles ({wins}-{total-wins}) → -1.0 pts"
            elif diff > 0.20:
                return +1.0, f"{team} home dominance ({wins}-{total-wins}) → +1.0 pts"
        
        else:  # Away
            team_games = schedule[schedule['away_team'] == team].copy()
            if len(team_games) == 0:
                return 0.0, ""
            
            wins = (team_games['away_score'] > team_games['home_score']).sum()
            total = len(team_games)
            win_pct = wins / total if total > 0 else 0.45
            
            # Away teams expected to win ~45%
            expected = 0.45
            diff = win_pct - expected
            
            if diff < -0.20:  # e.g., 0% vs 45% expected
                return -1.5, f"{team} away struggles ({wins}-{total-wins}) → -1.5 pts"
            elif diff < -0.10:
                return -1.0, f"{team} away struggles ({wins}-{total-wins}) → -1.0 pts"
            elif diff > 0.20:
                return +1.0, f"{team} away dominance ({wins}-{total-wins}) → +1.0 pts"
    
    except Exception as e:
        print(f"    Warning: Could not fetch home/away splits: {e}")
        return 0.0, ""
    
    return 0.0, ""


def get_pace_adjustment(away_team: str, home_team: str, season: int = 2025) -> Tuple[float, str]:
    """
    Calculate pace adjustment for totals.
    Fast pace teams = more plays = higher scoring.
    
    Returns:
        (adjustment_pts, explanation)
    """
    try:
        # Fetch play-by-play data (cached by nfl_data_py)
        pbp = nfl.import_pbp_data([season], columns=['posteam', 'game_id', 'play_type', 'week'])
        
        # Only use completed games (weeks 1-8)
        pbp = pbp[pbp['week'] <= 8]
        
        # Count plays per team per game
        plays_per_game = pbp[pbp['play_type'].isin(['pass', 'run'])].groupby(['posteam', 'game_id']).size()
        avg_plays = plays_per_game.groupby('posteam').mean()
        
        if away_team not in avg_plays.index or home_team not in avg_plays.index:
            return 0.0, ""
        
        away_pace = avg_plays[away_team]
        home_pace = avg_plays[home_team]
        combined_pace = (away_pace + home_pace) / 2
        
        # League average is ~65 plays/game
        league_avg = 65.0
        
        # Fast pace matchup (both teams >68 plays/game)
        if away_pace > 68 and home_pace > 68:
            adjustment = (combined_pace - league_avg) * 0.15  # ~0.15 pts per extra play
            return adjustment, f"Fast pace matchup ({combined_pace:.0f} plays/game) → +{adjustment:.1f} pts to total"
        
        # Slow pace matchup (both teams <62 plays/game)
        elif away_pace < 62 and home_pace < 62:
            adjustment = (combined_pace - league_avg) * 0.15
            return adjustment, f"Slow pace matchup ({combined_pace:.0f} plays/game) → {adjustment:.1f} pts to total"
    
    except Exception as e:
        print(f"    Warning: Could not fetch pace data: {e}")
        return 0.0, ""
    
    return 0.0, ""


def get_divisional_game_adjustment(away_team: str, home_team: str) -> Tuple[float, str]:
    """
    Divisional games tend to be more conservative and lower scoring.
    
    Returns:
        (adjustment_pts, explanation)
    """
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
    
    for division, teams in DIVISIONS.items():
        if away_team in teams and home_team in teams:
            return -2.0, f"Divisional game → -2.0 pts to total (more conservative)"
    
    return 0.0, ""


def get_temperature_adjustment(away_team: str, home_team: str, temp_f: float) -> Tuple[float, str]:
    """
    Extreme temperature adjustments.
    
    Returns:
        (adjustment_pts, explanation)
    """
    # Home team in dome = no adjustment
    if home_team in DOME_STADIUMS:
        return 0.0, ""
    
    # Extreme cold (<20°F)
    if temp_f < 20:
        return -2.0, f"Extreme cold ({temp_f:.0f}°F) → -2.0 pts to total"
    
    # Very cold (20-32°F)
    elif temp_f < 32:
        return -1.0, f"Very cold ({temp_f:.0f}°F) → -1.0 pts to total"
    
    # Extreme heat (>95°F)
    elif temp_f > 95:
        return -1.5, f"Extreme heat ({temp_f:.0f}°F) → -1.5 pts to total (fatigue)"
    
    return 0.0, ""


def get_all_situational_adjustments(
    away_team: str,
    home_team: str,
    temp_f: float = 70.0,
    season: int = 2025
) -> Dict:
    """
    Get all situational adjustments for a game.
    
    Returns:
        Dictionary with adjustments and explanations
    """
    adjustments = {
        'travel': get_travel_adjustment(away_team, home_team),
        'away_split': get_home_away_splits(away_team, is_home=False, season=season),
        'home_split': get_home_away_splits(home_team, is_home=True, season=season),
        'pace': get_pace_adjustment(away_team, home_team, season=season),
        'divisional': get_divisional_game_adjustment(away_team, home_team),
        'temperature': get_temperature_adjustment(away_team, home_team, temp_f),
    }
    
    # Calculate total adjustments
    spread_adj = 0.0
    total_adj = 0.0
    explanations = []
    
    # Travel affects away team only (spread)
    if adjustments['travel'][0] != 0:
        spread_adj += adjustments['travel'][0]
        total_adj += adjustments['travel'][0]  # Also reduces total
        explanations.append(adjustments['travel'][1])
    
    # Home/away splits affect spread
    if adjustments['away_split'][0] != 0:
        spread_adj += adjustments['away_split'][0]
        total_adj += adjustments['away_split'][0]
        explanations.append(adjustments['away_split'][1])
    
    if adjustments['home_split'][0] != 0:
        spread_adj -= adjustments['home_split'][0]  # Negative because it helps home
        total_adj += adjustments['home_split'][0]
        explanations.append(adjustments['home_split'][1])
    
    # Pace affects total only
    if adjustments['pace'][0] != 0:
        total_adj += adjustments['pace'][0]
        explanations.append(adjustments['pace'][1])
    
    # Divisional affects total only
    if adjustments['divisional'][0] != 0:
        total_adj += adjustments['divisional'][0]
        explanations.append(adjustments['divisional'][1])
    
    # Temperature affects total only
    if adjustments['temperature'][0] != 0:
        total_adj += adjustments['temperature'][0]
        explanations.append(adjustments['temperature'][1])
    
    return {
        'spread_adjustment': spread_adj,
        'total_adjustment': total_adj,
        'explanations': explanations,
        'has_adjustment': len(explanations) > 0
    }


if __name__ == "__main__":
    # Test with BAL @ MIA
    print("=" * 80)
    print("TESTING SITUATIONAL FACTORS: BAL @ MIA")
    print("=" * 80)
    print()
    
    result = get_all_situational_adjustments('BAL', 'MIA', temp_f=75.0, season=2025)
    
    print(f"Spread Adjustment: {result['spread_adjustment']:.1f} pts")
    print(f"Total Adjustment: {result['total_adjustment']:.1f} pts")
    print()
    print("Explanations:")
    for exp in result['explanations']:
        print(f"  • {exp}")
    
    print("\n" + "=" * 80)
    print("TESTING: MIN @ DET")
    print("=" * 80)
    print()
    
    result2 = get_all_situational_adjustments('MIN', 'DET', temp_f=45.0, season=2025)
    
    print(f"Spread Adjustment: {result2['spread_adjustment']:.1f} pts")
    print(f"Total Adjustment: {result2['total_adjustment']:.1f} pts")
    print()
    print("Explanations:")
    for exp in result2['explanations']:
        print(f"  • {exp}")

