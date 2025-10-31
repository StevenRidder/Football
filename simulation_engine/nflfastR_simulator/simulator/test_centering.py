"""
Test market centering: Anchor simulator to closing lines.

This demonstrates the KEY insight:
- We don't try to beat Vegas on the mean
- We model the SHAPE: variance, tails, skew
- Edge comes from distribution, not point prediction
"""

import sys
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from team_profile import TeamProfile
from game_simulator import GameSimulator
from market_centering import (
    center_to_market,
    validate_centering,
    get_betting_recommendation,
    print_centering_report
)


def test_centering():
    """Test market centering on a single game."""
    print("="*80)
    print("TEST: MARKET CENTERING")
    print("="*80)
    print("\nKey insight: We anchor to Vegas mean, model the shape.")
    print("Edge comes from variance/tails, not mean prediction.")
    
    # Data directory
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    
    # Load team profiles (KC vs BUF, 2024 Week 1)
    print("\n📊 Loading team profiles...")
    home_team = TeamProfile('KC', 2024, 1, data_dir)
    away_team = TeamProfile('BUF', 2024, 1, data_dir)
    
    print(f"   Home: {home_team}")
    print(f"   Away: {away_team}")
    
    # Create simulator
    simulator = GameSimulator(home_team, away_team)
    
    # Run Monte Carlo (small sample for speed)
    print("\n🎲 Running Monte Carlo (1000 simulations)...")
    mc_results = simulator.simulate_monte_carlo(n_sims=1000)
    
    print(f"\n📊 Raw Simulation Results (BEFORE centering):")
    print(f"   {away_team.team} avg score: {mc_results['away_score_avg']:.1f}")
    print(f"   {home_team.team} avg score: {mc_results['home_score_avg']:.1f}")
    print(f"   Avg spread: {mc_results['spread_avg']:.1f}")
    print(f"   Avg total: {mc_results['total_avg']:.1f}")
    
    # Market lines (actual Week 1 2024 KC vs BUF)
    market_spread = -2.5  # KC -2.5
    market_total = 47.5
    
    print(f"\n🎯 Market Lines:")
    print(f"   Spread: KC {market_spread}")
    print(f"   Total: {market_total}")
    
    # Center to market
    print("\n🔧 Centering to market...")
    centered = center_to_market(mc_results, market_spread, market_total)
    
    # Print report
    print_centering_report(centered)
    
    # Get betting recommendations
    print("\n💰 Betting Recommendations (Based on Centered Distribution):")
    bets = get_betting_recommendation(centered)
    
    print(f"\n   Spread:")
    if bets['spread_bet']:
        print(f"      Bet: {bets['spread_bet'].upper()}")
        print(f"      Edge: {bets['spread_edge']:.1f} points")
        print(f"      Confidence: {bets['spread_confidence']:.1%}")
        print(f"      Estimated CLV: {bets['spread_clv']:.2f} points")
    else:
        print(f"      No bet (edge < 1.5 points)")
    
    print(f"\n   Total:")
    if bets['total_bet']:
        print(f"      Bet: {bets['total_bet'].upper()}")
        print(f"      Edge: {bets['total_edge']:.1f} points")
        print(f"      Confidence: {bets['total_confidence']:.1%}")
        print(f"      Estimated CLV: {bets['total_clv']:.2f} points")
    else:
        print(f"      No bet (edge < 2.0 points)")
    
    print("\n" + "="*80)
    print("✅ CENTERING TEST COMPLETE")
    print("="*80)
    
    print("\n📋 Key Takeaways:")
    print("   1. Raw sim had different mean than market")
    print("   2. Centering shifts distribution to match market mean")
    print("   3. We keep the SHAPE (variance, tails)")
    print("   4. Edge comes from shape, not mean")
    print("   5. Only bet if edge ≥ threshold")
    
    # Validation
    assert validate_centering(centered), "Centering validation failed"
    print("\n✅ Centering validation passed!")


if __name__ == "__main__":
    test_centering()

