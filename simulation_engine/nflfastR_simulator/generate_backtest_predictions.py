#!/usr/bin/env python3
"""
Generate Backtest Predictions - Run simulator on historical games

Outputs CSV in Flask format with:
- Betting recommendations
- Win/loss results
- Performance metrics
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_to_market


def generate_predictions_for_games(games_df: pd.DataFrame, n_sims: int = 1000) -> pd.DataFrame:
    """
    Generate predictions for a slate of games.
    
    Args:
        games_df: DataFrame with columns:
            - season, week, away_team, home_team
            - market_spread, market_total
            - actual_away_score, actual_home_score (if completed)
        n_sims: Number of simulations per game
    
    Returns:
        DataFrame in Flask format
    """
    print(f"\n🎲 Generating predictions for {len(games_df)} games...")
    print(f"   Simulations per game: {n_sims}\n")
    
    results = []
    
    for idx, game in games_df.iterrows():
        away = game['away_team']
        home = game['home_team']
        season = int(game['season'])
        week = int(game['week'])
        market_spread = float(game['market_spread'])
        market_total = float(game['market_total'])
        
        print(f"[{idx+1}/{len(games_df)}] {away} @ {home} (S{season} W{week})")
        
        try:
            # Load profiles
            data_dir = Path(__file__).parent / "data" / "nflfastR"
            away_profile = TeamProfile(away, season, week, data_dir)
            home_profile = TeamProfile(home, season, week, data_dir)
            
            # Run simulation
            simulator = GameSimulator(away_profile, home_profile)
            
            spreads = []
            totals = []
            away_scores = []
            home_scores = []
            
            for _ in range(n_sims):
                result = simulator.simulate_game()
                spreads.append(result['spread'])
                totals.append(result['total'])
                away_scores.append(result['away_score'])
                home_scores.append(result['home_score'])
            
            spreads = np.array(spreads)
            totals = np.array(totals)
            away_scores = np.array(away_scores)
            home_scores = np.array(home_scores)
            
            # Center to market
            sim_results = {
                'spread_distribution': spreads,
                'total_distribution': totals,
                'spread_median': np.median(spreads),
                'total_median': np.median(totals),
            }
            
            centered = center_to_market(sim_results, market_spread, market_total)
            
            # Calculate probabilities
            home_cover_prob = (centered['spread_distribution'] < market_spread).mean()
            away_cover_prob = 1 - home_cover_prob
            over_prob = (centered['total_distribution'] > market_total).mean()
            under_prob = 1 - over_prob
            
            # Home win probability (spread < 0 means home wins)
            home_win_prob = (centered['spread_distribution'] < 0).mean()
            
            # Our predictions (raw, before centering)
            our_away_score = np.mean(away_scores)
            our_home_score = np.mean(home_scores)
            our_spread = our_away_score - our_home_score  # Positive = away favored
            our_total = our_away_score + our_home_score
            
            # Market-implied scores (for display)
            closing_away_score = (market_total - market_spread) / 2
            closing_home_score = (market_total + market_spread) / 2
            
            # Betting recommendations
            spread_edge = abs(our_spread - market_spread)
            total_edge = abs(our_total - market_total)
            
            # Spread bet (edge ≥ 1.5 pts)
            if spread_edge >= 1.5:
                if our_spread < market_spread:
                    # We think home will cover
                    spread_recommendation = home
                    spread_bet = "Home ATS"
                else:
                    # We think away will cover
                    spread_recommendation = away
                    spread_bet = "Away ATS"
            else:
                spread_recommendation = None
                spread_bet = "Pass"
            
            # Total bet (edge ≥ 2.0 pts)
            if total_edge >= 2.0:
                if our_total > market_total:
                    total_recommendation = "Over"
                    total_bet = "Over"
                else:
                    total_recommendation = "Under"
                    total_bet = "Under"
            else:
                total_recommendation = "Pass"
                total_bet = "Pass"
            
            # Moneyline bet (if home_win_prob significantly different from 50%)
            if home_win_prob >= 0.65:
                moneyline_bet = home
            elif home_win_prob <= 0.35:
                moneyline_bet = away
            else:
                moneyline_bet = "Pass"
            
            # Actual results (if game completed)
            actual_away = game.get('actual_away_score')
            actual_home = game.get('actual_home_score')
            
            is_completed = pd.notna(actual_away) and pd.notna(actual_home)
            
            if is_completed:
                actual_away = float(actual_away)
                actual_home = float(actual_home)
                actual_spread = actual_away - actual_home
                actual_total = actual_away + actual_home
                
                # Grade spread bet
                if spread_bet != "Pass":
                    if spread_recommendation == home:
                        spread_win = 1 if actual_spread < market_spread else 0
                    else:
                        spread_win = 1 if actual_spread > market_spread else 0
                    spread_result = "WIN" if spread_win else "LOSS"
                else:
                    spread_win = None
                    spread_result = None
                
                # Grade total bet
                if total_bet != "Pass":
                    if total_recommendation == "Over":
                        total_win = 1 if actual_total > market_total else 0
                    else:
                        total_win = 1 if actual_total < market_total else 0
                    total_result = "WIN" if total_win else "LOSS"
                else:
                    total_win = None
                    total_result = None
                
                # Grade moneyline bet
                if moneyline_bet != "Pass":
                    if moneyline_bet == home:
                        ml_win = 1 if actual_spread < 0 else 0
                    else:
                        ml_win = 1 if actual_spread > 0 else 0
                    moneyline_result = "WIN" if ml_win else "LOSS"
                else:
                    ml_win = None
                    moneyline_result = None
                
                # Errors
                score_error_away = abs(our_away_score - actual_away)
                score_error_home = abs(our_home_score - actual_home)
                spread_error = abs(our_spread - actual_spread)
                total_error = abs(our_total - actual_total)
            else:
                actual_away = None
                actual_home = None
                spread_win = None
                spread_result = None
                total_win = None
                total_result = None
                ml_win = None
                moneyline_result = None
                score_error_away = None
                score_error_home = None
                spread_error = None
                total_error = None
            
            # Build result row
            results.append({
                'game_id': f"{away}@{home}_W{week}",
                'season': season,
                'week': week,
                'gameday': game.get('gameday', f"{season}-09-{week:02d}"),
                'gametime': game.get('gametime', '13:00'),
                'away_team': away,
                'home_team': home,
                
                # Market
                'market_spread': market_spread,
                'market_total': market_total,
                'closing_spread': market_spread,  # Assume same as market
                'closing_total': market_total,
                'closing_away_score': closing_away_score,
                'closing_home_score': closing_home_score,
                
                # Our predictions
                'our_away_score': round(our_away_score, 1),
                'our_home_score': round(our_home_score, 1),
                'our_spread': round(our_spread, 1),
                'our_total': round(our_total, 1),
                
                # Probabilities
                'home_cover_prob': round(home_cover_prob * 100, 1),
                'over_prob': round(over_prob * 100, 1),
                'home_win_prob': round(home_win_prob * 100, 1),
                
                # Recommendations
                'spread_recommendation': spread_recommendation,
                'spread_bet': spread_bet,
                'spread_edge': round(spread_edge, 1),
                'our_spread_pick': spread_recommendation,
                
                'total_recommendation': total_recommendation,
                'total_bet': total_bet,
                'total_edge': round(total_edge, 1),
                'our_total_pick': total_recommendation if total_recommendation != "Pass" else None,
                
                'moneyline_bet': moneyline_bet,
                
                # Actual results
                'actual_away_score': actual_away,
                'actual_home_score': actual_home,
                'is_completed': is_completed,
                
                # Grading
                'spread_result': spread_result,
                'spread_result_numeric': spread_win,
                'total_result': total_result,
                'total_result_numeric': total_win,
                'moneyline_result': moneyline_result,
                'moneyline_result_numeric': ml_win,
                
                # Errors
                'score_error_away': score_error_away,
                'score_error_home': score_error_home,
                'spread_error': spread_error,
                'total_error': total_error,
            })
            
            print(f"  ✅ {spread_bet} | {total_bet} | ML: {moneyline_bet}")
            
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
            continue
    
    return pd.DataFrame(results)


def print_performance_summary(df: pd.DataFrame):
    """Print performance summary."""
    print("\n" + "="*80)
    print("BETTING PERFORMANCE SUMMARY")
    print("="*80 + "\n")
    
    completed = df[df['is_completed'] == True].copy()
    
    if len(completed) == 0:
        print("⚠️  No completed games")
        return
    
    # Spread bets
    spread_bets = completed[completed['spread_bet'] != 'Pass'].copy()
    if len(spread_bets) > 0:
        spread_wins = spread_bets['spread_result_numeric'].sum()
        spread_win_rate = spread_wins / len(spread_bets)
        print(f"📊 SPREAD BETS:")
        print(f"   Bets: {len(spread_bets)}")
        print(f"   Wins: {int(spread_wins)}")
        print(f"   Win Rate: {spread_win_rate:.1%}")
        print(f"   Avg Edge: {spread_bets['spread_edge'].mean():.1f} pts")
        print()
    
    # Total bets
    total_bets = completed[completed['total_bet'] != 'Pass'].copy()
    if len(total_bets) > 0:
        total_wins = total_bets['total_result_numeric'].sum()
        total_win_rate = total_wins / len(total_bets)
        print(f"📊 TOTAL BETS:")
        print(f"   Bets: {len(total_bets)}")
        print(f"   Wins: {int(total_wins)}")
        print(f"   Win Rate: {total_win_rate:.1%}")
        print(f"   Avg Edge: {total_bets['total_edge'].mean():.1f} pts")
        print()
    
    # Moneyline bets
    ml_bets = completed[completed['moneyline_bet'] != 'Pass'].copy()
    if len(ml_bets) > 0:
        ml_wins = ml_bets['moneyline_result_numeric'].sum()
        ml_win_rate = ml_wins / len(ml_bets)
        print(f"📊 MONEYLINE BETS:")
        print(f"   Bets: {len(ml_bets)}")
        print(f"   Wins: {int(ml_wins)}")
        print(f"   Win Rate: {ml_win_rate:.1%}")
        print()
    
    # Overall
    all_bets = len(spread_bets) + len(total_bets)
    all_wins = (spread_bets['spread_result_numeric'].sum() if len(spread_bets) > 0 else 0) + \
               (total_bets['total_result_numeric'].sum() if len(total_bets) > 0 else 0)
    
    if all_bets > 0:
        overall_win_rate = all_wins / all_bets
        print(f"📊 OVERALL:")
        print(f"   Total Bets: {all_bets}")
        print(f"   Total Wins: {int(all_wins)}")
        print(f"   Win Rate: {overall_win_rate:.1%}")
        print(f"   Breakeven: 52.4%")
        if overall_win_rate >= 0.524:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
    
    print("\n" + "="*80 + "\n")


def main():
    # Load historical games
    print("📊 Loading historical games...")
    
    # For now, use dummy data - replace with actual nfl_data_py load
    games = []
    for season in [2024]:
        for week in range(1, 5):  # Test on 4 weeks
            # Sample games
            games.append({
                'season': season,
                'week': week,
                'away_team': 'KC',
                'home_team': 'BUF',
                'market_spread': -2.5,
                'market_total': 46.5,
                'actual_away_score': np.random.normal(24, 7),
                'actual_home_score': np.random.normal(21, 7),
            })
            games.append({
                'season': season,
                'week': week,
                'away_team': 'SF',
                'home_team': 'DAL',
                'market_spread': -3.0,
                'market_total': 48.0,
                'actual_away_score': np.random.normal(27, 7),
                'actual_home_score': np.random.normal(24, 7),
            })
    
    games_df = pd.DataFrame(games)
    print(f"   Loaded {len(games_df)} games\n")
    
    # Generate predictions
    predictions_df = generate_predictions_for_games(games_df, n_sims=500)
    
    # Print summary
    print_performance_summary(predictions_df)
    
    # Save to CSV
    output_file = Path(__file__).parent / "artifacts" / "backtest_predictions.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_file, index=False)
    print(f"✅ Saved predictions to: {output_file}\n")


if __name__ == '__main__':
    main()

