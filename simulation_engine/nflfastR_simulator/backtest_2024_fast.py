#!/usr/bin/env python3
"""
Ultra-fast backtest on 2024 weeks 1-8 with minimal simulations.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from multiprocessing import Pool, cpu_count
import nfl_data_py as nfl

from simulator.game_simulator import GameSimulator
from simulator.market_centering import center_scores_to_market


def load_games_with_odds(years=[2024]):
    """Load games with closing odds."""
    # Load schedule
    schedule = nfl.import_schedules(years)
    schedule = schedule[['game_id', 'season', 'week', 'away_team', 'home_team', 'gameday']].copy()
    
    # Load odds
    odds_file = Path(__file__).parent.parent.parent / "data" / "daily_odds_2022_2024_20251028.csv"
    odds = pd.read_csv(odds_file)
    
    # Team name mapping
    team_map = {
        'Los Angeles Rams': 'LAR', 'Los Angeles Chargers': 'LAC',
        'Washington Commanders': 'WAS', 'Washington Football Team': 'WAS', 'Washington Redskins': 'WAS',
        'Las Vegas Raiders': 'LV', 'Oakland Raiders': 'LV'
    }
    odds['home_team'] = odds['home_team'].replace(team_map)
    odds['away_team'] = odds['away_team'].replace(team_map)
    
    # Get closing lines (latest snapshot per game)
    odds['date'] = pd.to_datetime(odds['date'])
    closing = odds.sort_values('date').groupby(['season', 'week', 'home_team', 'away_team']).last().reset_index()
    closing = closing.rename(columns={'total': 'closing_total'})
    
    # Merge
    merged = schedule.merge(
        closing[['season', 'week', 'home_team', 'away_team', 'spread_line', 'closing_total']],
        on=['season', 'week', 'home_team', 'away_team'],
        how='inner'
    )
    
    merged['spread_line'] = pd.to_numeric(merged['spread_line'], errors='coerce')
    merged['closing_total'] = pd.to_numeric(merged['closing_total'], errors='coerce')
    merged = merged.dropna(subset=['spread_line', 'closing_total'])
    
    return merged


def simulate_single_game(args):
    """Simulate a single game."""
    idx, game, n_sims, total_games = args
    
    away = game['away_team']
    home = game['home_team']
    season = int(game['season'])
    week = int(game['week'])
    spread_line = float(game['spread_line'])
    total_line = float(game['closing_total'])
    
    # Progress every 10 games
    if (idx + 1) % 10 == 0:
        print(f"   [{idx+1}/{total_games}] {away}@{home}")
    
    try:
        sim = GameSimulator()
        
        # Run simulations
        home_scores = []
        away_scores = []
        for i in range(n_sims):
            seed = hash((season, week, home, away, i)) % (2**31)
            np.random.seed(seed)
            h, a = sim.simulate_game(home, away, season, week)
            home_scores.append(h)
            away_scores.append(a)
        
        # Center to market
        home_centered, away_centered = center_scores_to_market(
            np.array(home_scores),
            np.array(away_scores),
            spread_line,
            total_line
        )
        
        # Calculate probabilities
        BREAKEVEN = 0.524
        EDGE_THRESHOLD = 0.01
        
        spread_centered = home_centered - away_centered
        total_centered = home_centered + away_centered
        
        p_home_cover = np.mean(spread_centered > spread_line)
        p_over = np.mean(total_centered > total_line)
        
        # Betting decisions
        bet_spread = None
        bet_total = None
        
        if p_home_cover > BREAKEVEN + EDGE_THRESHOLD:
            bet_spread = 'HOME'
        elif (1 - p_home_cover) > BREAKEVEN + EDGE_THRESHOLD:
            bet_spread = 'AWAY'
        
        if p_over > BREAKEVEN + EDGE_THRESHOLD:
            bet_total = 'OVER'
        elif (1 - p_over) > BREAKEVEN + EDGE_THRESHOLD:
            bet_total = 'UNDER'
        
        return {
            'season': season,
            'week': week,
            'away_team': away,
            'home_team': home,
            'spread_line': spread_line,
            'total_line': total_line,
            'p_home_cover': p_home_cover,
            'p_over': p_over,
            'bet_spread': bet_spread,
            'bet_total': bet_total,
        }
    except Exception as e:
        print(f"   ERROR: {away}@{home} - {e}")
        return None


def print_summary(df):
    """Print betting summary."""
    print("\n" + "="*60)
    print("BETTING SUMMARY")
    print("="*60)
    
    spread_bets = df[df['bet_spread'].notna()]
    total_bets = df[df['bet_total'].notna()]
    
    print(f"\n📊 SPREAD BETS: {len(spread_bets)}/{len(df)} games")
    if len(spread_bets) > 0:
        print(f"   HOME: {(spread_bets['bet_spread'] == 'HOME').sum()}")
        print(f"   AWAY: {(spread_bets['bet_spread'] == 'AWAY').sum()}")
        print(f"   Avg edge: {spread_bets['p_home_cover'].apply(lambda p: max(p, 1-p) - 0.524).mean():.3f}")
    
    print(f"\n📊 TOTAL BETS: {len(total_bets)}/{len(df)} games")
    if len(total_bets) > 0:
        print(f"   OVER: {(total_bets['bet_total'] == 'OVER').sum()}")
        print(f"   UNDER: {(total_bets['bet_total'] == 'UNDER').sum()}")
        print(f"   Avg edge: {total_bets['p_over'].apply(lambda p: max(p, 1-p) - 0.524).mean():.3f}")
    
    print(f"\n📊 TOTAL RECOMMENDATIONS: {len(spread_bets) + len(total_bets)} bets")
    print("="*60 + "\n")


def main():
    """Run ultra-fast backtest on 2024 weeks 1-8."""
    
    print(f"📊 Loading 2024 season weeks 1-8...")
    games_df = load_games_with_odds(years=[2024])
    games_df = games_df[(games_df['week'] >= 1) & (games_df['week'] <= 8)].copy()
    print(f"   Found {len(games_df)} games\n")
    
    n_cores = cpu_count()
    n_sims = 50  # Minimal sims for speed
    
    print(f"🚀 Running on {n_cores} CPU cores")
    print(f"   {len(games_df)} games × {n_sims} sims = {len(games_df) * n_sims:,} total")
    print(f"   Target: < 2 minutes\n")
    
    # Prepare args
    total_games = len(games_df)
    args = [(i, games_df.iloc[i], n_sims, total_games) for i in range(total_games)]
    
    # Run in parallel
    print(f"Starting...\n")
    with Pool(n_cores) as pool:
        results = pool.map(simulate_single_game, args)
    
    # Filter and save
    results = [r for r in results if r is not None]
    predictions_df = pd.DataFrame(results)
    
    print(f"\n✅ Completed {len(predictions_df)} games")
    
    # Print summary
    print_summary(predictions_df)
    
    # Save
    output_file = Path(__file__).parent / "artifacts" / "backtest_2024_wk1-8.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_file, index=False)
    print(f"✅ Saved: {output_file}\n")


if __name__ == '__main__':
    main()

