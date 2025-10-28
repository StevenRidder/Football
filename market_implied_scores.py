"""
Convert market spreads and totals to implied scores.

This is the proper way to anchor predictions:
1. Start with market's implied score
2. Apply our adjustments (weather, injuries, etc.)
3. Compare adjusted score to market
4. Bet only when we have ≥2 point edge
"""

from typing import Tuple

def market_to_implied_score(spread_home: float, total: float) -> Tuple[float, float]:
    """
    Convert market spread and total to implied scores.
    
    Args:
        spread_home: Home team spread (negative = home favored, positive = away favored)
                    e.g., +7.5 means away favored by 7.5 (home is +7.5 underdog)
                    e.g., -7.5 means home favored by 7.5 (home is -7.5 favorite)
        total: Over/under total
    
    Returns:
        (away_score, home_score) tuple
    
    Example 1:
        BAL @ MIA: spread_home = +7.5 (BAL favored by 7.5), total = 50.0
        
        Solve:
        - Away - Home = 7.5  (BAL favored by 7.5)
        - Away + Home = 50.0
        
        Result: Away (BAL) = 28.75, Home (MIA) = 21.25
    
    Example 2:
        BAL @ MIA: spread_home = -7.5 (MIA favored by 7.5), total = 50.0
        
        Solve:
        - Home - Away = 7.5  (MIA favored by 7.5)
        - Away + Home = 50.0
        
        Result: Away (BAL) = 21.25, Home (MIA) = 28.75
    """
    # spread_home is from home's perspective
    # If positive (+7.5), home is underdog, away is favored
    # If negative (-7.5), home is favored, away is underdog
    
    # When spread_home is positive: Away - Home = spread_home
    # When spread_home is negative: Home - Away = abs(spread_home)
    
    # General formula:
    # Away - Home = spread_home (positive means away favored)
    # Away + Home = total
    
    # From algebra:
    # Away = (total + spread_home) / 2
    # Home = (total - spread_home) / 2
    
    away_score = (total + spread_home) / 2
    home_score = (total - spread_home) / 2
    
    return away_score, home_score


def implied_score_to_spread_total(away_score: float, home_score: float) -> Tuple[float, float]:
    """
    Convert scores back to spread and total.
    
    Args:
        away_score: Away team score
        home_score: Home team score
    
    Returns:
        (spread_home, total) tuple where spread_home is from home's perspective
        Positive = away favored, Negative = home favored
    
    Example:
        If away_score=29, home_score=21, then away wins by 8
        spread_home = away - home = 29 - 21 = +8 (away favored by 8)
    """
    spread_home = away_score - home_score  # Positive = away favored
    total = away_score + home_score
    
    return spread_home, total


if __name__ == "__main__":
    # Test with BAL @ MIA example
    print("=" * 60)
    print("Market Implied Score Calculator")
    print("=" * 60)
    
    # Example: BAL @ MIA
    # Market: MIA -7.5, Total 50.5
    spread_home = -7.5  # MIA favored
    total = 50.5
    
    away_score, home_score = market_to_implied_score(spread_home, total)
    
    print(f"\nExample: BAL @ MIA")
    print(f"Market Spread: MIA {spread_home:+.1f}")
    print(f"Market Total: {total:.1f}")
    print(f"\nImplied Score:")
    print(f"  BAL (away): {away_score:.1f}")
    print(f"  MIA (home): {home_score:.1f}")
    
    # Now apply adjustments
    print(f"\n" + "=" * 60)
    print("Adjustment Example:")
    print("=" * 60)
    
    # Say we have 36 mph wind = -3.0 points on total
    wind_adjustment = -3.0
    
    # Apply to both teams proportionally
    adjusted_away = away_score + (wind_adjustment / 2)
    adjusted_home = home_score + (wind_adjustment / 2)
    
    print(f"\nWeather Adjustment: {wind_adjustment:.1f} points (36 mph wind)")
    print(f"\nAdjusted Score:")
    print(f"  BAL (away): {adjusted_away:.1f}")
    print(f"  MIA (home): {adjusted_home:.1f}")
    
    # Convert back to spread/total
    adj_spread, adj_total = implied_score_to_spread_total(adjusted_away, adjusted_home)
    
    print(f"\nAdjusted Market:")
    print(f"  Spread: MIA {adj_spread:+.1f}")
    print(f"  Total: {adj_total:.1f}")
    
    # Calculate edge
    spread_edge = abs(spread_home - adj_spread)
    total_edge = abs(total - adj_total)
    
    print(f"\n" + "=" * 60)
    print("Betting Edge:")
    print("=" * 60)
    print(f"  Spread Edge: {spread_edge:.1f} points")
    print(f"  Total Edge: {total_edge:.1f} points")
    
    if total_edge >= 2.0:
        print(f"\n✅ BET UNDER {total:.1f} (Edge: {total_edge:.1f} points)")
    else:
        print(f"\n❌ NO BET (Edge < 2.0 points)")

