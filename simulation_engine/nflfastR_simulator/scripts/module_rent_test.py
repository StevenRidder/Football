#!/usr/bin/env python3
"""
Module Rent Test - Make Each Module Pay CLV Rent

Tests three models:
1. Gaussian Baseline - Dumb model centered on Vegas
2. EPA-Only - Simulator without PFF
3. EPA+PFF - Simulator with PFF adjustments

Measures CLV (Closing Line Value) for each module.
A module "pays rent" if it adds ≥ +0.3 points of CLV.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_to_market


def gaussian_baseline(market_spread, market_total, n_sims=10000, seed=42):
    """
    Gaussian baseline - dumb model centered on Vegas.
    
    This is what we MUST beat to have an edge.
    """
    np.random.seed(seed)
    
    # Historical NFL variance
    spread_std = 13.5
    total_std = 10.5
    
    spread_samples = np.random.normal(market_spread, spread_std, n_sims)
    total_samples = np.random.normal(market_total, total_std, n_sims)
    
    return spread_samples, total_samples


def compute_clv(pick_spread, closing_spread, pick_side):
    """
    Compute Closing Line Value.
    
    CLV = (closing_spread - pick_spread) * sign(pick_side)
    
    Positive CLV means you got a better line than the close.
    """
    return (closing_spread - pick_spread) * pick_side


def run_module_test(games_df, module_name, use_pff=False, n_sims=1000):
    """
    Test a module and measure its CLV.
    
    Args:
        games_df: DataFrame with games to test
        module_name: Name of module being tested
        use_pff: Whether to use PFF adjustments
        n_sims: Number of simulations per game
    
    Returns:
        Dict with CLV metrics
    """
    print(f"\n{'='*80}")
    print(f"MODULE: {module_name}")
    print(f"{'='*80}\n")
    
    results = []
    
    for idx, game in games_df.iterrows():
        away = game['away_team']
        home = game['home_team']
        season = int(game['season'])
        week = int(game['week'])
        market_spread = float(game['market_spread'])
        closing_spread = float(game['closing_spread'])
        market_total = float(game['market_total'])
        
        print(f"[{idx+1}/{len(games_df)}] {away} @ {home} (W{week})")
        
        if module_name == "Gaussian Baseline":
            # Gaussian baseline
            spread_dist, total_dist = gaussian_baseline(
                market_spread, market_total, n_sims=n_sims
            )
            pick_spread = market_spread  # Pick at market
            
        else:
            # Run simulator
            try:
                # Load team profiles
                data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
                away_profile = TeamProfile(away, season, week, data_dir)
                home_profile = TeamProfile(home, season, week, data_dir)
                
                # Temporarily disable PFF if testing EPA-only
                if not use_pff:
                    away_profile.ol_grade = None
                    away_profile.dl_grade = None
                    home_profile.ol_grade = None
                    home_profile.dl_grade = None
                
                # Run simulation
                simulator = GameSimulator(away_profile, home_profile)
                results_sim = simulator.simulate_game(n_sims=n_sims)
                
                # Center to market
                spread_dist = center_to_market(
                    results_sim['spread'],
                    market_spread
                )
                
                pick_spread = np.median(spread_dist)
                
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
                continue
        
        # Compute CLV
        # Assume we pick the favorite if our spread is more favorable
        if abs(pick_spread - market_spread) < 0.5:
            # Too close to market, skip
            clv = 0.0
            pick_side = 0
        elif pick_spread < market_spread:
            # We think away team is better → pick away
            pick_side = 1
            clv = compute_clv(market_spread, closing_spread, pick_side)
        else:
            # We think home team is better → pick home
            pick_side = -1
            clv = compute_clv(market_spread, closing_spread, pick_side)
        
        results.append({
            'game_id': f"{season}_{week:02d}_{away}_{home}",
            'module': module_name,
            'pick_spread': pick_spread,
            'market_spread': market_spread,
            'closing_spread': closing_spread,
            'clv': clv,
            'pick_side': pick_side
        })
        
        print(f"  Pick: {pick_spread:.1f} | Market: {market_spread:.1f} | Close: {closing_spread:.1f} | CLV: {clv:+.2f}")
    
    # Summary
    results_df = pd.DataFrame(results)
    mean_clv = results_df['clv'].mean()
    n_bets = len(results_df[results_df['pick_side'] != 0])
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: {module_name}")
    print(f"{'='*80}")
    print(f"Games: {len(results_df)}")
    print(f"Bets: {n_bets}")
    print(f"Mean CLV: {mean_clv:+.3f} pts")
    print(f"{'='*80}\n")
    
    return {
        'module': module_name,
        'n_games': len(results_df),
        'n_bets': n_bets,
        'mean_clv': mean_clv,
        'results': results_df
    }


def main():
    print("\n" + "="*80)
    print("MODULE RENT TEST")
    print("="*80 + "\n")
    
    # Load sample games (placeholder - replace with actual data)
    print("📊 Loading games...")
    
    # For now, create dummy data
    games = []
    for week in range(1, 5):  # Test on 4 weeks
        for game_num in range(1, 5):  # 4 games per week
            games.append({
                'season': 2024,
                'week': week,
                'away_team': 'KC',
                'home_team': 'BUF',
                'market_spread': -3.0 + np.random.normal(0, 1),
                'closing_spread': -3.5 + np.random.normal(0, 1),
                'market_total': 45.0 + np.random.normal(0, 2),
            })
    
    games_df = pd.DataFrame(games)
    print(f"   Loaded {len(games_df)} games\n")
    
    # Test each module
    baseline_results = run_module_test(games_df, "Gaussian Baseline", use_pff=False, n_sims=1000)
    epa_results = run_module_test(games_df, "EPA-Only", use_pff=False, n_sims=1000)
    pff_results = run_module_test(games_df, "EPA+PFF", use_pff=True, n_sims=1000)
    
    # Compare
    print("\n" + "="*80)
    print("MODULE COMPARISON")
    print("="*80 + "\n")
    
    comparison = pd.DataFrame([
        {
            'Module': baseline_results['module'],
            'CLV': baseline_results['mean_clv'],
            'vs Baseline': 0.0,
            'Pays Rent?': 'N/A'
        },
        {
            'Module': epa_results['module'],
            'CLV': epa_results['mean_clv'],
            'vs Baseline': epa_results['mean_clv'] - baseline_results['mean_clv'],
            'Pays Rent?': '✅' if (epa_results['mean_clv'] - baseline_results['mean_clv']) >= 0.3 else '❌'
        },
        {
            'Module': pff_results['module'],
            'CLV': pff_results['mean_clv'],
            'vs Baseline': pff_results['mean_clv'] - baseline_results['mean_clv'],
            'Pays Rent?': '✅' if (pff_results['mean_clv'] - baseline_results['mean_clv']) >= 0.3 else '❌'
        }
    ])
    
    print(comparison.to_string(index=False))
    print("\n" + "="*80)
    
    # Decision
    print("\n🎯 DECISION:")
    if pff_results['mean_clv'] - epa_results['mean_clv'] >= 0.3:
        print("   ✅ PFF module PAYS RENT (+0.3 CLV over EPA-only)")
        print("   → Keep PFF in production")
    elif epa_results['mean_clv'] - baseline_results['mean_clv'] >= 0.3:
        print("   ⚠️  EPA-only PAYS RENT, but PFF does not add value")
        print("   → Use EPA-only, drop PFF")
    else:
        print("   ❌ NO MODULE BEATS BASELINE")
        print("   → Market is efficient, no edge found")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()

