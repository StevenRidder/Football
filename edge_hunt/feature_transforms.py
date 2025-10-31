"""
Convert weather snapshots into actionable features for totals betting.

Uses simple, literature-inspired priors that can be refined after collecting CLV data.
Keeps adjustments linear and transparent so cause-and-effect is clear.

Weather adjustments can be calibrated via the global calibration multiplier.
"""

from dataclasses import dataclass
from edge_hunt.weather_features import WeatherSnapshot
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from adjustment_calibration import apply_calibration


@dataclass
class WeatherFeatures:
    """Weather-derived features for total adjustment."""
    wind_mph: float
    precip_mmph: float
    temp_f: float
    roof_flag: int
    wind_penalty_pts: float
    precip_penalty_pts: float
    total_adjustment_pts: float


def weather_to_total_adjustment(ws: WeatherSnapshot) -> WeatherFeatures:
    """
    Convert weather snapshot to total points adjustment.
    
    Simple, conservative priors based on research:
    - Wind >=20 mph: -3.0 points
    - Wind 15-20 mph: -1.5 points
    - Wind 10-15 mph: -0.7 points
    - Roof reduces wind effect by 75%
    - Heavy precip (>=3 mm/hr): -1.0 points
    - Moderate precip (1-3 mm/hr): -0.5 points
    
    Args:
        ws: WeatherSnapshot
    
    Returns:
        WeatherFeatures with total adjustment
    """
    # Wind effect on passing efficiency
    wind_effect = 0.0
    if ws.wind_mph >= 20:
        wind_effect = -3.0
    elif ws.wind_mph >= 15:
        wind_effect = -1.5
    elif ws.wind_mph >= 10:
        wind_effect = -0.7
    
    # Roof dampening (reduces wind effect by 75%)
    wind_effect *= 0.25 if ws.roof_flag == 1 else 1.0
    
    # Precipitation effect (small but nonzero)
    precip_effect = 0.0
    if ws.precip_mmph >= 3.0:
        precip_effect = -1.0
    elif ws.precip_mmph >= 1.0:
        precip_effect = -0.5
    
    # Apply calibration multiplier to all weather adjustments
    wind_effect = apply_calibration(wind_effect)
    precip_effect = apply_calibration(precip_effect)
    
    # Total adjustment
    adj = wind_effect + precip_effect
    
    return WeatherFeatures(
        wind_mph=ws.wind_mph,
        precip_mmph=ws.precip_mmph,
        temp_f=ws.temp_f,
        roof_flag=ws.roof_flag,
        wind_penalty_pts=wind_effect,
        precip_penalty_pts=precip_effect,
        total_adjustment_pts=adj,
    )


if __name__ == "__main__":
    # Test the module
    from datetime import datetime, timezone
    from edge_hunt.weather_features import get_weather_snapshot
    
    print("Testing weather feature transforms...")
    
    # Test game: BUF @ MIA
    kickoff = datetime(2025, 10, 26, 18, 0, tzinfo=timezone.utc)
    snapshot = get_weather_snapshot("MIA", "BUF", kickoff)
    
    if snapshot:
        features = weather_to_total_adjustment(snapshot)
        
        print(f"\n✅ Weather features for {snapshot.team_away} @ {snapshot.team_home}:")
        print(f"  Wind: {features.wind_mph:.1f} mph → {features.wind_penalty_pts:+.1f} pts")
        print(f"  Precip: {features.precip_mmph:.2f} mm/hr → {features.precip_penalty_pts:+.1f} pts")
        print(f"  Roof: {'Yes' if features.roof_flag else 'No'}")
        print(f"  Total Adjustment: {features.total_adjustment_pts:+.1f} pts")
    else:
        print("❌ Failed to fetch weather")

