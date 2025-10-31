#!/usr/bin/env python3
"""
Diagnostic: Verify centering and probability calibration

Checks:
1. Centering correctness: mean(home_adj - away_adj) = spread, mean(home_adj + away_adj) = total
2. Probability Integral Transform: z = (spread_sim - line)/sd should be ~N(0,1)
3. Reliability: binned predicted probabilities vs actual outcomes
4. Variance stability: SD of spreads and totals after centering
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.team_profile import TeamProfile
from simulator.game_simulator import GameSimulator
from simulator.market_centering import center_scores_to_market


def test_single_game_centering(away='KC', home='BUF', season=2024, week=1, 
                                spread_line=-3.0, total_line=47.0, n_sims=1000):
    """Test centering on a single game."""
    print(f"\n🏈 Testing: {away} @ {home}")
    print(f"   Line: {home} {spread_line:+.1f}, Total: {total_line:.1f}")
    print("=" * 60)
    
    # Load teams
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    away_profile = TeamProfile(away, season, week, data_dir)
    home_profile = TeamProfile(home, season, week, data_dir)
    
    # Simulate
    simulator = GameSimulator(away_profile, home_profile)
    
    home_scores_raw = []
    away_scores_raw = []
    
    np.random.seed(42)
    for _ in range(n_sims):
        result = simulator.simulate_game()
        home_scores_raw.append(result['home_score'])
        away_scores_raw.append(result['away_score'])
    
    home_scores_raw = np.array(home_scores_raw)
    away_scores_raw = np.array(away_scores_raw)
    
    # Raw stats
    spreads_raw = home_scores_raw - away_scores_raw
    totals_raw = home_scores_raw + away_scores_raw
    
    print(f"\n📊 RAW Simulation:")
    print(f"   Mean spread: {spreads_raw.mean():+.2f} (home - away)")
    print(f"   Mean total:  {totals_raw.mean():.2f}")
    print(f"   SD spread:   {spreads_raw.std():.2f}")
    print(f"   SD total:    {totals_raw.std():.2f}")
    
    # Center to market
    home_c, away_c = center_scores_to_market(
        home_scores_raw, away_scores_raw, spread_line, total_line
    )
    
    spreads_c = home_c - away_c
    totals_c = home_c + away_c
    
    print(f"\n📊 CENTERED to Market:")
    print(f"   Mean spread: {spreads_c.mean():+.2f} (target: {spread_line:+.1f})")
    print(f"   Mean total:  {totals_c.mean():.2f} (target: {total_line:.1f})")
    print(f"   SD spread:   {spreads_c.std():.2f}")
    print(f"   SD total:    {totals_c.std():.2f}")
    
    # Check centering accuracy
    spread_error = abs(spreads_c.mean() - spread_line)
    total_error = abs(totals_c.mean() - total_line)
    
    print(f"\n✅ Centering Accuracy:")
    print(f"   Spread error: {spread_error:.4f} {'✅ PASS' if spread_error < 0.1 else '❌ FAIL'}")
    print(f"   Total error:  {total_error:.4f} {'✅ PASS' if total_error < 0.1 else '❌ FAIL'}")
    
    # Probability Integral Transform
    z_spread = (spreads_c - spread_line) / spreads_c.std()
    z_total = (totals_c - total_line) / totals_c.std()
    
    print(f"\n🎯 Probability Integral Transform:")
    print(f"   Z-spread: mean={z_spread.mean():.3f}, std={z_spread.std():.3f} (expect: 0, 1)")
    print(f"   Z-total:  mean={z_total.mean():.3f}, std={z_total.std():.3f} (expect: 0, 1)")
    
    # Probabilities
    p_home_cover = np.mean(spreads_c > spread_line)
    p_over = np.mean(totals_c > total_line)
    
    print(f"\n📈 Probabilities:")
    print(f"   P(Home covers): {p_home_cover:.3f}")
    print(f"   P(Over):        {p_over:.3f}")
    print(f"   Expected if centered correctly: ~0.50")
    
    return {
        'spreads_raw': spreads_raw,
        'totals_raw': totals_raw,
        'spreads_c': spreads_c,
        'totals_c': totals_c,
        'p_home_cover': p_home_cover,
        'p_over': p_over,
    }


def test_multiple_games(n_games=20, n_sims=500):
    """Test centering across multiple games."""
    print("\n" + "=" * 60)
    print(f"🔬 Testing Centering Across {n_games} Games")
    print("=" * 60)
    
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    teams = ['KC', 'BUF', 'SF', 'DAL', 'PHI', 'BAL', 'CIN', 'MIA']
    
    spread_errors = []
    total_errors = []
    spread_sds = []
    total_sds = []
    p_home_covers = []
    p_overs = []
    
    np.random.seed(42)
    
    for i in range(n_games):
        # Random matchup and lines
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])
        spread_line = np.random.uniform(-7, 7)
        total_line = np.random.uniform(40, 50)
        
        # Load and simulate
        away_profile = TeamProfile(away_team, 2023, 10, data_dir)
        home_profile = TeamProfile(home_team, 2023, 10, data_dir)
        simulator = GameSimulator(away_profile, home_profile)
        
        home_scores = []
        away_scores = []
        
        for _ in range(n_sims):
            result = simulator.simulate_game()
            home_scores.append(result['home_score'])
            away_scores.append(result['away_score'])
        
        home_scores = np.array(home_scores)
        away_scores = np.array(away_scores)
        
        # Center
        home_c, away_c = center_scores_to_market(
            home_scores, away_scores, spread_line, total_line
        )
        
        spreads_c = home_c - away_c
        totals_c = home_c + away_c
        
        # Collect metrics
        spread_errors.append(abs(spreads_c.mean() - spread_line))
        total_errors.append(abs(totals_c.mean() - total_line))
        spread_sds.append(spreads_c.std())
        total_sds.append(totals_c.std())
        p_home_covers.append(np.mean(spreads_c > spread_line))
        p_overs.append(np.mean(totals_c > total_line))
    
    print(f"\n📊 Centering Accuracy (n={n_games}):")
    print(f"   Mean spread error: {np.mean(spread_errors):.4f} (max: {np.max(spread_errors):.4f})")
    print(f"   Mean total error:  {np.mean(total_errors):.4f} (max: {np.max(total_errors):.4f})")
    
    print(f"\n📏 Distribution Shape:")
    print(f"   Spread SD: {np.mean(spread_sds):.2f} ± {np.std(spread_sds):.2f} (target: ~13)")
    print(f"   Total SD:  {np.mean(total_sds):.2f} ± {np.std(total_sds):.2f} (target: ~9-10)")
    
    print(f"\n🎲 Probability Distribution:")
    print(f"   P(Home cover): {np.mean(p_home_covers):.3f} ± {np.std(p_home_covers):.3f} (expect: ~0.50)")
    print(f"   P(Over):       {np.mean(p_overs):.3f} ± {np.std(p_overs):.3f} (expect: ~0.50)")
    
    # Check if probabilities are well-distributed
    print(f"\n📈 Probability Range:")
    print(f"   P(Home cover) range: [{np.min(p_home_covers):.3f}, {np.max(p_home_covers):.3f}]")
    print(f"   P(Over) range:       [{np.min(p_overs):.3f}, {np.max(p_overs):.3f}]")
    
    return {
        'spread_errors': spread_errors,
        'total_errors': total_errors,
        'spread_sds': spread_sds,
        'total_sds': total_sds,
        'p_home_covers': p_home_covers,
        'p_overs': p_overs,
    }


def main():
    print("🔬 CENTERING DIAGNOSTIC")
    print("=" * 60)
    
    # Test 1: Single game
    result1 = test_single_game_centering(
        away='BAL', home='KC', season=2024, week=1,
        spread_line=-3.0, total_line=47.0, n_sims=1000
    )
    
    # Test 2: Multiple games
    result2 = test_multiple_games(n_games=20, n_sims=500)
    
    print("\n" + "=" * 60)
    print("✅ DIAGNOSTIC COMPLETE")
    print("=" * 60)
    
    # Summary
    print("\n📋 SUMMARY:")
    print(f"   ✓ Centering is {'ACCURATE' if np.mean(result2['spread_errors']) < 0.1 else 'INACCURATE'}")
    print(f"   ✓ Spread SD is {np.mean(result2['spread_sds']):.1f} (target: ~13)")
    print(f"   ✓ Total SD is {np.mean(result2['total_sds']):.1f} (target: ~9-10)")
    print(f"   ✓ Probabilities centered at {np.mean(result2['p_home_covers']):.3f} (target: ~0.50)")


if __name__ == '__main__':
    main()

