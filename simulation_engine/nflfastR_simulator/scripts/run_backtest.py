#!/usr/bin/env python3
"""
Backtest Script - Reproducible, Auditable, Falsifiable

Usage:
    python scripts/run_backtest.py --year 2023 --output artifacts/run1 --seed 42
"""

import argparse
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_to_market, validate_centering


def compute_hash(filepath):
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_manifest(output_dir, git_sha, seed, year):
    """Create manifest.json with all metadata."""
    manifest = {
        "git_sha": git_sha,
        "timestamp": datetime.utcnow().isoformat(),
        "seed": seed,
        "year": year,
        "calibration_hash": compute_hash("simulator/calibration.json"),
        "data_snapshots": {
            "rolling_epa": "data/features/rolling_epa_2022_2025.csv",
        },
        "as_of": {
            "season": year,
            "week": 18
        }
    }
    
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return manifest


def gaussian_baseline(market_spread, market_total, n_sims=10000, seed=42):
    """
    Gaussian baseline centered on market with historical variance.
    
    This is the dumb baseline we must beat.
    """
    np.random.seed(seed)
    
    # Historical NFL variance
    spread_std = 13.5
    total_std = 10.5
    
    spread_samples = np.random.normal(market_spread, spread_std, n_sims)
    total_samples = np.random.normal(market_total, total_std, n_sims)
    
    return spread_samples, total_samples


def compute_clv(pick_line, closing_line, pick_side):
    """
    Compute Closing Line Value.
    
    CLV = (closing_line - pick_line) * sign(pick_side)
    
    Positive CLV means you got a better line than the close.
    """
    return (closing_line - pick_line) * pick_side


def compute_brier(probs, outcomes):
    """
    Compute Brier score.
    
    Lower is better. Perfect predictions = 0, random = 0.25.
    """
    return ((probs - outcomes) ** 2).mean()


