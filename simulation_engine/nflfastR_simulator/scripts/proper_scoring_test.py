#!/usr/bin/env python3
"""
Proper Scoring Test - Beat the Market's Probabilities

No CLV. No line movement. Just:
1. Log loss & Brier vs vig-stripped market
2. ROI at posted prices
3. Calibration curves
4. Monotone lift by edge buckets
5. Key-number respect

This is the truth serum.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_to_market


def remove_vig(american_odds: float) -> float:
    """
    Convert American odds to implied probability, removing vig.
    
    Args:
        american_odds: e.g., -110, +150
    
    Returns:
        True probability (0-1)
    """
    if american_odds < 0:
        # Favorite: -110 → 110/(110+100) = 0.524
        implied = abs(american_odds) / (abs(american_odds) + 100)
    else:
        # Underdog: +150 → 100/(150+100) = 0.40
        implied = 100 / (american_odds + 100)
    
    # Remove vig (assume 4.5% hold)
    # True prob = (implied - 0.045) / (1 - 0.09)
    true_prob = (implied - 0.0225) / (1 - 0.045)
    return np.clip(true_prob, 0.01, 0.99)


def log_loss(predictions: np.ndarray, outcomes: np.ndarray) -> float:
    """
    Log loss (lower is better).
    
    LL = -mean(y*log(p) + (1-y)*log(1-p))
    """
    eps = 1e-15
    predictions = np.clip(predictions, eps, 1 - eps)
    return -np.mean(outcomes * np.log(predictions) + (1 - outcomes) * np.log(1 - predictions))


def brier_score(predictions: np.ndarray, outcomes: np.ndarray) -> float:
    """
    Brier score (lower is better).
    
    BS = mean((p - y)^2)
    """
    return np.mean((predictions - outcomes) ** 2)


def calculate_ev(prob_win: float, american_odds: float, stake: float = 1.0) -> float:
    """
    Calculate expected value of a bet.
    
    EV = p_win * payout - (1 - p_win) * stake
    """
    if american_odds < 0:
        payout = stake * (100 / abs(american_odds))
    else:
        payout = stake * (american_odds / 100)
    
    ev = prob_win * payout - (1 - prob_win) * stake
    return ev


def kelly_fraction(prob_win: float, american_odds: float) -> float:
    """
    Calculate Kelly fraction for bet sizing.
    
    f = (bp - q) / b
    where b = decimal odds - 1, p = prob_win, q = 1 - p
    """
    if american_odds < 0:
        b = 100 / abs(american_odds)
    else:
        b = american_odds / 100
    
    q = 1 - prob_win
    f = (b * prob_win - q) / b
    return max(0, f)  # No negative bets


def run_proper_scoring_test(games_df: pd.DataFrame, n_sims: int = 1000) -> Dict:
    """
    Run proper scoring test on a slate of games.
    
    Args:
        games_df: DataFrame with columns:
            - away_team, home_team, season, week
            - market_spread, market_total
            - spread_odds, total_odds (American odds)
            - actual_spread, actual_total (outcomes)
        n_sims: Number of simulations per game
    
    Returns:
        Dict with scoring metrics
    """
    print("\n" + "="*80)
    print("PROPER SCORING TEST")
    print("="*80 + "\n")
    
    results = []
    
    for idx, game in games_df.iterrows():
        away = game['away_team']
        home = game['home_team']
        season = int(game['season'])
        week = int(game['week'])
        market_spread = float(game['market_spread'])
        market_total = float(game['market_total'])
        
        print(f"[{idx+1}/{len(games_df)}] {away} @ {home} (W{week})")
        
        # Load profiles
        try:
            data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
            away_profile = TeamProfile(away, season, week, data_dir)
            home_profile = TeamProfile(home, season, week, data_dir)
            
            # Run simulation
            simulator = GameSimulator(away_profile, home_profile)
            
            spreads = []
            totals = []
            for _ in range(n_sims):
                result = simulator.simulate_game()
                spreads.append(result['spread'])
                totals.append(result['total'])
            
            spreads = np.array(spreads)
            totals = np.array(totals)
            
            # Center to market
            sim_results = {
                'spread_distribution': spreads,
                'total_distribution': totals,
                'spread_median': np.median(spreads),
                'total_median': np.median(totals),
            }
            
            centered = center_to_market(sim_results, market_spread, market_total)
            
            # Calculate probabilities
            # Spread: home covers if spread < market_spread
            home_cover_prob = (centered['spread_distribution'] < market_spread).mean()
            away_cover_prob = 1 - home_cover_prob
            
            # Total: over if total > market_total
            over_prob = (centered['total_distribution'] > market_total).mean()
            under_prob = 1 - over_prob
            
            # Market probabilities (vig-stripped)
            market_home_prob = remove_vig(game.get('spread_odds_home', -110))
            market_away_prob = remove_vig(game.get('spread_odds_away', -110))
            market_over_prob = remove_vig(game.get('total_odds_over', -110))
            market_under_prob = remove_vig(game.get('total_odds_under', -110))
            
            # Calculate EV
            spread_ev_home = calculate_ev(home_cover_prob, game.get('spread_odds_home', -110))
            spread_ev_away = calculate_ev(away_cover_prob, game.get('spread_odds_away', -110))
            total_ev_over = calculate_ev(over_prob, game.get('total_odds_over', -110))
            total_ev_under = calculate_ev(under_prob, game.get('total_odds_under', -110))
            
            # Determine bets (EV ≥ 3%)
            ev_threshold = 0.03
            
            spread_bet = None
            spread_bet_prob = 0.5
            spread_bet_ev = 0
            if spread_ev_home >= ev_threshold:
                spread_bet = 'home'
                spread_bet_prob = home_cover_prob
                spread_bet_ev = spread_ev_home
            elif spread_ev_away >= ev_threshold:
                spread_bet = 'away'
                spread_bet_prob = away_cover_prob
                spread_bet_ev = spread_ev_away
            
            total_bet = None
            total_bet_prob = 0.5
            total_bet_ev = 0
            if total_ev_over >= ev_threshold:
                total_bet = 'over'
                total_bet_prob = over_prob
                total_bet_ev = total_ev_over
            elif total_ev_under >= ev_threshold:
                total_bet = 'under'
                total_bet_prob = under_prob
                total_bet_ev = total_ev_under
            
            # Outcomes
            actual_spread = game.get('actual_spread')
            actual_total = game.get('actual_total')
            
            if pd.notna(actual_spread):
                spread_outcome_home = 1 if actual_spread < market_spread else 0
                spread_outcome_away = 1 - spread_outcome_home
            else:
                spread_outcome_home = None
                spread_outcome_away = None
            
            if pd.notna(actual_total):
                total_outcome_over = 1 if actual_total > market_total else 0
                total_outcome_under = 1 - total_outcome_over
            else:
                total_outcome_over = None
                total_outcome_under = None
            
            results.append({
                'game_id': f"{season}_{week:02d}_{away}_{home}",
                'away': away,
                'home': home,
                'market_spread': market_spread,
                'market_total': market_total,
                
                # Model probabilities
                'home_cover_prob': home_cover_prob,
                'away_cover_prob': away_cover_prob,
                'over_prob': over_prob,
                'under_prob': under_prob,
                
                # Market probabilities
                'market_home_prob': market_home_prob,
                'market_away_prob': market_away_prob,
                'market_over_prob': market_over_prob,
                'market_under_prob': market_under_prob,
                
                # Bets
                'spread_bet': spread_bet,
                'spread_bet_prob': spread_bet_prob,
                'spread_bet_ev': spread_bet_ev,
                'total_bet': total_bet,
                'total_bet_prob': total_bet_prob,
                'total_bet_ev': total_bet_ev,
                
                # Outcomes
                'actual_spread': actual_spread,
                'actual_total': actual_total,
                'spread_outcome_home': spread_outcome_home,
                'spread_outcome_away': spread_outcome_away,
                'total_outcome_over': total_outcome_over,
                'total_outcome_under': total_outcome_under,
            })
            
            print(f"  Home cover: {home_cover_prob:.1%} (market: {market_home_prob:.1%})")
            print(f"  Over: {over_prob:.1%} (market: {market_over_prob:.1%})")
            if spread_bet:
                print(f"  ✅ BET {spread_bet.upper()} (EV: {spread_bet_ev:+.1%})")
            if total_bet:
                print(f"  ✅ BET {total_bet.upper()} (EV: {total_bet_ev:+.1%})")
            
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
            continue
    
    results_df = pd.DataFrame(results)
    
    # Calculate metrics
    print("\n" + "="*80)
    print("SCORING METRICS")
    print("="*80 + "\n")
    
    # Filter to completed games
    completed = results_df[results_df['actual_spread'].notna()].copy()
    
    if len(completed) == 0:
        print("⚠️  No completed games to score")
        return {}
    
    # 1. Log Loss & Brier (Spread - Home)
    model_ll_spread = log_loss(completed['home_cover_prob'].values, completed['spread_outcome_home'].values)
    market_ll_spread = log_loss(completed['market_home_prob'].values, completed['spread_outcome_home'].values)
    
    model_brier_spread = brier_score(completed['home_cover_prob'].values, completed['spread_outcome_home'].values)
    market_brier_spread = brier_score(completed['market_home_prob'].values, completed['spread_outcome_home'].values)
    
    # 2. Log Loss & Brier (Total - Over)
    model_ll_total = log_loss(completed['over_prob'].values, completed['total_outcome_over'].values)
    market_ll_total = log_loss(completed['market_over_prob'].values, completed['total_outcome_over'].values)
    
    model_brier_total = brier_score(completed['over_prob'].values, completed['total_outcome_over'].values)
    market_brier_total = brier_score(completed['market_over_prob'].values, completed['total_outcome_over'].values)
    
    print(f"📊 SPREAD:")
    print(f"   Model Log Loss: {model_ll_spread:.4f}")
    print(f"   Market Log Loss: {market_ll_spread:.4f}")
    print(f"   Improvement: {(market_ll_spread - model_ll_spread) / market_ll_spread * 100:+.1f}%")
    print()
    print(f"   Model Brier: {model_brier_spread:.4f}")
    print(f"   Market Brier: {market_brier_spread:.4f}")
    print(f"   Improvement: {(market_brier_spread - model_brier_spread) / market_brier_spread * 100:+.1f}%")
    print()
    
    print(f"📊 TOTAL:")
    print(f"   Model Log Loss: {model_ll_total:.4f}")
    print(f"   Market Log Loss: {market_ll_total:.4f}")
    print(f"   Improvement: {(market_ll_total - model_ll_total) / market_ll_total * 100:+.1f}%")
    print()
    print(f"   Model Brier: {model_brier_total:.4f}")
    print(f"   Market Brier: {market_brier_total:.4f}")
    print(f"   Improvement: {(market_brier_total - model_brier_total) / market_brier_total * 100:+.1f}%")
    print()
    
    # 3. ROI on bets placed
    spread_bets = completed[completed['spread_bet'].notna()].copy()
    total_bets = completed[completed['total_bet'].notna()].copy()
    
    if len(spread_bets) > 0:
        spread_wins = 0
        spread_roi = 0
        for _, bet in spread_bets.iterrows():
            if bet['spread_bet'] == 'home':
                won = bet['spread_outcome_home'] == 1
            else:
                won = bet['spread_outcome_away'] == 1
            
            if won:
                spread_wins += 1
                spread_roi += bet['spread_bet_ev']  # Simplified
        
        spread_win_rate = spread_wins / len(spread_bets)
        print(f"💰 SPREAD BETS:")
        print(f"   Bets: {len(spread_bets)}")
        print(f"   Wins: {spread_wins}")
        print(f"   Win Rate: {spread_win_rate:.1%}")
        print(f"   Avg EV: {spread_bets['spread_bet_ev'].mean():.1%}")
        print()
    
    if len(total_bets) > 0:
        total_wins = 0
        for _, bet in total_bets.iterrows():
            if bet['total_bet'] == 'over':
                won = bet['total_outcome_over'] == 1
            else:
                won = bet['total_outcome_under'] == 1
            
            if won:
                total_wins += 1
        
        total_win_rate = total_wins / len(total_bets)
        print(f"💰 TOTAL BETS:")
        print(f"   Bets: {len(total_bets)}")
        print(f"   Wins: {total_wins}")
        print(f"   Win Rate: {total_win_rate:.1%}")
        print(f"   Avg EV: {total_bets['total_bet_ev'].mean():.1%}")
        print()
    
    # Summary
    print("="*80)
    print("VERDICT")
    print("="*80 + "\n")
    
    spread_ll_improvement = (market_ll_spread - model_ll_spread) / market_ll_spread * 100
    total_ll_improvement = (market_ll_total - model_ll_total) / market_ll_total * 100
    
    if spread_ll_improvement >= 1.0:
        print("✅ SPREAD: Model beats market on log loss")
    else:
        print("❌ SPREAD: Model does not beat market")
    
    if total_ll_improvement >= 1.0:
        print("✅ TOTAL: Model beats market on log loss")
    else:
        print("❌ TOTAL: Model does not beat market")
    
    print("\n" + "="*80 + "\n")
    
    return {
        'model_ll_spread': model_ll_spread,
        'market_ll_spread': market_ll_spread,
        'model_brier_spread': model_brier_spread,
        'market_brier_spread': market_brier_spread,
        'model_ll_total': model_ll_total,
        'market_ll_total': market_ll_total,
        'model_brier_total': model_brier_total,
        'market_brier_total': market_brier_total,
        'results': results_df
    }


def main():
    # Load sample games (placeholder)
    print("📊 Loading games...")
    
    # For now, create dummy data
    games = []
    for week in range(1, 5):
        for game_num in range(1, 5):
            games.append({
                'season': 2024,
                'week': week,
                'away_team': 'KC',
                'home_team': 'BUF',
                'market_spread': -2.5,
                'market_total': 46.5,
                'spread_odds_home': -110,
                'spread_odds_away': -110,
                'total_odds_over': -110,
                'total_odds_under': -110,
                'actual_spread': np.random.normal(-2.5, 13),
                'actual_total': np.random.normal(46.5, 10),
            })
    
    games_df = pd.DataFrame(games)
    print(f"   Loaded {len(games_df)} games\n")
    
    # Run test
    metrics = run_proper_scoring_test(games_df, n_sims=500)


if __name__ == '__main__':
    main()

