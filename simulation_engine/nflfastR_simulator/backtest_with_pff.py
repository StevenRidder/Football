"""
Backtest with zero-mean PFF adjustments (Step 2)

This version:
1. Loads PFF weekly z-scores
2. Passes them to TeamProfile
3. Applies gated adjustments (±2-3% pressure, ±1-2% explosive, ±0.5-1 possession)
4. Compares log likelihood vs baseline
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import time

# Import from backtest_ultra_fast
from backtest_ultra_fast import (
    load_games_2024,
    center_scores_to_market,
    BREAKEVEN,
    EDGE_THRESHOLD,
)

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile

# Load PFF z-scores
PFF_ZSCORES = pd.read_csv("data/pff_raw/pff_weekly_zscores_2024.csv")
print(f"✅ Loaded {len(PFF_ZSCORES)} PFF z-score records")

def get_pff_zscores(season: int, week: int, home_team: str, away_team: str):
    """Get PFF z-scores for a game."""
    match = PFF_ZSCORES[
        (PFF_ZSCORES['season'] == season) &
        (PFF_ZSCORES['week'] == week) &
        (PFF_ZSCORES['home_team'] == home_team) &
        (PFF_ZSCORES['away_team'] == away_team)
    ]
    
    if len(match) == 0:
        return None, None
    
    row = match.iloc[0]
    return {
        'pressure_z': row['home_pass_mismatch_z'],
        'run_z': row['home_run_mismatch_z'],
    }, {
        'pressure_z': row['away_pass_mismatch_z'],
        'run_z': row['away_run_mismatch_z'],
    }

def simulate_one_game_with_pff(args):
    """Simulate one game with PFF adjustments."""
    idx, row, n_sims, total_games, use_pff = args
    
    try:
        # Extract game info
        season = int(row.get('season', 2024))
        week = int(row.get('week', 1))
        away = row.get('away_team', row.get('away'))
        home = row.get('home_team', row.get('home'))
        spread_line = float(row.get('spread_line', 0))
        total_line = float(row.get('total_line', 0))
        
        # Get PFF z-scores if using PFF
        home_pff_z, away_pff_z = None, None
        if use_pff:
            home_pff_z, away_pff_z = get_pff_zscores(season, week, home, away)
        
        # Create team profiles
        data_dir = Path(__file__).parent / "data" / "nflfastR"
        home_profile = TeamProfile(home, season, week, data_dir=data_dir)
        away_profile = TeamProfile(away, season, week, data_dir=data_dir)
        
        # Inject PFF z-scores
        if home_pff_z:
            home_profile.pff_pressure_z = home_pff_z['pressure_z']
            home_profile.pff_run_z = home_pff_z['run_z']
        if away_pff_z:
            away_profile.pff_pressure_z = away_pff_z['pressure_z']
            away_profile.pff_run_z = away_pff_z['run_z']
        
        # Create simulator
        simulator = GameSimulator(home_profile, away_profile)
        
        # Run simulations
        home_scores = []
        away_scores = []
        
        for sim_i in range(n_sims):
            sim_seed = (idx * 10000 + sim_i) * (2 if use_pff else 1)
            np.random.seed(int(sim_seed))
            
            result = simulator.simulate_game()
            
            home_scores.append(result['home_score'])
            away_scores.append(result['away_score'])
        
        # Center to market
        home_scores = np.asarray(home_scores)
        away_scores = np.asarray(away_scores)
        home_c, away_c = center_scores_to_market(
            home_scores, away_scores, spread_line, total_line
        )
        
        spreads_c = home_c - away_c
        totals_c = home_c + away_c
        
        # Calculate probabilities
        p_home_cover = np.mean(spreads_c > spread_line)
        p_over = np.mean(totals_c > total_line)
        
        # Actual outcomes
        actual_home = row.get('home_score', row.get('home_final'))
        actual_away = row.get('away_score', row.get('away_final'))
        
        if actual_home is None or actual_away is None:
            return None
        
        actual_spread = float(actual_home) - float(actual_away)
        actual_total = float(actual_home) + float(actual_away)
        
        # Determine outcomes (handle pushes)
        home_covered = 1.0 if actual_spread > spread_line else (0.0 if actual_spread < spread_line else None)
        over_hit = 1.0 if actual_total > total_line else (0.0 if actual_total < total_line else None)
        
        return {
            'game_id': row.get('game_id', f"{season}_{week:02d}_{away}_{home}"),
            'season': season,
            'week': week,
            'away_team': away,
            'home_team': home,
            'spread_line': spread_line,
            'total_line': total_line,
            'p_home_cover': p_home_cover,
            'p_over': p_over,
            'actual_spread': actual_spread,
            'actual_total': actual_total,
            'home_covered': home_covered,
            'over_hit': over_hit,
            'has_pff': home_pff_z is not None,
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Error on game {idx} ({away}@{home}): {e}")
        traceback.print_exc()
        return None

def run_backtest(use_pff=False, n_sims=50):
    """Run backtest with or without PFF."""
    print(f"\n{'='*60}")
    print(f"BACKTEST {'WITH' if use_pff else 'WITHOUT'} PFF")
    print(f"{'='*60}")
    
    games = load_games_2024()
    n_games = len(games)
    
    # Convert to list of dicts
    games_list = games.to_dict('records')
    
    # Prepare args
    args_list = [
        (idx, row, n_sims, n_games, use_pff)
        for idx, row in enumerate(games_list)
    ]
    
    # Run in parallel
    n_workers = min(8, os.cpu_count() or 1)
    chunksize = max(1, n_games // (n_workers * 4))
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        results = list(ex.map(simulate_one_game_with_pff, args_list, chunksize=chunksize))
    
    elapsed = time.time() - start_time
    
    # Filter out None results
    results = [r for r in results if r is not None]
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Calculate log likelihood
    eps = 1e-10
    
    # Spread log likelihood (excluding pushes)
    spread_valid = df[df['home_covered'].notna()].copy()
    if len(spread_valid) > 0:
        spread_ll = -np.mean(
            spread_valid['home_covered'] * np.log(spread_valid['p_home_cover'] + eps) +
            (1 - spread_valid['home_covered']) * np.log(1 - spread_valid['p_home_cover'] + eps)
        )
    else:
        spread_ll = np.nan
    
    # Total log likelihood (excluding pushes)
    total_valid = df[df['over_hit'].notna()].copy()
    if len(total_valid) > 0:
        total_ll = -np.mean(
            total_valid['over_hit'] * np.log(total_valid['p_over'] + eps) +
            (1 - total_valid['over_hit']) * np.log(1 - total_valid['p_over'] + eps)
        )
    else:
        total_ll = np.nan
    
    print(f"\n✅ Completed in {elapsed:.1f} seconds")
    print(f"\n📊 RESULTS:")
    print(f"   Games: {len(df)}")
    print(f"   Games with PFF: {df['has_pff'].sum()}")
    print(f"   Spread Log Loss: {spread_ll:.4f} (random=0.693)")
    print(f"   Total Log Loss: {total_ll:.4f} (random=0.693)")
    
    return df, spread_ll, total_ll

if __name__ == "__main__":
    # Run baseline (no PFF)
    df_baseline, spread_ll_baseline, total_ll_baseline = run_backtest(use_pff=False, n_sims=50)
    
    # Run with PFF
    df_pff, spread_ll_pff, total_ll_pff = run_backtest(use_pff=True, n_sims=50)
    
    # Compare
    print(f"\n{'='*60}")
    print("A/B TEST RESULTS")
    print(f"{'='*60}")
    print(f"\n📊 SPREAD:")
    print(f"   Baseline Log Loss: {spread_ll_baseline:.4f}")
    print(f"   PFF Log Loss: {spread_ll_pff:.4f}")
    print(f"   Improvement: {spread_ll_baseline - spread_ll_pff:.4f}")
    if spread_ll_pff < spread_ll_baseline:
        print(f"   ✅ PFF IMPROVES spread predictions")
    else:
        print(f"   ❌ PFF HURTS spread predictions")
    
    print(f"\n📊 TOTAL:")
    print(f"   Baseline Log Loss: {total_ll_baseline:.4f}")
    print(f"   PFF Log Loss: {total_ll_pff:.4f}")
    print(f"   Improvement: {total_ll_baseline - total_ll_pff:.4f}")
    if total_ll_pff < total_ll_baseline:
        print(f"   ✅ PFF IMPROVES total predictions")
    else:
        print(f"   ❌ PFF HURTS total predictions")
    
    # Save results
    df_baseline.to_csv("artifacts/backtest_baseline.csv", index=False)
    df_pff.to_csv("artifacts/backtest_with_pff.csv", index=False)
    print(f"\n💾 Saved results to artifacts/")

