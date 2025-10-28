"""
Generate betting recommendations based on ADJUSTED scores vs MARKET lines.

This is the CORRECT way to bet:
1. Start with market-implied score (from spread + total)
2. Apply our adjustments (injuries, weather, etc.)
3. Convert adjusted score back to spread + total
4. Compare adjusted line to market line
5. Bet when we have ≥2 point edge

Example:
- Market: GB -12.5, Total 44.5 → Implied: GB 29, CAR 16
- Adjusted: GB 27, CAR 15 → New line: GB -12, Total 42
- Spread edge: 0.5 (too small, SKIP)
- Total edge: 2.5 (good, BET UNDER 44.5)
"""

import pandas as pd
import numpy as np
from typing import Tuple


def generate_adjusted_recommendations(
    df: pd.DataFrame,
    min_spread_edge: float = 2.0,
    min_total_edge: float = 2.0
) -> pd.DataFrame:
    """
    Generate betting recommendations based on ADJUSTED vs MARKET comparison.
    
    Args:
        df: DataFrame with columns:
            - market_spread (home-based, negative = home favored)
            - market_total
            - adjusted_spread (from adjusted scores)
            - adjusted_total (from adjusted scores)
            - away, home (team names)
        min_spread_edge: Minimum edge in points to recommend spread bet
        min_total_edge: Minimum edge in points to recommend total bet
    
    Returns:
        DataFrame with added columns:
            - spread_edge_pts: Our edge in points on spread
            - total_edge_pts: Our edge in points on total
            - Rec_spread: Spread recommendation
            - Rec_total: Total recommendation
            - Best_bet: Best play for this game
    """
    df = df.copy()
    
    # Map column names (handle both formats)
    market_spread_col = 'market_spread' if 'market_spread' in df.columns else 'Spread used (home-)'
    market_total_col = 'market_total' if 'market_total' in df.columns else 'Total used'
    
    # Calculate edges (positive = we think favorite will cover by more)
    df['spread_edge_pts'] = df[market_spread_col] - df['adjusted_spread']
    df['total_edge_pts'] = df[market_total_col] - df['adjusted_total']
    
    recommendations_spread = []
    recommendations_total = []
    best_bets = []
    
    for _, row in df.iterrows():
        away = row['away']
        home = row['home']
        market_spread = row[market_spread_col]
        market_total = row[market_total_col]
        spread_edge = row['spread_edge_pts']
        total_edge = row['total_edge_pts']
        
        # === SPREAD RECOMMENDATION ===
        if abs(spread_edge) >= min_spread_edge:
            # Determine which side to bet
            if spread_edge > 0:
                # Market spread is MORE negative (home more favored) than our adjusted
                # We think home will cover by LESS than market thinks
                # So bet the DOG (away team)
                team = away
                line = -market_spread  # Away gets positive line
                rec_spread = f"BET {team} {line:+.1f} (Edge: {abs(spread_edge):.1f} pts)"
            else:
                # Market spread is LESS negative (home less favored) than our adjusted
                # We think home will cover by MORE than market thinks
                # So bet the FAVORITE (home team)
                team = home
                line = market_spread
                rec_spread = f"BET {team} {line:+.1f} (Edge: {abs(spread_edge):.1f} pts)"
        else:
            rec_spread = "SKIP"
        
        recommendations_spread.append(rec_spread)
        
        # === TOTAL RECOMMENDATION ===
        if abs(total_edge) >= min_total_edge:
            # Determine over/under
            if total_edge > 0:
                # Market total is HIGHER than our adjusted total
                # We think the game will score LESS
                # So bet UNDER
                side = "UNDER"
                rec_total = f"BET {side} {market_total:.1f} (Edge: {abs(total_edge):.1f} pts)"
            else:
                # Market total is LOWER than our adjusted total
                # We think the game will score MORE
                # So bet OVER
                side = "OVER"
                rec_total = f"BET {side} {market_total:.1f} (Edge: {abs(total_edge):.1f} pts)"
        else:
            rec_total = "SKIP"
        
        recommendations_total.append(rec_total)
        
        # === BEST BET ===
        if abs(spread_edge) >= min_spread_edge and abs(total_edge) >= min_total_edge:
            # Both have edge - pick the bigger one
            if abs(spread_edge) > abs(total_edge):
                best_bets.append(f"SPREAD: {rec_spread}")
            else:
                best_bets.append(f"TOTAL: {rec_total}")
        elif abs(spread_edge) >= min_spread_edge:
            best_bets.append(f"SPREAD: {rec_spread}")
        elif abs(total_edge) >= min_total_edge:
            best_bets.append(f"TOTAL: {rec_total}")
        else:
            best_bets.append("NO PLAY")
    
    df['Rec_spread'] = recommendations_spread
    df['Rec_total'] = recommendations_total
    df['Best_bet'] = best_bets
    
    return df


if __name__ == "__main__":
    # Test with CAR @ GB example
    test_data = {
        'away': ['CAR'],
        'home': ['GB'],
        'market_spread': [-12.5],  # GB -12.5
        'market_total': [44.5],
        'adjusted_spread': [-12.0],  # GB -12 (from 27-15 = 12)
        'adjusted_total': [42.0],  # 27 + 15 = 42
    }
    
    df = pd.DataFrame(test_data)
    result = generate_adjusted_recommendations(df)
    
    print("=" * 70)
    print("CAR @ GB Example")
    print("=" * 70)
    print(f"Market: GB {result['market_spread'].iloc[0]:+.1f}, Total {result['market_total'].iloc[0]:.1f}")
    print(f"Adjusted: GB {result['adjusted_spread'].iloc[0]:+.1f}, Total {result['adjusted_total'].iloc[0]:.1f}")
    print(f"Spread Edge: {result['spread_edge_pts'].iloc[0]:.1f} pts")
    print(f"Total Edge: {result['total_edge_pts'].iloc[0]:.1f} pts")
    print()
    print(f"Spread Rec: {result['Rec_spread'].iloc[0]}")
    print(f"Total Rec: {result['Rec_total'].iloc[0]}")
    print(f"Best Bet: {result['Best_bet'].iloc[0]}")
    print()
    print("✅ Should recommend: BET UNDER 44.5 (Edge: 2.5 pts)")
    print("✅ Should skip spread (edge only 0.5 pts)")

