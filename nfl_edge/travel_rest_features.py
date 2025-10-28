"""
Travel and Rest Features for NFL Betting Model

This module calculates travel distance, timezone changes, and rest day differentials
for NFL games. Research shows these factors have measurable effects on performance:

1. Travel Distance - Long trips (>1500 miles) reduce performance
2. Timezone Changes - East-to-West and West-to-East travel affects circadian rhythm
3. Rest Days Differential - Teams with more rest have an advantage
4. Back-to-Back Travel - Consecutive away games reduce performance

References:
- Teams traveling >1500 miles perform ~2 points worse ATS
- West-to-East travel (especially for night games) reduces performance
- Extra rest day provides ~1-2 point advantage
"""

import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
from typing import Dict, Tuple
from datetime import datetime, timedelta


# NFL Stadium Locations (lat, lon, timezone)
STADIUM_INFO = {
    'ARI': (33.5276, -112.2626, 'America/Phoenix'),      # MST (no DST)
    'ATL': (33.7555, -84.4009, 'America/New_York'),      # EST
    'BAL': (39.2780, -76.6227, 'America/New_York'),      # EST
    'BUF': (42.7738, -78.7870, 'America/New_York'),      # EST
    'CAR': (35.2258, -80.8529, 'America/New_York'),      # EST
    'CHI': (41.8623, -87.6167, 'America/Chicago'),       # CST
    'CIN': (39.0954, -84.5160, 'America/New_York'),      # EST
    'CLE': (41.5061, -81.6995, 'America/New_York'),      # EST
    'DAL': (32.7473, -97.0945, 'America/Chicago'),       # CST
    'DEN': (39.7439, -105.0201, 'America/Denver'),       # MST
    'DET': (42.3400, -83.0456, 'America/Detroit'),       # EST
    'GB': (44.5013, -88.0622, 'America/Chicago'),        # CST
    'HOU': (29.6847, -95.4107, 'America/Chicago'),       # CST
    'IND': (39.7601, -86.1639, 'America/Indiana/Indianapolis'),  # EST
    'JAX': (30.3240, -81.6373, 'America/New_York'),      # EST
    'KC': (39.0489, -94.4839, 'America/Chicago'),        # CST
    'LAC': (33.9535, -118.3390, 'America/Los_Angeles'),  # PST
    'LAR': (33.9535, -118.3390, 'America/Los_Angeles'),  # PST
    'LA': (33.9535, -118.3390, 'America/Los_Angeles'),   # PST
    'LV': (36.0909, -115.1833, 'America/Los_Angeles'),   # PST
    'MIA': (25.9580, -80.2389, 'America/New_York'),      # EST
    'MIN': (44.9738, -93.2577, 'America/Chicago'),       # CST
    'NE': (42.0909, -71.2643, 'America/New_York'),       # EST
    'NO': (29.9511, -90.0812, 'America/Chicago'),        # CST
    'NYG': (40.8135, -74.0745, 'America/New_York'),      # EST
    'NYJ': (40.8135, -74.0745, 'America/New_York'),      # EST
    'PHI': (39.9008, -75.1675, 'America/New_York'),      # EST
    'PIT': (40.4468, -80.0158, 'America/New_York'),      # EST
    'SEA': (47.5952, -122.3316, 'America/Los_Angeles'),  # PST
    'SF': (37.4032, -121.9698, 'America/Los_Angeles'),   # PST
    'TB': (27.9759, -82.5033, 'America/New_York'),       # EST
    'TEN': (36.1665, -86.7713, 'America/Chicago'),       # CST
    'WAS': (38.9076, -76.8645, 'America/New_York'),      # EST
}

