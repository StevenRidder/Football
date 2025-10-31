#!/usr/bin/env python3
"""
Test Centered Game - KC vs BUF with Proper Market Centering

This is the CORRECT test that:
1. Runs raw simulation
2. Centers to market (mean anchored to Vegas)
3. Reports centered distributions
4. Measures CLV
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import (
    center_to_market, 
    validate_centering,
    get_betting_recommendation,
    print_centering_report
)


def test_kc_vs_buf_centered():
    """Test KC @ BUF with proper market centering."""
    
    print("\n" + "="*80)
    print("CENTERED GAME TEST: KC @ BUF 2024 Week 11")
    print("="*80 + "\n")
    
    # Game details
    away_team = 'KC'
    home_team = 'BUF'
    season = 2024
    week = 11
    
    # Market lines
    market_spread = -2.5  # BUF favored by 2.5
    market_total = 46.5
    
    # Actual result
    actual_away_score = 30
    actual_home_score = 21
    actual_spread = actual_away_score - actual_home_score  # +9
    actual_total = actual_away_score + actual_home_score  # 51
    
    print(f"📊 Game: {away_team} @ {home_team}")
    print(f"Market: {market_spread:+.1f} (BUF favored), Total: {market_total:.1f}")
    print(f"Actual: {away_team} {actual_away_score}, {home_team} {actual_home_score}")
    print(f"Actual Spread: {actual_spread:+.1f}, Total: {actual_total:.1f}")
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
    print("🎲 Running Monte Carlo (1,000 simulations)...")
    simulator = GameSimulator(away_profile, home_profile)
    
    n_sims = 1000
    spreads = []
    totals = []
    
    for i in range(n_sims):
        result = simulator.simulate_game()
        spreads.append(result['spread'])
        totals.append(result['total'])
        
        if (i + 1) % 250 == 0:
            print(f"   Completed {i+1}/{n_sims}...")
    
    spreads = np.array(spreads)
    totals = np.array(totals)
    
    print(f"   ✅ Complete\n")
    
    # Prepare for centering
    sim_results = {
        'spread_distribution': spreads,
        'total_distribution': totals,
        'spread_median': np.median(spreads),
        'total_median': np.median(totals),
    }
    
    print(f"📊 Raw Simulation Results:")
    print(f"   Spread: {sim_results['spread_median']:+.1f} ± {np.std(spreads):.1f}")
    print(f"   Total: {sim_results['total_median']:.1f} ± {np.std(totals):.1f}")
    print()
    
    # Center to market
    print("🎯 Centering to market...")
    centered = center_to_market(sim_results, market_spread, market_total)
    
    # Print centering report
    print_centering_report(centered)
    
    # Get betting recommendations
    print("\n" + "="*80)
    print("BETTING RECOMMENDATIONS")
    print("="*80 + "\n")
    
    recs = get_betting_recommendation(centered, edge_threshold_spread=1.5, edge_threshold_total=2.0)
    
    # Spread
    if recs['spread_bet']:
        if recs['spread_bet'] == 'away':
            print(f"✅ BET {away_team} {market_spread:+.1f}")
        else:
            print(f"✅ BET {home_team} {market_spread:+.1f}")
        print(f"   Edge: {recs['spread_edge']:+.1f} pts")
        print(f"   Confidence: {recs['spread_confidence']:.1%}")
        print(f"   CLV: {recs['spread_clv']:+.2f} pts")
    else:
        print(f"❌ NO SPREAD BET (edge < 1.5 pts)")
        print(f"   Edge: {recs['spread_edge']:+.1f} pts")
    
    print()
    
    # Total
    if recs['total_bet']:
        print(f"✅ BET {recs['total_bet'].upper()} {market_total:.1f}")
        print(f"   Edge: {recs['total_edge']:+.1f} pts")
        print(f"   Confidence: {recs['total_confidence']:.1%}")
        print(f"   CLV: {recs['total_clv']:+.2f} pts")
    else:
        print(f"❌ NO TOTAL BET (edge < 2.0 pts)")
        print(f"   Edge: {recs['total_edge']:+.1f} pts")
    
    # Compare to actual
    print("\n" + "="*80)
    print("COMPARISON TO ACTUAL")
    print("="*80 + "\n")
    
    # Spread
    if recs['spread_bet'] == 'away':
        spread_result = "WIN" if actual_spread > market_spread else "LOSS"
        print(f"Spread Bet: {away_team} {market_spread:+.1f}")
        print(f"   Result: {spread_result} (actual: {actual_spread:+.1f})")
    elif recs['spread_bet'] == 'home':
        spread_result = "WIN" if actual_spread < market_spread else "LOSS"
        print(f"Spread Bet: {home_team} {market_spread:+.1f}")
        print(f"   Result: {spread_result} (actual: {actual_spread:+.1f})")
    else:
        print(f"Spread Bet: None")
    
    print()
    
    # Total
    if recs['total_bet'] == 'over':
        total_result = "WIN" if actual_total > market_total else "LOSS"
        print(f"Total Bet: OVER {market_total:.1f}")
        print(f"   Result: {total_result} (actual: {actual_total:.1f})")
    elif recs['total_bet'] == 'under':
        total_result = "WIN" if actual_total < market_total else "LOSS"
        print(f"Total Bet: UNDER {market_total:.1f}")
        print(f"   Result: {total_result} (actual: {actual_total:.1f})")
    else:
        print(f"Total Bet: None")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    test_kc_vs_buf_centered()