def run_backtest(year, output_dir, seed, git_sha, holdout=False):
    """
    Run full backtest with all verification checks.
    
    Steps:
    1. Load games for year
    2. For each game:
       - Run Gaussian baseline
       - Run simulator
       - Center to market
       - Validate centering
       - Compute CLV
       - Compute Brier
    3. Aggregate results
    4. Generate artifacts
    """
    print(f"\n{'='*80}")
    print(f"BACKTEST: {year} ({'HOLDOUT' if holdout else 'DEV'})")
    print(f"Git SHA: {git_sha}")
    print(f"Seed: {seed}")
    print(f"Output: {output_dir}")
    print(f"{'='*80}\n")
    
    # Set seed for reproducibility
    np.random.seed(seed)
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create manifest
    manifest = create_manifest(output_dir, git_sha, seed, year)
    print(f"✅ Manifest created: {output_dir}/manifest.json\n")
    
    # Load games (placeholder - replace with actual data loading)
    print("📊 Loading games...")
    games = load_games(year)
    print(f"   Loaded {len(games)} games\n")
    
    # Results storage
    results = []
    distributions = []
    
    # Run backtest
    print("🎲 Running simulations...\n")
    for i, game in enumerate(games, 1):
        print(f"[{i}/{len(games)}] {game['away']} @ {game['home']}")
        
        # Gaussian baseline
        baseline_spread, baseline_total = gaussian_baseline(
            game['market_spread'], 
            game['market_total'],
            n_sims=10000,
            seed=seed + i
        )
        
        # Simulator (placeholder - replace with actual simulator)
        sim_spread, sim_total = run_simulator(game, seed=seed + i)
        
        # Center to market
        centered_spread = center_to_market(
            sim_spread, 
            game['market_spread']
        )
        centered_total = center_to_market(
            sim_total,
            game['market_total']
        )
        
        # Validate centering
        validate_centering(
            centered_spread,
            game['market_spread'],
            tolerance=0.2
        )
        validate_centering(
            centered_total,
            game['market_total'],
            tolerance=0.2
        )
        
        # Compute CLV (placeholder - need pick line and closing line)
        # For now, assume we picked at market and compare to close
        clv_spread = compute_clv(
            game['market_spread'],
            game['closing_spread'],
            pick_side=1  # Placeholder
        )
        
        # Compute Brier (placeholder - need actual outcomes)
        # For now, just store distributions
        
        # Store results
        results.append({
            'game_id': game['game_id'],
            'away': game['away'],
            'home': game['home'],
            'market_spread': game['market_spread'],
            'market_total': game['market_total'],
            'closing_spread': game['closing_spread'],
            'closing_total': game['closing_total'],
            'sim_spread_mean': centered_spread.mean(),
            'sim_total_mean': centered_total.mean(),
            'baseline_spread_mean': baseline_spread.mean(),
            'baseline_total_mean': baseline_total.mean(),
            'clv_spread': clv_spread,
        })
        
        distributions.append({
            'game_id': game['game_id'],
            'baseline_spread': baseline_spread,
            'baseline_total': baseline_total,
            'sim_spread': centered_spread,
            'sim_total': centered_total,
        })
    
    print(f"\n✅ Simulations complete\n")
    
    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_dir / "results.csv", index=False)
    print(f"✅ Results saved: {output_dir}/results.csv")
    
    # Save distributions (as parquet for efficiency)
    # distributions_df = pd.DataFrame(distributions)
    # distributions_df.to_parquet(output_dir / "distributions.parquet")
    # print(f"✅ Distributions saved: {output_dir}/distributions.parquet")
    
    # Compute summary stats
    summary = {
        'n_games': len(games),
        'mean_clv': results_df['clv_spread'].mean(),
        'centering_error_spread': (results_df['sim_spread_mean'] - results_df['market_spread']).abs().mean(),
        'centering_error_total': (results_df['sim_total_mean'] - results_df['market_total']).abs().mean(),
    }
    
    summary_path = output_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ Summary saved: {output_dir}/summary.json\n")
    
    # Print summary
    print(f"{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Games: {summary['n_games']}")
    print(f"Mean CLV: {summary['mean_clv']:.3f} pts")
    print(f"Centering Error (Spread): {summary['centering_error_spread']:.3f} pts")
    print(f"Centering Error (Total): {summary['centering_error_total']:.3f} pts")
    print(f"{'='*80}\n")
    
    return summary


def load_games(year):
    """
    Load games for backtest.
    
    Placeholder - replace with actual data loading.
    """
    # For now, return dummy data
    games = []
    for week in range(1, 18):
        for game_num in range(1, 16):
            games.append({
                'game_id': f"{year}_{week:02d}_{game_num:02d}",
                'season': year,
                'week': week,
                'away': 'AWAY',
                'home': 'HOME',
                'market_spread': -3.0,
                'market_total': 45.0,
                'closing_spread': -3.5,
                'closing_total': 44.5,
                'actual_spread': -7.0,
                'actual_total': 42.0,
            })
    
    return games


def run_simulator(game, seed):
    """
    Run simulator for a game.
    
    Placeholder - replace with actual simulator.
    """
    np.random.seed(seed)
    
    # For now, return random distributions
    spread = np.random.normal(game['market_spread'], 13.5, 10000)
    total = np.random.normal(game['market_total'], 10.5, 10000)
    
    return spread, total


def main():
    parser = argparse.ArgumentParser(description='Run backtest')
    parser.add_argument('--year', type=int, required=True, help='Year to backtest')
    parser.add_argument('--output', type=str, required=True, help='Output directory')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--git-sha', type=str, required=True, help='Git SHA')
    parser.add_argument('--holdout', action='store_true', help='Holdout test')
    
    args = parser.parse_args()
    
    run_backtest(
        year=args.year,
        output_dir=args.output,
        seed=args.seed,
        git_sha=args.git_sha,
        holdout=args.holdout
    )


if __name__ == '__main__':
    main()

