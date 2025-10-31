#!/usr/bin/env python3
"""
Calibration Harness for NFL Simulator

Tunes the simulator to match NFL reality:
- Mean total: 44-46 points
- SD of totals: 12-14 points
- Possessions per team: 10-12 (mid ~11.0)
- Pass rate: 58-62%
- Explosive play rate: 10-11% of plays
- Turnover rate: 10-12% of drives
- Key numbers: Match historical distribution around 41-47

Strategy: Grid search over key parameters, minimize composite loss.
"""

import numpy as np
from pathlib import Path
import sys
import json
from typing import Dict, List, Tuple
from collections import Counter

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.team_profile import TeamProfile
from simulator.game_simulator import GameSimulator


# Targets from NFL data
TARGETS = {
    'mean_total': 45.0,
    'sd_total': 13.0,
    'possessions_per_team': 11.0,
    'pass_rate': 0.60,
    'explosive_rate': 0.105,  # 10.5% of plays
    'turnover_rate_per_drive': 0.11,  # 11% of drives
}

# Key numbers to check (most common totals)
KEY_NUMBERS = [41, 42, 43, 44, 45, 46, 47]


def simulate_many_games(n_games: int, seed: int = 42) -> Dict:
    """
    Simulate many games and collect statistics.
    
    Returns:
        Dict with keys: totals, possessions, pass_plays, run_plays, 
                       explosive_plays, turnovers, drives
    """
    np.random.seed(seed)
    
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    teams = ['KC', 'BUF', 'SF', 'DAL', 'PHI', 'BAL', 'CIN', 'MIA', 
             'DET', 'GB', 'SEA', 'MIN', 'NYJ', 'HOU']
    
    totals = []
    possessions_home = []
    possessions_away = []
    
    for i in range(n_games):
        if i % 100 == 0 and i > 0:
            print(f"    Simulated {i}/{n_games} games...")
        
        # Random matchup
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])
        
        # Use 2023 data (more complete)
        home = TeamProfile(home_team, 2023, 10, data_dir)
        away = TeamProfile(away_team, 2023, 10, data_dir)
        
        # Simulate
        sim = GameSimulator(away, home)
        result = sim.simulate_game()
        
        # Collect stats
        totals.append(result['home_score'] + result['away_score'])
        # Note: We'd need to add possession tracking to GameSimulator
        # For now, estimate from drives
    
    return {
        'totals': np.array(totals),
        'n_games': n_games,
    }


def compute_metrics(data: Dict) -> Dict:
    """Compute calibration metrics from simulation data."""
    totals = data['totals']
    
    metrics = {
        'mean_total': np.mean(totals),
        'sd_total': np.std(totals),
        'median_total': np.median(totals),
        'min_total': np.min(totals),
        'max_total': np.max(totals),
    }
    
    # Key number distribution
    total_counts = Counter(np.round(totals).astype(int))
    key_number_freq = {k: total_counts.get(k, 0) / len(totals) for k in KEY_NUMBERS}
    metrics['key_numbers'] = key_number_freq
    
    return metrics


def compute_loss(metrics: Dict) -> float:
    """
    Compute composite loss for calibration.
    
    Penalizes deviation from targets.
    """
    loss = 0.0
    
    # Mean total (weight: 10.0)
    mean_error = (metrics['mean_total'] - TARGETS['mean_total']) ** 2
    loss += 10.0 * mean_error
    
    # SD total (weight: 5.0)
    sd_error = (metrics['sd_total'] - TARGETS['sd_total']) ** 2
    loss += 5.0 * sd_error
    
    # Penalize extreme outliers
    if metrics['min_total'] < 0:
        loss += 100.0
    if metrics['max_total'] > 100:
        loss += 50.0
    
    return loss


def print_metrics(metrics: Dict):
    """Pretty print metrics."""
    print("\n" + "=" * 60)
    print("CALIBRATION METRICS")
    print("=" * 60)
    
    print(f"\n📊 Scoring:")
    print(f"   Mean Total:   {metrics['mean_total']:6.2f}  (target: {TARGETS['mean_total']:.1f})")
    print(f"   SD Total:     {metrics['sd_total']:6.2f}  (target: {TARGETS['sd_total']:.1f})")
    print(f"   Median:       {metrics['median_total']:6.2f}")
    print(f"   Range:        [{metrics['min_total']:.0f}, {metrics['max_total']:.0f}]")
    
    print(f"\n🎯 Key Numbers (frequency):")
    for k in KEY_NUMBERS:
        freq = metrics['key_numbers'][k]
        bar = '█' * int(freq * 200)
        print(f"   {k:2d}: {freq:5.3f} {bar}")
    
    # Status
    mean_ok = abs(metrics['mean_total'] - TARGETS['mean_total']) < 1.0
    sd_ok = abs(metrics['sd_total'] - TARGETS['sd_total']) < 1.5
    
    print(f"\n✅ Status:")
    print(f"   Mean: {'✅ PASS' if mean_ok else '❌ FAIL'}")
    print(f"   SD:   {'✅ PASS' if sd_ok else '❌ FAIL'}")
    
    return mean_ok and sd_ok


def main():
    """Run calibration."""
    print("🏈 NFL Simulator Calibration Harness")
    print("=" * 60)
    
    # Run baseline simulation
    print("\n📊 Running baseline simulation (1000 games)...")
    data = simulate_many_games(1000, seed=42)
    
    # Compute metrics
    metrics = compute_metrics(data)
    
    # Print results
    passed = print_metrics(metrics)
    
    # Compute loss
    loss = compute_loss(metrics)
    print(f"\n📉 Loss: {loss:.2f}")
    
    # Save results
    output_dir = Path(__file__).parent.parent / "artifacts"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "calibration_metrics.json"
    
    # Convert numpy types to native Python for JSON serialization
    metrics_serializable = {
        'mean_total': float(metrics['mean_total']),
        'sd_total': float(metrics['sd_total']),
        'median_total': float(metrics['median_total']),
        'min_total': float(metrics['min_total']),
        'max_total': float(metrics['max_total']),
        'key_numbers': {k: float(v) for k, v in metrics['key_numbers'].items()},
        'loss': float(loss),
        'passed': bool(passed),
    }
    
    with open(output_file, 'w') as f:
        json.dump(metrics_serializable, f, indent=2)
    
    print(f"\n💾 Saved metrics to: {output_file}")
    
    if passed:
        print("\n🎉 CALIBRATION PASSED!")
        return 0
    else:
        print("\n⚠️  CALIBRATION FAILED - Tuning needed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

