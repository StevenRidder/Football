"""
Minimal weather feature module for NFL totals betting.

Fetches stadium-specific wind and rain forecasts stamped at collection time.
Converts raw forecasts into simple bins for model features and betting rules.
"""

from __future__ import annotations
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional

# Stadium coordinates (lat, lon)
STADIUMS: Dict[str, Tuple[float, float]] = {
    "ARI": (33.5276, -112.2626),
    "ATL": (33.7555, -84.4009),
    "BAL": (39.2780, -76.6227),
    "BUF": (42.7738, -78.7870),
    "CAR": (35.2258, -80.8529),
    "CHI": (41.8623, -87.6167),
    "CIN": (39.0954, -84.5160),
    "CLE": (41.5061, -81.6995),
    "DAL": (32.7473, -97.0945),
    "DEN": (39.7439, -105.0201),
    "DET": (42.3400, -83.0456),
    "GB": (44.5013, -88.0622),
    "HOU": (29.6847, -95.4107),
    "IND": (39.7601, -86.1639),
    "JAX": (30.3240, -81.6373),
    "KC": (39.0489, -94.4839),
    "LAC": (33.9535, -118.3390),
    "LAR": (33.9535, -118.3390),
    "LA": (33.9535, -118.3390),
    "LV": (36.0909, -115.1833),
    "MIA": (25.9580, -80.2389),
    "MIN": (44.9738, -93.2577),
    "NE": (42.0909, -71.2643),
    "NO": (29.9511, -90.0812),
    "NYG": (40.8135, -74.0745),
    "NYJ": (40.8135, -74.0745),
    "PHI": (39.9008, -75.1675),
    "PIT": (40.4468, -80.0158),
    "SEA": (47.5952, -122.3316),
    "SF": (37.4032, -121.9698),
    "TB": (27.9759, -82.5033),
    "TEN": (36.1665, -86.7713),
    "WAS": (38.9076, -76.8645),
}


@dataclass
class WeatherSnapshot:
    """Timestamped weather snapshot for a game."""
    team_home: str
    team_away: str
    kickoff_utc: datetime
    collected_at_utc: datetime
    wind_kts: float
    wind_mph: float
    precip_mmph: float
    temp_f: float
    wind_bin: str
    precip_bin: str
    roof_flag: int


def _to_mph(kts: float) -> float:
    """Convert knots to mph."""
    return kts * 1.15078


def _bin_wind(mph: float) -> str:
    """Bin wind speed into meaningful categories."""
    if mph < 8:
        return "calm"
    if mph < 15:
        return "breeze"
    if mph < 20:
        return "windy"
    return "very_windy"


def _bin_precip(mm_per_hour: float) -> str:
    """Bin precipitation into meaningful categories."""
    if mm_per_hour < 0.1:
        return "dry"
    if mm_per_hour < 1.0:
        return "light"
    if mm_per_hour < 3.0:
        return "moderate"
    return "heavy"


def home_roof_flag(home: str) -> int:
    """
    Return 1 if stadium has roof/dome that reduces wind effect on totals.
    
    Roofed stadiums: DAL, DET, NO, MIN, ATL, LAR, LAC, LV
    Retractable (often closed in bad weather): HOU, IND, ARI
    """
    ROOFED = {"DAL", "DET", "NO", "MIN", "ATL", "LAR", "LAC", "LA", "LV", "HOU", "IND", "ARI"}
    return 1 if home in ROOFED else 0


def fetch_open_meteo(lat: float, lon: float, hour_utc: datetime) -> Optional[dict]:
    """
    Fetch weather forecast from Open-Meteo API (free, no key required).
    
    Args:
        lat: Latitude
        lon: Longitude
        hour_utc: Kickoff hour (UTC)
    
    Returns:
        JSON response or None if error
    """
    base = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,precipitation,temperature_2m",
        "start": hour_utc.strftime("%Y-%m-%dT%H:00"),
        "end": (hour_utc + timedelta(hours=3)).strftime("%Y-%m-%dT%H:00"),
        "timezone": "UTC",
    }
    
    try:
        r = requests.get(base, params=params, timeout=15)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        print(f"⚠️  Open-Meteo API error: {e}")
        return None


def get_weather_snapshot(
    home: str, away: str, kickoff_utc: datetime
) -> Optional[WeatherSnapshot]:
    """
    Get weather snapshot for a game at kickoff time.
    
    Args:
        home: Home team abbreviation
        away: Away team abbreviation
        kickoff_utc: Kickoff datetime (UTC)
    
    Returns:
        WeatherSnapshot or None if unavailable
    """
    if home not in STADIUMS:
        return None
    
    lat, lon = STADIUMS[home]
    data = fetch_open_meteo(
        lat, lon, kickoff_utc.replace(minute=0, second=0, microsecond=0)
    )
    
    if not data or "hourly" not in data:
        return None
    
    hrs = data["hourly"]["time"]
    winds = data["hourly"]["wind_speed_10m"]  # km/h (API returns km/h, not m/s!)
    precs = data["hourly"]["precipitation"]  # mm
    temps = data["hourly"]["temperature_2m"]  # C
    
    # Pick the forecast hour closest to kickoff
    idx = min(
        range(len(hrs)),
        key=lambda i: abs(
            datetime.fromisoformat(hrs[i]).replace(tzinfo=timezone.utc) - kickoff_utc
        ),
    )
    
    wind_kmh = float(winds[idx])
    wind_mph = wind_kmh * 0.621371  # km/h to mph (NOT m/s!)
    wind_mps = wind_kmh / 3.6  # km/h to m/s for backwards compat
    precip = float(precs[idx])
    temp_f = float(temps[idx]) * 9 / 5 + 32
    
    return WeatherSnapshot(
        team_home=home,
        team_away=away,
        kickoff_utc=kickoff_utc,
        collected_at_utc=datetime.now(timezone.utc),
        wind_kts=wind_mps * 1.94384,
        wind_mph=wind_mph,
        precip_mmph=precip,
        temp_f=temp_f,
        wind_bin=_bin_wind(wind_mph),
        precip_bin=_bin_precip(precip),
        roof_flag=home_roof_flag(home),
    )


if __name__ == "__main__":
    # Test the module
    print("Testing weather snapshot...")
    
    # Test game: BUF @ MIA, Sunday 1pm ET (18:00 UTC)
    kickoff = datetime(2025, 10, 26, 18, 0, tzinfo=timezone.utc)
    snapshot = get_weather_snapshot("MIA", "BUF", kickoff)
    
    if snapshot:
        print(f"\n✅ Weather snapshot for {snapshot.team_away} @ {snapshot.team_home}:")
        print(f"  Kickoff: {snapshot.kickoff_utc}")
        print(f"  Collected: {snapshot.collected_at_utc}")
        print(f"  Wind: {snapshot.wind_mph:.1f} mph ({snapshot.wind_bin})")
        print(f"  Precip: {snapshot.precip_mmph:.2f} mm/hr ({snapshot.precip_bin})")
        print(f"  Temp: {snapshot.temp_f:.1f}°F")
        print(f"  Roof: {'Yes' if snapshot.roof_flag else 'No'}")
    else:
        print("❌ Failed to fetch weather")

