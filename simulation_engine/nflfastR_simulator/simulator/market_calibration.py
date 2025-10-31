"""
Market-based score calibration.

Centers raw simulation results to market spread and total.
"""
import numpy as np


def calibrate_monte_carlo_results(home_scores: list,
                                   away_scores: list,
                                   market_spread: float = None,
                                   market_total: float = None,
                                   spread_weight: float = 0.7,
                                   total_weight: float = 0.7) -> tuple:
    """
    Calibrate Monte Carlo simulation results to market lines.
    
    Centers the distribution to market spread/total while preserving variance.
    
    Args:
        home_scores: List of home team scores from N simulations
        away_scores: List of away team scores from N simulations
        market_spread: Market spread (positive = home favored)
        market_total: Market over/under
        spread_weight: Weight for market spread (0-1)
        total_weight: Weight for market total (0-1)
    
    Returns:
        (calibrated_home_scores, calibrated_away_scores) as lists
    """
    # Calculate average raw predictions
    avg_raw_home = np.mean(home_scores)
    avg_raw_away = np.mean(away_scores)
    raw_total = avg_raw_home + avg_raw_away
    raw_spread = avg_raw_home - avg_raw_away
    
    # If no market data, return raw scores
    if market_spread is None and market_total is None:
        return home_scores, away_scores
    
    # Target spread (blend of raw and market)
    if market_spread is not None:
        target_spread = (1 - spread_weight) * raw_spread + spread_weight * market_spread
    else:
        target_spread = raw_spread
    
    # Target total (blend of raw and market)
    if market_total is not None:
        target_total = (1 - total_weight) * raw_total + total_weight * market_total
    else:
        target_total = raw_total
    
    # Solve for target means
    # home - away = target_spread
    # home + away = target_total
    target_home = (target_total + target_spread) / 2
    target_away = (target_total - target_spread) / 2
    
    # Apply shifts to center distribution
    home_shift = target_home - avg_raw_home
    away_shift = target_away - avg_raw_away
    
    calibrated_home = [max(0, h + home_shift) for h in home_scores]
    calibrated_away = [max(0, a + away_shift) for a in away_scores]
    
    return calibrated_home, calibrated_away

