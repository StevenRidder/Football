"""
Weather Features for NFL Betting Model

This module fetches and processes weather data for NFL games, focusing on
measurable environmental factors that affect scoring and efficiency:

1. Wind Speed - Documented effect on passing efficiency and totals
2. Temperature - Affects ball handling and player performance  
3. Precipitation - Reduces scoring and passing yards

Weather data is collected at kickoff time and binned into empirically meaningful
ranges based on research showing effects on NFL outcomes.

References:
- Wind >15 mph reduces passing efficiency and lowers totals
- Temperature <32°F affects ball handling and reduces scoring
- Precipitation (rain/snow) reduces passing yards and total points
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import os


# NFL Stadium Locations (lat, lon)
STADIUM_LOCATIONS = {
    'ARI': (33.5276, -112.2626),  # State Farm Stadium
    'ATL': (33.7555, -84.4009),   # Mercedes-Benz Stadium
    'BAL': (39.2780, -76.6227),   # M&T Bank Stadium
    'BUF': (42.7738, -78.7870),   # Highmark Stadium
    'CAR': (35.2258, -80.8529),   # Bank of America Stadium
    'CHI': (41.8623, -87.6167),   # Soldier Field
    'CIN': (39.0954, -84.5160),   # Paycor Stadium
    'CLE': (41.5061, -81.6995),   # Cleveland Browns Stadium
    'DAL': (32.7473, -97.0945),   # AT&T Stadium (dome)
    'DEN': (39.7439, -105.0201),  # Empower Field
    'DET': (42.3400, -83.0456),   # Ford Field (dome)
    'GB': (44.5013, -88.0622),    # Lambeau Field
    'HOU': (29.6847, -95.4107),   # NRG Stadium (retractable)
    'IND': (39.7601, -86.1639),   # Lucas Oil Stadium (retractable)
    'JAX': (30.3240, -81.6373),   # TIAA Bank Field
    'KC': (39.0489, -94.4839),    # GEHA Field at Arrowhead
    'LAC': (33.9535, -118.3390),  # SoFi Stadium (dome)
    'LAR': (33.9535, -118.3390),  # SoFi Stadium (dome)
    'LA': (33.9535, -118.3390),   # SoFi Stadium (dome)
    'LV': (36.0909, -115.1833),   # Allegiant Stadium (dome)
    'MIA': (25.9580, -80.2389),   # Hard Rock Stadium
    'MIN': (44.9738, -93.2577),   # U.S. Bank Stadium (dome)
    'NE': (42.0909, -71.2643),    # Gillette Stadium
    'NO': (29.9511, -90.0812),    # Caesars Superdome (dome)
    'NYG': (40.8135, -74.0745),   # MetLife Stadium
    'NYJ': (40.8135, -74.0745),   # MetLife Stadium
    'PHI': (39.9008, -75.1675),   # Lincoln Financial Field
    'PIT': (40.4468, -80.0158),   # Acrisure Stadium
    'SEA': (47.5952, -122.3316),  # Lumen Field
    'SF': (37.4032, -121.9698),   # Levi's Stadium
    'TB': (27.9759, -82.5033),    # Raymond James Stadium
    'TEN': (36.1665, -86.7713),   # Nissan Stadium
    'WAS': (38.9076, -76.8645),   # Northwest Stadium
}

# Dome/Retractable Roof Stadiums (weather has minimal effect)
DOME_STADIUMS = {'DAL', 'DET', 'LAC', 'LAR', 'LA', 'LV', 'MIN', 'NO'}
RETRACTABLE_STADIUMS = {'HOU', 'IND'}  # Often closed in bad weather


def get_weather_for_game(home_team: str, 
                         game_date: datetime,
                         api_key: Optional[str] = None) -> Dict:
    """
    Fetch weather data for a game at kickoff time.
    
    Uses Open-Meteo API (free, no API key required) for historical weather.
    
    Args:
        home_team: Home team abbreviation
        game_date: Game datetime (kickoff time)
        api_key: Optional API key (not needed for Open-Meteo)
    
    Returns:
        Dictionary with weather features
    """
    # Check if dome/retractable
    is_dome = home_team in DOME_STADIUMS
    is_retractable = home_team in RETRACTABLE_STADIUMS
    
    # Default weather (neutral conditions)
    default_weather = {
        'temperature_f': 65.0,
        'wind_speed_mph': 5.0,
        'precipitation_inches': 0.0,
        'is_dome': is_dome,
        'is_retractable': is_retractable,
        'weather_impact_score': 0.0
    }
    
    # If dome, weather doesn't matter
    if is_dome:
        return default_weather
    
    # Get stadium location
    if home_team not in STADIUM_LOCATIONS:
        print(f"⚠️  No stadium location for {home_team}, using default weather")
        return default_weather
    
    lat, lon = STADIUM_LOCATIONS[home_team]
    
    try:
        # Use Open-Meteo API (free, no key required)
        # https://open-meteo.com/en/docs/historical-weather-api
        
        date_str = game_date.strftime('%Y-%m-%d')
        hour = game_date.hour
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            'latitude': lat,
            'longitude': lon,
            'start_date': date_str,
            'end_date': date_str,
            'hourly': 'temperature_2m,windspeed_10m,precipitation',
            'temperature_unit': 'fahrenheit',
            'windspeed_unit': 'mph',
            'precipitation_unit': 'inch',
            'timezone': 'America/New_York'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract hourly data for kickoff time
        hourly = data.get('hourly', {})
        times = hourly.get('time', [])
        
        # Find closest hour to kickoff
        target_time = game_date.strftime('%Y-%m-%dT%H:00')
        if target_time in times:
            idx = times.index(target_time)
        else:
            # Use closest available hour
            idx = hour if hour < len(times) else 0
        
        temperature = hourly.get('temperature_2m', [65.0])[idx]
        wind_speed = hourly.get('windspeed_10m', [5.0])[idx]
        precipitation = hourly.get('precipitation', [0.0])[idx]
        
        # Calculate weather impact score
        impact_score = calculate_weather_impact(
            temperature, wind_speed, precipitation, is_retractable
        )
        
        return {
            'temperature_f': temperature,
            'wind_speed_mph': wind_speed,
            'precipitation_inches': precipitation,
            'is_dome': is_dome,
            'is_retractable': is_retractable,
            'weather_impact_score': impact_score
        }
        
    except Exception as e:
        print(f"⚠️  Weather API error for {home_team} on {date_str}: {e}")
        return default_weather


def calculate_weather_impact(temperature: float, 
                             wind_speed: float, 
                             precipitation: float,
                             is_retractable: bool) -> float:
    """
    Calculate overall weather impact score.
    
    Based on research:
    - Wind >15 mph: -0.5 to -1.0 points per game per 5 mph
    - Temp <32°F: -0.3 to -0.5 points per game per 10°F below
    - Precipitation >0.1": -0.5 to -1.0 points per game
    
    Returns:
        Negative score = reduces scoring (lower totals)
        Positive score = neutral/favorable conditions
    """
    impact = 0.0
    
    # Wind impact (exponential above 15 mph)
    if wind_speed > 15:
        impact -= (wind_speed - 15) * 0.2  # -0.2 per mph above 15
    
    # Temperature impact (linear below 32°F)
    if temperature < 32:
        impact -= (32 - temperature) * 0.05  # -0.05 per degree below freezing
    
    # Precipitation impact
    if precipitation > 0.1:
        impact -= 2.0  # Significant reduction in scoring
    elif precipitation > 0.01:
        impact -= 0.5  # Light rain/snow
    
    # Retractable roofs often close in bad weather
    if is_retractable and (wind_speed > 20 or precipitation > 0.1):
        impact *= 0.3  # Reduce impact (roof likely closed)
    
    return impact


def bin_weather_features(weather: Dict) -> Dict:
    """
    Bin weather into empirically meaningful categories.
    
    Args:
        weather: Raw weather dictionary
    
    Returns:
        Dictionary with binned features
    """
    temp = weather['temperature_f']
    wind = weather['wind_speed_mph']
    precip = weather['precipitation_inches']
    
    return {
        # Temperature bins
        'temp_freezing': 1 if temp < 32 else 0,
        'temp_cold': 1 if 32 <= temp < 45 else 0,
        'temp_moderate': 1 if 45 <= temp < 75 else 0,
        'temp_hot': 1 if temp >= 75 else 0,
        
        # Wind bins
        'wind_calm': 1 if wind < 10 else 0,
        'wind_moderate': 1 if 10 <= wind < 15 else 0,
        'wind_high': 1 if 15 <= wind < 20 else 0,
        'wind_extreme': 1 if wind >= 20 else 0,
        
        # Precipitation bins
        'precip_none': 1 if precip < 0.01 else 0,
        'precip_light': 1 if 0.01 <= precip < 0.1 else 0,
        'precip_heavy': 1 if precip >= 0.1 else 0,
        
        # Raw values
        'temperature_f': temp,
        'wind_speed_mph': wind,
        'precipitation_inches': precip,
        'weather_impact_score': weather['weather_impact_score'],
        'is_dome': weather['is_dome'],
        'is_retractable': weather['is_retractable']
    }


def add_weather_features(matchups: pd.DataFrame, 
                         season: int = 2025,
                         week: Optional[int] = None) -> pd.DataFrame:
    """
    Add weather features to matchups DataFrame.
    
    Args:
        matchups: DataFrame with 'home', 'away', and optionally 'game_date' columns
        season: NFL season year
        week: NFL week number (optional, for estimating game dates)
    
    Returns:
        DataFrame with weather features added
    """
    df = matchups.copy()
    
    # If no game_date column, estimate from season and week
    if 'game_date' not in df.columns and week is not None:
        # Estimate game date (NFL season starts ~Sept 5, games on Sundays)
        season_start = datetime(season, 9, 5)
        # Find first Sunday
        while season_start.weekday() != 6:  # 6 = Sunday
            season_start += timedelta(days=1)
        
        # Add weeks
        estimated_date = season_start + timedelta(weeks=week-1)
        df['game_date'] = estimated_date
    
    # Fetch weather for each game
    weather_data = []
    
    for idx, row in df.iterrows():
        home_team = row['home']
        
        # Get game date
        if 'game_date' in row and pd.notna(row['game_date']):
            if isinstance(row['game_date'], str):
                game_date = datetime.fromisoformat(row['game_date'])
            else:
                game_date = row['game_date']
        else:
            # Use estimated date with 1pm ET kickoff
            game_date = df['game_date'].iloc[0] if 'game_date' in df.columns else datetime.now()
            game_date = game_date.replace(hour=13, minute=0, second=0)
        
        # Fetch weather
        weather = get_weather_for_game(home_team, game_date)
        binned = bin_weather_features(weather)
        weather_data.append(binned)
    
    # Add weather features to dataframe
    weather_df = pd.DataFrame(weather_data)
    
    # Prefix with 'weather_'
    weather_df.columns = [f'weather_{col}' if not col.startswith('weather_') else col 
                          for col in weather_df.columns]
    
    # Concatenate
    df = pd.concat([df, weather_df], axis=1)
    
    print(f"✅ Added weather features for {len(df)} games")
    
    return df


if __name__ == "__main__":
    # Test the module
    print("Testing weather features...")
    
    # Create sample matchups
    test_matchups = pd.DataFrame({
        'away': ['BUF', 'KC', 'GB'],
        'home': ['MIA', 'DEN', 'CHI'],
        'game_date': [
            datetime(2025, 10, 20, 13, 0),  # Oct 20, 1pm
            datetime(2025, 10, 20, 16, 0),  # Oct 20, 4pm
            datetime(2025, 10, 20, 13, 0),  # Oct 20, 1pm
        ]
    })
    
    # Add weather features
    enhanced = add_weather_features(test_matchups, season=2025)
    
    # Display key features
    weather_cols = [c for c in enhanced.columns if 'weather' in c]
    print("\nWeather features added:")
    for col in weather_cols:
        print(f"  - {col}")
    
    print("\nSample weather data:")
    display_cols = ['away', 'home', 'weather_temperature_f', 'weather_wind_speed_mph', 
                    'weather_precipitation_inches', 'weather_impact_score']
    print(enhanced[display_cols].to_string())

