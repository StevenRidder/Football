"""Quick backtest on 5 games to validate everything works"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
import nfl_data_py as nfl

# Import centering function
from backtest_ultra_fast import center_scores_to_market

def load_games_2025():
    """Load 2025 games from nflfastR - matches backtest_ultra_fast.py logic."""
    print("📊 Loading 2025 games...")
    
    # Use same logic as backtest_ultra_fast.py
    from backtest_ultra_fast import load_games_2025 as load_2025
    games = load_2025()
    
    print(f"   Found {len(games)} completed games")
    return games

def simulate_one_game(row, n_sims=100):
    """Simulate a single game."""
    try:
        data_dir = Path("data/nflfastR")
        
        home_team = row['home_team']
        away_team = row['away_team']
        season = row['season']
        week = row['week']
        spread_line = row['spread_line']
        total_line = row.get('closing_total', row.get('total_line', 45.0))  # Support both column names
        
        # Create profiles (set debug=True to see data loading details)
        home_profile = TeamProfile(home_team, season, week, data_dir=data_dir, debug=False)
        away_profile = TeamProfile(away_team, season, week, data_dir=data_dir, debug=False)
        
        # Simulate
        simulator = GameSimulator(home_profile, away_profile)
        home_scores = []
        away_scores = []
        
        for i in range(n_sims):
            np.random.seed(42 + i)
            result = simulator.simulate_game()
            home_scores.append(result['home_score'])
            away_scores.append(result['away_score'])
        
        home_scores = np.array(home_scores)
        away_scores = np.array(away_scores)
        
        # Center to market
        home_centered, away_centered = center_scores_to_market(
            home_scores, away_scores, spread_line, total_line
        )
        spreads_c = home_centered - away_centered
        totals_c = home_centered + away_centered
        
        # Probabilities
        p_home_cover = np.mean(spreads_c > spread_line)
        p_over = np.mean(totals_c > total_line)
        
        # Actual results
        actual_home = row['home_score']
        actual_away = row['away_score']
        actual_spread = actual_home - actual_away
        actual_total = actual_home + actual_away
        
        home_covered = (actual_spread > spread_line)
        over_hit = (actual_total > total_line)
        
        return {
            'game_id': row['game_id'],
            'home_team': home_team,
            'away_team': away_team,
            'spread_line': spread_line,
            'total_line': total_line,
            'actual_home': actual_home,
            'actual_away': actual_away,
            'actual_spread': actual_spread,
            'actual_total': actual_total,
            'p_home_cover': p_home_cover,
            'p_over': p_over,
            'home_covered': home_covered,
            'over_hit': over_hit,
            'spread_sd': spreads_c.std(),
            'total_sd': totals_c.std(),
        }
    except Exception as e:
        print(f"❌ Error simulating {row.get('game_id', 'unknown')}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("="*80)
    print("QUICK BACKTEST - 5 GAMES")
    print("="*80)
    
    # Load games
    games = load_games_2025()
    games = games.head(5).copy()
    
    print(f"\n🎮 Simulating {len(games)} games...")
    
    results = []
    for idx, row in games.iterrows():
        print(f"\n  Game {idx+1}/{len(games)}: {row['away_team']} @ {row['home_team']} (W{row['week']})")
        result = simulate_one_game(row, n_sims=100)
        if result:
            results.append(result)
            print(f"    ✅ Predicted: Home cover={result['p_home_cover']:.1%}, Over={result['p_over']:.1%}")
            print(f"    ✅ Actual: Home covered={result['home_covered']}, Over hit={result['over_hit']}")
    
    if results:
        df = pd.DataFrame(results)
        
        print("\n" + "="*80)
        print("BACKTEST RESULTS")
        print("="*80)
        
        # Spread bets (bet if p > 0.5238)
        spread_bets = df[df['p_home_cover'].notna()].copy()
        if len(spread_bets) > 0:
            spread_bets['bet_home'] = spread_bets['p_home_cover'] > 0.5238
            spread_bets['won'] = spread_bets['bet_home'] == spread_bets['home_covered']
            
            wins = spread_bets['won'].sum()
            total = spread_bets['bet_home'].sum()
            print(f"\n📊 SPREAD BETS: {total} bets")
            if total > 0:
                print(f"   Wins: {wins}/{total} ({wins/total:.1%})")
                roi = (wins * 0.91 - (total - wins)) / total * 100  # -110 odds
                print(f"   ROI: {roi:.1f}%")
        
        # Total bets
        total_bets = df[df['p_over'].notna()].copy()
        if len(total_bets) > 0:
            total_bets['bet_over'] = total_bets['p_over'] > 0.5238
            total_bets['won'] = total_bets['bet_over'] == total_bets['over_hit']
            
            wins = total_bets['won'].sum()
            total = total_bets['bet_over'].sum()
            print(f"\n📊 TOTAL BETS: {total} bets")
            if total > 0:
                print(f"   Wins: {wins}/{total} ({wins/total:.1%})")
                roi = (wins * 0.91 - (total - wins)) / total * 100
                print(f"   ROI: {roi:.1f}%")
        
        print(f"\n📈 Variance Stats:")
        print(f"   Avg Spread SD: {df['spread_sd'].mean():.1f}")
        print(f"   Avg Total SD: {df['total_sd'].mean():.1f}")
        
        print("\n" + "="*80)
        print("✅ QUICK BACKTEST COMPLETE")
        print("="*80)
    else:
        print("\n❌ No results - check errors above")

if __name__ == "__main__":
    main()