# Timezone hour offsets from EST
TIMEZONE_OFFSETS = {
    'America/New_York': 0,
    'America/Detroit': 0,
    'America/Indiana/Indianapolis': 0,
    'America/Chicago': -1,
    'America/Denver': -2,
    'America/Phoenix': -2,  # No DST
    'America/Los_Angeles': -3,
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two points in miles.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in miles
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in miles
    r = 3956
    
    return c * r


def get_timezone_change(away_team: str, home_team: str) -> int:
    """
    Calculate timezone change for away team (hours).
    
    Positive = traveling east (lose hours, harder adjustment)
    Negative = traveling west (gain hours, easier adjustment)
    
    Args:
        away_team: Away team abbreviation
        home_team: Home team abbreviation
    
    Returns:
        Timezone change in hours
    """
    if away_team not in STADIUM_INFO or home_team not in STADIUM_INFO:
        return 0
    
    away_tz = STADIUM_INFO[away_team][2]
    home_tz = STADIUM_INFO[home_team][2]
    
    away_offset = TIMEZONE_OFFSETS.get(away_tz, 0)
    home_offset = TIMEZONE_OFFSETS.get(home_tz, 0)
    
    # Positive = traveling east
    return home_offset - away_offset


def calculate_travel_features(away_team: str, home_team: str) -> Dict:
    """
    Calculate travel-related features for a game.
    
    Args:
        away_team: Away team abbreviation
        home_team: Home team abbreviation
    
    Returns:
        Dictionary with travel features
    """
    # Get stadium locations
    if away_team not in STADIUM_INFO or home_team not in STADIUM_INFO:
        return {
            'travel_distance_miles': 0.0,
            'timezone_change_hours': 0,
            'is_long_travel': 0,
            'is_cross_country': 0,
            'is_east_to_west': 0,
            'is_west_to_east': 0,
            'travel_impact_score': 0.0
        }
    
    away_lat, away_lon, away_tz = STADIUM_INFO[away_team]
    home_lat, home_lon, home_tz = STADIUM_INFO[home_team]
    
    # Calculate distance
    distance = haversine_distance(away_lat, away_lon, home_lat, home_lon)
    
    # Calculate timezone change
    tz_change = get_timezone_change(away_team, home_team)
    
    # Binary flags
    is_long_travel = 1 if distance > 1500 else 0
    is_cross_country = 1 if distance > 2500 else 0
    is_east_to_west = 1 if tz_change < 0 else 0  # Traveling west
    is_west_to_east = 1 if tz_change > 0 else 0  # Traveling east
    
    # Calculate travel impact score
    # Research shows:
    # - Distance >1500 miles: -1 to -2 points
    # - West-to-East travel: -0.5 to -1 point (especially for night games)
    # - East-to-West travel: -0.3 to -0.5 point
    impact = 0.0
    
    if distance > 1500:
        impact -= (distance - 1500) / 1000  # -1 point per 1000 miles over 1500
    
    if tz_change > 0:  # West to East
        impact -= abs(tz_change) * 0.5  # -0.5 per timezone
    elif tz_change < 0:  # East to West
        impact -= abs(tz_change) * 0.3  # -0.3 per timezone
    
    return {
        'travel_distance_miles': distance,
        'timezone_change_hours': tz_change,
        'is_long_travel': is_long_travel,
        'is_cross_country': is_cross_country,
        'is_east_to_west': is_east_to_west,
        'is_west_to_east': is_west_to_east,
        'travel_impact_score': impact
    }


def calculate_rest_differential(away_rest_days: int, home_rest_days: int) -> Dict:
    """
    Calculate rest day differential features.
    
    Args:
        away_rest_days: Days of rest for away team
        home_rest_days: Days of rest for home team
    
    Returns:
        Dictionary with rest features
    """
    rest_diff = home_rest_days - away_rest_days
    
    # Binary flags
    home_extra_rest = 1 if rest_diff > 0 else 0
    away_extra_rest = 1 if rest_diff < 0 else 0
    home_short_week = 1 if home_rest_days < 6 else 0  # Thursday game
    away_short_week = 1 if away_rest_days < 6 else 0
    
    # Rest impact score
    # Research shows ~1-2 point advantage per extra rest day
    impact = rest_diff * 1.5
    
    return {
        'rest_differential': rest_diff,
        'home_rest_days': home_rest_days,
        'away_rest_days': away_rest_days,
        'home_extra_rest': home_extra_rest,
        'away_extra_rest': away_extra_rest,
        'home_short_week': home_short_week,
        'away_short_week': away_short_week,
        'rest_impact_score': impact
    }


def add_travel_rest_features(matchups: pd.DataFrame) -> pd.DataFrame:
    """
    Add travel and rest features to matchups DataFrame.
    
    Args:
        matchups: DataFrame with 'away' and 'home' columns
                 Optionally 'away_rest_days' and 'home_rest_days'
    
    Returns:
        DataFrame with travel and rest features added
    """
    df = matchups.copy()
    
    # Calculate travel features
    travel_data = []
    for idx, row in df.iterrows():
        travel = calculate_travel_features(row['away'], row['home'])
        travel_data.append(travel)
    
    travel_df = pd.DataFrame(travel_data)
    
    # Calculate rest features if available
    if 'away_rest_days' in df.columns and 'home_rest_days' in df.columns:
        rest_data = []
        for idx, row in df.iterrows():
            rest = calculate_rest_differential(
                row.get('away_rest_days', 7),
                row.get('home_rest_days', 7)
            )
            rest_data.append(rest)
        
        rest_df = pd.DataFrame(rest_data)
    else:
        # Default: assume 7 days rest (no differential)
        rest_df = pd.DataFrame({
            'rest_differential': [0] * len(df),
            'home_rest_days': [7] * len(df),
            'away_rest_days': [7] * len(df),
            'home_extra_rest': [0] * len(df),
            'away_extra_rest': [0] * len(df),
            'home_short_week': [0] * len(df),
            'away_short_week': [0] * len(df),
            'rest_impact_score': [0.0] * len(df)
        })
    
    # Combine travel and rest features
    combined_df = pd.concat([travel_df, rest_df], axis=1)
    
    # Prefix with 'travel_' or 'rest_'
    combined_df.columns = [
        f'travel_{col}' if 'travel' in col or 'timezone' in col or 'east' in col or 'west' in col or 'cross' in col or 'long' in col
        else f'rest_{col}' if 'rest' in col or 'short' in col or 'extra' in col
        else col
        for col in combined_df.columns
    ]
    
    # Concatenate with original dataframe
    df = pd.concat([df, combined_df], axis=1)
    
    print(f"✅ Added travel and rest features for {len(df)} games")
    
    return df


if __name__ == "__main__":
    # Test the module
    print("Testing travel and rest features...")
    
    # Create sample matchups
    test_matchups = pd.DataFrame({
        'away': ['SEA', 'MIA', 'NE', 'DAL'],
        'home': ['NE', 'LAR', 'BUF', 'SF'],
        'away_rest_days': [7, 6, 10, 7],
        'home_rest_days': [7, 7, 7, 10]
    })
    
    # Add features
    enhanced = add_travel_rest_features(test_matchups)
    
    # Display key features
    print("\nSample travel features:")
    travel_cols = ['away', 'home', 'travel_travel_distance_miles', 'travel_timezone_change_hours', 
                   'travel_is_long_travel', 'travel_travel_impact_score']
    print(enhanced[travel_cols].to_string())
    
    print("\nSample rest features:")
    rest_cols = ['away', 'home', 'rest_rest_differential', 'rest_home_extra_rest', 
                 'rest_away_short_week', 'rest_rest_impact_score']
    print(enhanced[rest_cols].to_string())
    
    print("\nAll travel/rest columns:")
    feature_cols = [c for c in enhanced.columns if c.startswith('travel_') or c.startswith('rest_')]
    for col in sorted(feature_cols):
        print(f"  - {col}")

