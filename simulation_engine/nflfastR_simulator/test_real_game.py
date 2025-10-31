#!/usr/bin/env python3
"""
Test Real Game - KC vs BUF 2024 Week 11

Tests the full simulator pipeline:
1. Load team profiles (with PFF data)
2. Run simulation
3. Center to market
4. Compare to actual result
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_to_market, validate_centering


def test_kc_vs_buf():
    """Test KC @ BUF 2024 Week 11 (AFC Championship rematch)."""
    
    print("\n" + "="*80)
    print("REAL GAME TEST: KC @ BUF 2024 Week 11")
    print("="*80 + "\n")
    
    # Game details
    away_team = 'KC'
    home_team = 'BUF'
    season = 2024
    week = 11
    
    # Market lines (example - replace with actual)
    market_spread = -2.5  # BUF favored by 2.5
    market_total = 46.5
    
    # Actual result (if known)
    actual_away_score = 30  # Example
    actual_home_score = 21  # Example
    actual_spread = actual_away_score - actual_home_score  # +9 (KC wins)
    actual_total = actual_away_score + actual_home_score  # 51
    
    print(f"Market: {away_team} @ {home_team}")
    print(f"Spread: {market_spread} (BUF favored)")
    print(f"Total: {market_total}")
    print(f"Actual: {away_team} {actual_away_score}, {home_team} {actual_home_score}")
    print(f"Actual Spread: {actual_spread:+.1f}")
    print(f"Actual Total: {actual_total:.1f}")
    print()
    
    # Load team profiles
    print("📊 Loading team profiles...")
    data_dir = Path(__file__).parent / "data" / "nflfastR"
    
    away_profile = TeamProfile(away_team, season, week, data_dir)
    home_profile = TeamProfile(home_team, season, week, data_dir)
    
    print(f"   Away: {away_profile}")
    print(f"   Home: {home_profile}")
    print()
    
    # Run simulation
    print("🎲 Running simulation (1,000 games)...")
    simulator = GameSimulator(away_profile, home_profile)
    
    # Run Monte Carlo
    n_sims = 1000
    spreads = []
    totals = []
    
    for i in range(n_sims):
        result = simulator.simulate_game()
        spreads.append(result['spread'])
        totals.append(result['total'])
        
        if (i + 1) % 100 == 0:
            print(f"   Completed {i+1}/{n_sims} simulations...")
    
    # Convert to numpy arrays
    spreads = np.array(spreads)
    totals = np.array(totals)
    
    # Raw results
    raw_spread_mean = np.mean(spreads)
    raw_total_mean = np.mean(totals)
    raw_spread_std = np.std(spreads)
    raw_total_std = np.std(totals)
    
    print(f"   Raw spread: {raw_spread_mean:+.1f} ± {raw_spread_std:.1f}")
    print(f"   Raw total: {raw_total_mean:.1f} ± {raw_total_std:.1f}")
    print()
    
    # Center to market
    print("📍 Centering to market...")
    centered_spread = center_to_market(spreads, market_spread)
    centered_total = center_to_market(totals, market_total)
    
    # Validate centering
    validate_centering(centered_spread, market_spread, tolerance=0.2)
    validate_centering(centered_total, market_total, tolerance=0.2)
    
    centered_spread_mean = np.mean(centered_spread)
    centered_total_mean = np.mean(centered_total)
    centered_spread_std = np.std(centered_spread)
    centered_total_std = np.std(centered_total)
    
    print(f"   Centered spread: {centered_spread_mean:+.1f} ± {centered_spread_std:.1f}")
    print(f"   Centered total: {centered_total_mean:.1f} ± {centered_total_std:.1f}")
    print()
    
    # Analyze distribution
    print("="*80)
    print("DISTRIBUTION ANALYSIS")
    print("="*80 + "\n")
    
    # Spread distribution
    away_cover_pct = (centered_spread > market_spread).mean() * 100
    home_cover_pct = (centered_spread < market_spread).mean() * 100
    push_pct = (np.abs(centered_spread - market_spread) < 0.5).mean() * 100
    
    print(f"Spread ({market_spread:+.1f}):")
    print(f"   {away_team} covers: {away_cover_pct:.1f}%")
    print(f"   {home_team} covers: {home_cover_pct:.1f}%")
    print(f"   Push: {push_pct:.1f}%")
    print()
    
    # Total distribution
    over_pct = (centered_total > market_total).mean() * 100
    under_pct = (centered_total < market_total).mean() * 100
    
    print(f"Total ({market_total:.1f}):")
    print(f"   Over: {over_pct:.1f}%")
    print(f"   Under: {under_pct:.1f}%")
    print()
    
    # Compare to actual
    print("="*80)
    print("COMPARISON TO ACTUAL")
    print("="*80 + "\n")
    
    spread_error = abs(raw_spread_mean - actual_spread)
    total_error = abs(raw_total_mean - actual_total)
    
    print(f"Spread Error: {spread_error:.1f} pts")
    print(f"   Predicted: {raw_spread_mean:+.1f}")
    print(f"   Actual: {actual_spread:+.1f}")
    print()
    
    print(f"Total Error: {total_error:.1f} pts")
    print(f"   Predicted: {raw_total_mean:.1f}")
    print(f"   Actual: {actual_total:.1f}")
    print()
    
    # Betting recommendation
    print("="*80)
    print("BETTING RECOMMENDATION")
    print("="*80 + "\n")
    
    # Spread bet
    if abs(raw_spread_mean - market_spread) > 2.0:
        if raw_spread_mean > market_spread:
            print(f"✅ BET {away_team} +{abs(market_spread):.1f}")
            print(f"   Model: {away_team} {raw_spread_mean:+.1f}")
            print(f"   Market: {away_team} {market_spread:+.1f}")
            print(f"   Edge: {abs(raw_spread_mean - market_spread):.1f} pts")
        else:
            print(f"✅ BET {home_team} {market_spread:+.1f}")
            print(f"   Model: {home_team} {-raw_spread_mean:+.1f}")
            print(f"   Market: {home_team} {market_spread:+.1f}")
            print(f"   Edge: {abs(raw_spread_mean - market_spread):.1f} pts")
    else:
        print(f"❌ NO BET (edge < 2.0 pts)")
        print(f"   Model: {raw_spread_mean:+.1f}")
        print(f"   Market: {market_spread:+.1f}")
        print(f"   Edge: {abs(raw_spread_mean - market_spread):.1f} pts")
    
    print()
    
    # Total bet
    if abs(raw_total_mean - market_total) > 3.0:
        if raw_total_mean > market_total:
            print(f"✅ BET OVER {market_total:.1f}")
            print(f"   Model: {raw_total_mean:.1f}")
            print(f"   Market: {market_total:.1f}")
            print(f"   Edge: {abs(raw_total_mean - market_total):.1f} pts")
        else:
            print(f"✅ BET UNDER {market_total:.1f}")
            print(f"   Model: {raw_total_mean:.1f}")
            print(f"   Market: {market_total:.1f}")
            print(f"   Edge: {abs(raw_total_mean - market_total):.1f} pts")
    else:
        print(f"❌ NO BET (edge < 3.0 pts)")
        print(f"   Model: {raw_total_mean:.1f}")
        print(f"   Market: {market_total:.1f}")
        print(f"   Edge: {abs(raw_total_mean - market_total):.1f} pts")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    test_kc_vs_buf()

