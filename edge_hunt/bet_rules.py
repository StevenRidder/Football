"""
Simple betting rules for weather-adjusted totals.

Places $5 bets only when weather adjustment is meaningful (>=2 points edge).
Designed to be testable and fun with clear success metrics.
"""

from typing import Optional, Dict, Any


def should_bet_total(
    open_total: float, adj_total: float, min_edge_pts: float = 2.0
) -> Optional[Dict[str, Any]]:
    """
    Determine if we should bet the total based on weather adjustment.
    
    Logic:
    - If adj_total < open_total by >=2 pts → Bet UNDER (weather reduces scoring)
    - If adj_total > open_total by >=2 pts → Bet OVER (weather increases scoring)
    - Otherwise → No bet
    
    Args:
        open_total: Opening total from market
        adj_total: Weather-adjusted total
        min_edge_pts: Minimum edge required to bet (default: 2.0)
    
    Returns:
        Bet recommendation dict or None if no bet
        - side: "under" or "over"
        - edge_pts: float (absolute edge in points)
        - stake: float (bet size, default $5)
    """
    edge = open_total - adj_total  # Positive = bet UNDER, Negative = bet OVER
    
    if abs(edge) < min_edge_pts:
        return None
    
    side = "under" if edge > 0 else "over"
    
    return {"side": side, "edge_pts": abs(edge), "stake": 5.0}


if __name__ == "__main__":
    # Test the module
    print("Testing bet rules...")
    
    # Test case 1: High wind, bet UNDER
    print("\nTest 1: High wind game")
    print("  Opening total: 47.5")
    print("  Adjusted total: 44.5 (wind penalty -3.0)")
    bet = should_bet_total(47.5, 44.5, min_edge_pts=2.0)
    if bet:
        print(f"  ✅ Bet {bet['side'].upper()} with {bet['edge_pts']:.1f} pt edge, stake ${bet['stake']:.2f}")
    else:
        print("  ❌ No bet")
    
    # Test case 2: Marginal wind, no bet
    print("\nTest 2: Marginal wind game")
    print("  Opening total: 47.5")
    print("  Adjusted total: 46.8 (wind penalty -0.7)")
    bet = should_bet_total(47.5, 46.8, min_edge_pts=2.0)
    if bet:
        print(f"  ✅ Bet {bet['side'].upper()} with {bet['edge_pts']:.1f} pt edge, stake ${bet['stake']:.2f}")
    else:
        print("  ❌ No bet (edge < 2.0 pts)")
    
    # Test case 3: Calm conditions, no bet
    print("\nTest 3: Calm conditions")
    print("  Opening total: 47.5")
    print("  Adjusted total: 47.5 (no penalty)")
    bet = should_bet_total(47.5, 47.5, min_edge_pts=2.0)
    if bet:
        print(f"  ✅ Bet {bet['side'].upper()} with {bet['edge_pts']:.1f} pt edge, stake ${bet['stake']:.2f}")
    else:
        print("  ❌ No bet (no edge)")

