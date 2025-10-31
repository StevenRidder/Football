"""
Quick test of the nflfastR play-by-play simulator.

Tests:
1. Load team profiles
2. Run single game simulation
3. Run Monte Carlo (100 sims for speed)
4. Check outputs are reasonable
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from team_profile import TeamProfile
from game_simulator import GameSimulator


def test_simulator():
    """Test the simulator on a single game."""
    print("="*80)
    print("TESTING nflfastR PLAY-BY-PLAY SIMULATOR")
    print("="*80)
    
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
    
    # Test single game
    print("\n🏈 Running single game simulation...")
    result = simulator.simulate_game()
    print(f"   Final Score: {away_team.team} {result['away_score']}, {home_team.team} {result['home_score']}")
    print(f"   Spread: {result['spread']} (positive = away wins)")
    print(f"   Total: {result['total']}")
    
    # Test Monte Carlo (small sample for speed)
    print("\n🎲 Running Monte Carlo (100 simulations)...")
    mc_results = simulator.simulate_monte_carlo(n_sims=100)
    
    print(f"\n📊 Results:")
    print(f"   {away_team.team} avg score: {mc_results['away_score_avg']:.1f}")
    print(f"   {home_team.team} avg score: {mc_results['home_score_avg']:.1f}")
    print(f"   Avg spread: {mc_results['spread_avg']:.1f}")
    print(f"   Avg total: {mc_results['total_avg']:.1f}")
    print(f"   {home_team.team} win prob: {mc_results['home_win_prob']:.1%}")
    
    # Test betting recommendations
    print("\n💰 Testing betting recommendations...")
    market_spread = -2.5  # KC -2.5
    market_total = 47.5
    
    bets = simulator.get_betting_recommendations(mc_results, market_spread, market_total)
    
    print(f"\n   Market: {home_team.team} {market_spread}, O/U {market_total}")
    print(f"   Model: {home_team.team} {mc_results['spread_median']:.1f}, O/U {mc_results['total_median']:.1f}")
    print(f"\n   Spread bet: {bets['spread_bet']} (edge: {bets['spread_edge']:.1f}, confidence: {bets['spread_confidence']:.1%})")
    print(f"   Total bet: {bets['total_bet']} (edge: {bets['total_edge']:.1f}, confidence: {bets['total_confidence']:.1%})")
    
    print("\n" + "="*80)
    print("✅ SIMULATOR TEST COMPLETE")
    print("="*80)
    
    # Sanity checks
    assert 0 <= result['home_score'] <= 70, "Home score out of range"
    assert 0 <= result['away_score'] <= 70, "Away score out of range"
    assert 20 <= mc_results['total_avg'] <= 70, "Average total out of range"
    assert 0 <= mc_results['home_win_prob'] <= 1, "Win probability out of range"
    
    print("\n✅ All sanity checks passed!")


if __name__ == "__main__":
    test_simulator()

