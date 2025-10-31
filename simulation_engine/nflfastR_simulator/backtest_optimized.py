"""
Optimized backtest with:
1. More simulations (200 instead of 50)
2. Separate thresholds for spreads vs totals
3. Performance tracking by bet type
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Import everything from ultra_fast
from backtest_ultra_fast import *

# Override simulation parameters
N_SIMS = 200  # More stable probabilities
SPREAD_EDGE_THRESHOLD = 0.035  # 3.5% for spreads (tighter market)
TOTAL_EDGE_THRESHOLD = 0.025   # 2.5% for totals (proven to work)

def simulate_one_game_optimized(args):
    """Enhanced version with separate thresholds."""
    idx, row, n_sims, total_games = args
    
    try:
        season = int(row.get('season', 2024))
        week = int(row.get('week', 1))
        away = row.get('away_team', row.get('away'))
        home = row.get('home_team', row.get('home'))
        spread_line = float(row.get('spread_line', 0))
        total_line = float(row.get('total_line', 0))
        
        # Create team profiles
        data_dir = Path(__file__).parent / "data" / "nflfastR"
        home_profile = TeamProfile(home, season, week, data_dir=data_dir)
        away_profile = TeamProfile(away, season, week, data_dir=data_dir)
        
        # Create simulator
        simulator = GameSimulator(home_profile, away_profile)
        
        # Run simulations
        home_scores = []
        away_scores = []
        
        for sim_i in range(n_sims):
            sim_seed = idx * 10000 + sim_i
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
        
        spread_sd = spreads_c.std()
        total_sd = totals_c.std()
        
        # Validate centering
        assert abs(spreads_c.mean() - spread_line) < 0.25, f"Spread centering failed"
        assert abs(totals_c.mean() - total_line) < 0.25, f"Total centering failed"
        
        # Calculate probabilities
        p_home_cover = np.mean(spreads_c > spread_line)
        p_over = np.mean(totals_c > total_line)
        
        # Betting decisions with SEPARATE thresholds
        bet_spread = 'HOME' if p_home_cover > (BREAKEVEN + SPREAD_EDGE_THRESHOLD) else \
                     'AWAY' if p_home_cover < (1 - BREAKEVEN - SPREAD_EDGE_THRESHOLD) else None
        bet_total = 'OVER' if p_over > (BREAKEVEN + TOTAL_EDGE_THRESHOLD) else \
                    'UNDER' if p_over < (1 - BREAKEVEN - TOTAL_EDGE_THRESHOLD) else None
        
        return {
            'game_id': row.get('game_id', f"{season}_{week:02d}_{away}_{home}"),
            'season': season,
            'week': week,
            'away_team': away,
            'home_team': home,
            'spread_line': spread_line,
            'total_line': total_line,
            'spread_mean': spreads_c.mean(),
            'total_mean': totals_c.mean(),
            'p_home_cover': p_home_cover,
            'p_over': p_over,
            'bet_spread': bet_spread,
            'bet_total': bet_total,
            'actual_home_score': row.get('home_score', row.get('home_final')),
            'actual_away_score': row.get('away_score', row.get('away_final')),
            'spread_sd': spread_sd,
            'total_sd': total_sd,
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Error on game {idx} ({away}@{home}): {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("OPTIMIZED BACKTEST")
    print(f"{'='*60}")
    print(f"Simulations per game: {N_SIMS}")
    print(f"Spread edge threshold: {SPREAD_EDGE_THRESHOLD*100:.1f}%")
    print(f"Total edge threshold: {TOTAL_EDGE_THRESHOLD*100:.1f}%")
    print(f"{'='*60}\n")
    
    games = load_games_2024()
    n_games = len(games)
    
    # Convert to list of dicts
    games_list = games.to_dict('records')
    
    # Prepare args
    args_list = [
        (idx, row, N_SIMS, n_games)
        for idx, row in enumerate(games_list)
    ]
    
    # Run in parallel
    n_workers = min(8, os.cpu_count() or 1)
    chunksize = max(1, n_games // (n_workers * 4))
    
    print(f"🚀 Running {n_games} games × {N_SIMS} sims = {n_games * N_SIMS:,} total")
    print(f"   Using {n_workers} CPU cores\n")
    print(f"   Chunksize: {chunksize}\n\n")
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        results = list(ex.map(simulate_one_game_optimized, args_list, chunksize=chunksize))
    
    print(f"\n   Completed all {n_games} games\n")
    
    elapsed = time.time() - start_time
    print(f"✅ Completed in {elapsed:.1f} seconds\n")
    
    # Filter out None results
    results = [r for r in results if r is not None]
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Grade bets
    df = grade_bets(df)
    
    # Print summary
    print_summary(df)
    
    # Save results
    output_file = Path("artifacts/backtest_optimized.csv")
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved to: {output_file}")
    
    # Additional analysis
    print(f"\n{'='*60}")
    print("EDGE ANALYSIS")
    print(f"{'='*60}\n")
    
    spread_bets = df[df['bet_spread'].notna()]
    total_bets = df[df['bet_total'].notna()]
    
    if len(spread_bets) > 0:
        avg_spread_edge = spread_bets.apply(
            lambda r: abs(r['p_home_cover'] - 0.5) if r['bet_spread'] == 'HOME' 
                     else abs((1 - r['p_home_cover']) - 0.5),
            axis=1
        ).mean()
        print(f"📊 SPREAD BETS:")
        print(f"   Average edge: {avg_spread_edge*100:.2f}%")
        print(f"   Threshold: {SPREAD_EDGE_THRESHOLD*100:.1f}%")
    
    if len(total_bets) > 0:
        avg_total_edge = total_bets.apply(
            lambda r: abs(r['p_over'] - 0.5) if r['bet_total'] == 'OVER'
                     else abs((1 - r['p_over']) - 0.5),
            axis=1
        ).mean()
        print(f"\n📊 TOTAL BETS:")
        print(f"   Average edge: {avg_total_edge*100:.2f}%")
        print(f"   Threshold: {TOTAL_EDGE_THRESHOLD*100:.1f}%")
    
    print(f"\n{'='*60}")

