"""
Apply weather adjustment to opening totals.

Anchors on the opener, fetches weather, and produces a weather-adjusted total
with full transparency for CLV tracking.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Any
from edge_hunt.weather_features import get_weather_snapshot
from edge_hunt.feature_transforms import weather_to_total_adjustment


def adjusted_total(
    open_total: float, home: str, away: str, kickoff_utc: datetime
) -> Dict[str, Any]:
    """
    Calculate weather-adjusted total for a game.
    
    Args:
        open_total: Opening total from market
        home: Home team abbreviation
        away: Away team abbreviation
        kickoff_utc: Kickoff datetime (UTC)
    
    Returns:
        Dictionary with:
        - ok: bool (success/failure)
        - open_total: float (original)
        - adj_total: float (weather-adjusted)
        - weather: dict (raw weather snapshot)
        - weather_features: dict (derived features)
        - reason: str (if failed)
    """
    ws = get_weather_snapshot(home, away, kickoff_utc)
    
    if not ws:
        return {"ok": False, "reason": "no_weather"}
    
    wf = weather_to_total_adjustment(ws)
    new_total = open_total + wf.total_adjustment_pts
    
    return {
        "ok": True,
        "home": home,
        "away": away,
        "kickoff_utc": kickoff_utc.isoformat(),
        "open_total": open_total,
        "adj_total": round(new_total, 1),
        "weather": asdict(ws),
        "weather_features": asdict(wf),
    }


if __name__ == "__main__":
    # Test the module
    print("Testing weather adjustment...")
    
    # Test game: BUF @ MIA, opening total 47.5
    kickoff = datetime(2025, 10, 26, 18, 0, tzinfo=timezone.utc)
    result = adjusted_total(47.5, "MIA", "BUF", kickoff)
    
    if result["ok"]:
        print(f"\n✅ Adjusted total for {result['away']} @ {result['home']}:")
        print(f"  Opening Total: {result['open_total']}")
        print(f"  Adjusted Total: {result['adj_total']}")
        print(f"  Adjustment: {result['adj_total'] - result['open_total']:+.1f} pts")
        print(f"\n  Weather:")
        wf = result["weather_features"]
        print(f"    Wind: {wf['wind_mph']:.1f} mph → {wf['wind_penalty_pts']:+.1f} pts")
        print(f"    Precip: {wf['precip_mmph']:.2f} mm/hr → {wf['precip_penalty_pts']:+.1f} pts")
    else:
        print(f"❌ Failed: {result['reason']}")

