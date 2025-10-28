"""
Situational features for NFL predictions:
- Rest days
- Travel distance
- Time zone changes
- Divisional games
- Primetime games
"""

import pandas as pd
from math import radians, cos, sin, asin, sqrt


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in miles
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in miles
    r = 3956
    
    return c * r


def calculate_rest_days(schedule_df, current_week):
    """
    Calculate days of rest for each team.
    
    Returns:
    - rest_days: days since last game (3-14 typical)
    - is_short_rest: 1 if < 6 days rest (Thursday game)
    """
    # This requires historical schedule data
    # For now, use heuristics:
    # - Thursday games: 3-4 days rest
    # - Sunday/Monday games: 6-7 days rest
    # - Bye week: 13-14 days rest
    
    rest_data = {}
    for team in schedule_df['team'].unique():
        # Default: 7 days (normal week)
        rest_data[team] = 7.0
    
    return rest_data


def calculate_travel_distance(matchups, stadiums_csv="data/stadiums.csv"):
    """
    Calculate travel distance for away team.
    
    Returns:
    - travel_miles: distance from home stadium to opponent's stadium
    - timezone_diff: hours difference (0-3)
    """
    stadiums = pd.read_csv(stadiums_csv).set_index("team")
    
    travel_data = []
    for away, home in matchups:
        if away not in stadiums.index or home not in stadiums.index:
            # Default values if stadium data missing
            travel_data.append({
                "away": away,
                "home": home,
                "away_travel_miles": 0.0,
                "home_travel_miles": 0.0,
                "timezone_diff": 0.0
            })
            continue
        
        away_stadium = stadiums.loc[away]
        home_stadium = stadiums.loc[home]
        
        # Calculate distance
        distance = haversine(
            away_stadium['lon'], away_stadium['lat'],
            home_stadium['lon'], home_stadium['lat']
        )
        
        # Calculate timezone difference
        # Rough approximation: 15 degrees longitude ≈ 1 hour
        tz_diff = abs(away_stadium['lon'] - home_stadium['lon']) / 15.0
        tz_diff = min(tz_diff, 3.0)  # Cap at 3 hours
        
        travel_data.append({
            "away": away,
            "home": home,
            "away_travel_miles": distance,
            "home_travel_miles": 0.0,  # Home team doesn't travel
            "timezone_diff": tz_diff
        })
    
    return pd.DataFrame(travel_data)


def add_divisional_flags(matchups):
    """
    Add flags for divisional and conference games.
    
    Divisions:
    - AFC East: BUF, MIA, NE, NYJ
    - AFC North: BAL, CIN, CLE, PIT
    - AFC South: HOU, IND, JAX, TEN
    - AFC West: DEN, KC, LAC, LV
    - NFC East: DAL, NYG, PHI, WAS
    - NFC North: CHI, DET, GB, MIN
    - NFC South: ATL, CAR, NO, TB
    - NFC West: ARI, LA, SF, SEA
    """
    divisions = {
        'AFC East': ['BUF', 'MIA', 'NE', 'NYJ'],
        'AFC North': ['BAL', 'CIN', 'CLE', 'PIT'],
        'AFC South': ['HOU', 'IND', 'JAX', 'TEN'],
        'AFC West': ['DEN', 'KC', 'LAC', 'LV'],
        'NFC East': ['DAL', 'NYG', 'PHI', 'WAS'],
        'NFC North': ['CHI', 'DET', 'GB', 'MIN'],
        'NFC South': ['ATL', 'CAR', 'NO', 'TB'],
        'NFC West': ['ARI', 'LA', 'SF', 'SEA']
    }
    
    # Create team-to-division mapping
    team_division = {}
    team_conference = {}
    for div_name, teams in divisions.items():
        conference = 'AFC' if div_name.startswith('AFC') else 'NFC'
        for team in teams:
            team_division[team] = div_name
            team_conference[team] = conference
    
    flags = []
    for away, home in matchups:
        away_div = team_division.get(away, 'UNKNOWN')
        home_div = team_division.get(home, 'UNKNOWN')
        away_conf = team_conference.get(away, 'UNKNOWN')
        home_conf = team_conference.get(home, 'UNKNOWN')
        
        is_divisional = 1 if away_div == home_div else 0
        is_conference = 1 if away_conf == home_conf else 0
        
        flags.append({
            "away": away,
            "home": home,
            "is_divisional": is_divisional,
            "is_conference": is_conference
        })
    
    return pd.DataFrame(flags)


def add_all_situational_features(matchups, current_week=1):
    """
    Add all situational features to matchups.
    
    Returns DataFrame with:
    - away_travel_miles, home_travel_miles
    - timezone_diff
    - is_divisional, is_conference
    - week_in_season
    """
    # Travel distance
    travel_df = calculate_travel_distance(matchups)
    
    # Divisional flags
    divisional_df = add_divisional_flags(matchups)
    
    # Merge
    result = travel_df.merge(divisional_df, on=['away', 'home'], how='left')
    
    # Add week in season
    result['week_in_season'] = current_week
    
    # Add rest days (placeholder for now - would need historical schedule)
    result['away_rest_days'] = 7.0
    result['home_rest_days'] = 7.0
    
    return result

