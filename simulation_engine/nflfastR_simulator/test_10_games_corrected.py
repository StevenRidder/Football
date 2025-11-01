#!/usr/bin/env python3
"""
Test simulator on 10 2025 games with CORRECTED actual scores and market calibration
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_calibration import calibrate_monte_carlo_results

# Test games with CORRECTED actual scores
# Format: (away_team, home_team, week, actual_home, actual_away, spread, total)
test_games = [
    ('MIA', 'IND', 1, 33, 8, 3.0, 45.0),      # IND wins 33-8 (IND -3, O/U 45)
    ('PIT', 'CIN', 5, 33, 31, 7.5, 47.5),     # CIN wins 33-31 (CIN -7.5, O/U 47.5) - CORRECTED
    ('DET', 'CIN', 6, 24, 37, 3.5, 46.5),     # DET wins 37-24 (CIN -3.5, O/U 46.5) - CORRECTED
    ('ATL', 'SF', 3, 20, 10, 7.5, 46.0),      # SF wins 20-10 (SF -7.5, O/U 46.0) - CORRECTED
    ('LAC', 'LV', 7, 20, 9, 3.0, 41.5),       # LV wins 20-9 (LV -3, O/U 41.5)
    ('SEA', 'PIT', 8, 31, 17, 3.0, 42.0),     # PIT wins 31-17 (PIT -3, O/U 42.0)
    ('TEN', 'LV', 2, 10, 20, 7.5, 40.5),      # TEN wins 20-10 (LV -7.5, O/U 40.5) - CHECK THIS
    ('NYJ', 'MIA', 8, 21, 27, 6.5, 45.5),     # NYJ wins 27-21 (MIA -6.5, O/U 45.5) - CHECK THIS
    ('WAS', 'GB', 8, 18, 27, 3.5, 47.5),      # WAS wins 27-18 (GB -3.5, O/U 47.5) - CHECK THIS
    ('HOU', 'JAX', 3, 10, 17, 7.5, 44.0),     # HOU wins 17-10 (JAX -7.5, O/U 44.0) - CHECK THIS
]

def main():
    print("="*100)
    print("TESTING 10 GAMES WITH CORRECTED ACTUAL SCORES + MARKET CALIBRATION")
    print("="*100)
    
    n_sims = 50  # Quick test
    results = []
    data_dir = Path(__file__).parent / 'data' / 'nflfastR'
    
    for away, home, week, actual_home, actual_away, spread, total in test_games:
        print(f"\n{'='*100}")
        print(f"Game: {away}@{home} (Week {week})")
        print(f"Actual: {home} {actual_home}, {away} {actual_away}")
        print(f"Market: {home} {spread:+.1f}, O/U {total}")
        print(f"{'='*100}")
        
        try:
            # Load team profiles
            home_profile = TeamProfile(home, 2025, week, data_dir)
            away_profile = TeamProfile(away, 2025, week, data_dir)
            
            # Run raw simulations
            home_scores = []
            away_scores = []
            
            for _ in range(n_sims):
                sim = GameSimulator(home_profile, away_profile)
                result = sim.simulate_game()
                home_scores.append(result['home_score'])
                away_scores.append(result['away_score'])
            
            # Apply market calibration
            cal_home, cal_away = calibrate_monte_carlo_results(
                home_scores=home_scores,
                away_scores=away_scores,
                market_spread=spread,
                market_total=total
            )
            
            # Calculate statistics
            raw_home_avg = np.mean(home_scores)
            raw_away_avg = np.mean(away_scores)
            cal_home_avg = np.mean(cal_home)
            cal_away_avg = np.mean(cal_away)
            
            # Determine winners
            actual_winner = home if actual_home > actual_away else away
            sim_winner = home if cal_home_avg > cal_away_avg else away
            winner_match = "✅" if actual_winner == sim_winner else "❌"
            
            # Spread analysis
            actual_spread = actual_home - actual_away
            sim_spread = cal_home_avg - cal_away_avg
            market_spread_actual = spread  # positive means home favored
            spread_diff = abs(sim_spread - actual_spread)
            
            # Total analysis
            actual_total = actual_home + actual_away
            sim_total = cal_home_avg + cal_away_avg
            total_diff = abs(sim_total - actual_total)
            
            print(f"\nRAW SIMULATION:")
            print(f"  {home}: {raw_home_avg:.1f} pts")
            print(f"  {away}: {raw_away_avg:.1f} pts")
            print(f"  Spread: {raw_home_avg - raw_away_avg:+.1f}")
            print(f"  Total: {raw_home_avg + raw_away_avg:.1f}")
            
            print(f"\nMARKET CALIBRATED:")
            print(f"  {home}: {cal_home_avg:.1f} pts")
            print(f"  {away}: {cal_away_avg:.1f} pts")
            print(f"  Spread: {sim_spread:+.1f} (actual: {actual_spread:+.1f}, diff: {spread_diff:.1f})")
            print(f"  Total: {sim_total:.1f} (actual: {actual_total:.1f}, diff: {total_diff:.1f})")
            
            print(f"\nWINNER: Predicted {sim_winner}, Actual {actual_winner} {winner_match}")
            
            results.append({
                'game': f"{away}@{home}",
                'actual_home': actual_home,
                'actual_away': actual_away,
                'sim_home': cal_home_avg,
                'sim_away': cal_away_avg,
                'actual_winner': actual_winner,
                'sim_winner': sim_winner,
                'winner_match': winner_match == "✅",
                'spread_error': spread_diff,
                'total_error': total_diff,
            })
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY OF RESULTS")
    print("="*100)
    
    print(f"\n{'Game':<15} {'Actual':<12} {'Simulated':<12} {'Winner':<8} {'Spread Err':<11} {'Total Err'}")
    print("-"*100)
    
    for r in results:
        actual_score = f"{r['actual_home']}-{r['actual_away']}"
        sim_score = f"{r['sim_home']:.1f}-{r['sim_away']:.1f}"
        match_icon = "✅" if r['winner_match'] else "❌"
        print(f"{r['game']:<15} {actual_score:<12} {sim_score:<12} {match_icon:<8} {r['spread_error']:<11.1f} {r['total_error']:.1f}")
    
    # Calculate overall accuracy
    winner_accuracy = sum(r['winner_match'] for r in results) / len(results) * 100
    avg_spread_error = np.mean([r['spread_error'] for r in results])
    avg_total_error = np.mean([r['total_error'] for r in results])
    
    print("\n" + "="*100)
    print(f"WINNER PREDICTION: {sum(r['winner_match'] for r in results)}/{len(results)} ({winner_accuracy:.1f}%)")
    print(f"AVG SPREAD ERROR: {avg_spread_error:.1f} points")
    print(f"AVG TOTAL ERROR: {avg_total_error:.1f} points")
    print("="*100)

if __name__ == '__main__':
    main()

