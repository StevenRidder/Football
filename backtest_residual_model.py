#!/usr/bin/env python3
"""
Backtest: Market-Anchored Residual Model vs Current Model
Tests on Weeks 1-8 of 2025 NFL season
Does NOT modify existing model - standalone analysis only
"""
import sys
sys.path.insert(0, '/Users/steveridder/Git/Football')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import requests
from typing import Dict, List, Tuple
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

WEEKS_TO_TEST = list(range(1, 8))  # Weeks 1-7 (Week 8 has no opening lines)
TRAIN_WEEKS = list(range(1, 5))  # Weeks 1-4 for training
TEST_WEEKS = list(range(5, 8))  # Weeks 5-7 for testing
CURRENT_SEASON = 2025
ARTIFACTS_DIR = Path('/Users/steveridder/Git/Football/artifacts')

# Backup QB games - REMOVED for honest backtest
# This was post-hoc tuning that inflated results
BACKUP_QB_GAMES = []

# ============================================================================
# ESPN API - Fetch Actual Scores
# ============================================================================

def fetch_espn_scores(week: int) -> Dict[str, Dict]:
    """Fetch actual scores from ESPN for a given week"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {'seasontype': 2, 'week': week, 'year': CURRENT_SEASON}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"  ⚠️  ESPN API returned {response.status_code} for week {week}")
            return {}
        
        data = response.json()
        scores = {}
        
        for event in data.get('events', []):
            comp = event.get('competitions', [{}])[0]
            competitors = comp.get('competitors', [])
            
            if len(competitors) == 2:
                home = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                away = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                
                if home and away:
                    away_abbr = away['team']['abbreviation']
                    home_abbr = home['team']['abbreviation']
                    
                    # Handle score format
                    away_score_val = away.get('score', 0)
                    home_score_val = home.get('score', 0)
                    
                    if isinstance(away_score_val, dict):
                        away_score = int(away_score_val.get('value', 0))
                    else:
                        away_score = int(away_score_val) if away_score_val else 0
                        
                    if isinstance(home_score_val, dict):
                        home_score = int(home_score_val.get('value', 0))
                    else:
                        home_score = int(home_score_val) if home_score_val else 0
                    
                    if away_score > 0 or home_score > 0:  # Only completed games
                        game_key = f"{away_abbr}@{home_abbr}"
                        scores[game_key] = {
                            'away': away_abbr,
                            'home': home_abbr,
                            'away_score': away_score,
                            'home_score': home_score,
                            'total': away_score + home_score,
                            'margin': home_score - away_score  # Positive = home wins
                        }
        
        return scores
    except Exception as e:
        print(f"  ❌ Error fetching ESPN scores for week {week}: {e}")
        return {}

# ============================================================================
# RESIDUAL MODEL SIMULATION
# ============================================================================

def calculate_residual_prediction(
    market_spread: float,
    market_total: float,
    model_spread: float,
    model_total: float,
    away_team: str,
    home_team: str,
    week: int,
    home_win_pct: float,
    ev_spread: float,
    ev_total: float
) -> Dict:
    """
    Simulate residual model prediction
    
    Strategy: Start with market baseline, then adjust based on:
    1. Model's disagreement with market (but dampened)
    2. Expected Value signals
    3. Confidence from win probability
    
    Key insight: We don't replace market, we adjust it slightly
    """
    
    # Calculate model's disagreement with market
    spread_disagreement = model_spread - market_spread
    total_disagreement = model_total - market_total
    
    # Dampen the disagreement (only take 30% of model's opinion)
    # This is the "residual" - we trust market more than our model
    RESIDUAL_WEIGHT = 0.30
    
    spread_adjustment = spread_disagreement * RESIDUAL_WEIGHT
    total_adjustment = total_disagreement * RESIDUAL_WEIGHT
    
    # Apply adjustments to market baseline
    predicted_margin = market_spread + spread_adjustment
    predicted_total = market_total + total_adjustment
    
    # Calculate confidence based on model features ONLY (not EV from prediction file)
    # EV from prediction file is circular - it was calculated using these same lines
    confidence_factors = []
    
    # 1. Win probability confidence (extreme probabilities = high confidence)
    if home_win_pct > 70 or home_win_pct < 30:
        confidence_factors.append(0.7)
    elif home_win_pct > 60 or home_win_pct < 40:
        confidence_factors.append(0.6)
    else:
        confidence_factors.append(0.5)
    
    # 2. Model disagreement confidence (strong disagreement = higher confidence)
    if abs(spread_disagreement) > 7 or abs(total_disagreement) > 10:
        confidence_factors.append(0.75)
    elif abs(spread_disagreement) > 4 or abs(total_disagreement) > 6:
        confidence_factors.append(0.6)
    else:
        confidence_factors.append(0.5)
    
    # Average confidence (removed EV factor to avoid circularity)
    confidence = np.mean(confidence_factors)
    
    # Check for backup QB (bonus confidence)
    backup_qb_bonus = 0
    for backup_game in BACKUP_QB_GAMES:
        if backup_game['week'] == week:
            if backup_game['team'] == away_team:
                backup_qb_bonus = 5
                predicted_margin += backup_qb_bonus
                predicted_total -= 8
                confidence = min(confidence + 0.2, 0.95)
            elif backup_game['team'] == home_team:
                backup_qb_bonus = 5
                predicted_margin -= backup_qb_bonus
                predicted_total -= 8
                confidence = min(confidence + 0.2, 0.95)
    
    return {
        'predicted_margin': predicted_margin,
        'predicted_total': predicted_total,
        'confidence': confidence,
        'adjustments': {
            'spread_adjustment': spread_adjustment,
            'total_adjustment': total_adjustment,
            'backup_qb_bonus': backup_qb_bonus
        }
    }

# ============================================================================
# BETTING LOGIC
# ============================================================================

def evaluate_bet_opportunities(
    market_spread: float,
    market_total: float,
    predicted_margin: float,
    predicted_total: float,
    confidence: float
) -> List[Dict]:
    """
    Determine which bets to make based on edge
    
    Rules:
    - Only bet if confidence > 0.55 (medium-high confidence)
    - Only bet if edge > 1.0 points (meaningful disagreement)
    - Bet size based on confidence level
    """
    bets = []
    
    # Spread bet
    spread_edge = abs(predicted_margin - market_spread)
    if spread_edge >= 1.0 and confidence >= 0.55:
        # Determine which side
        if predicted_margin > market_spread:
            # Home team is better than market thinks
            bets.append({
                'type': 'spread',
                'side': 'home',
                'line': market_spread,
                'edge': spread_edge,
                'stake': min(confidence * 100, 250)  # Max $250
            })
        else:
            # Away team is better than market thinks
            bets.append({
                'type': 'spread',
                'side': 'away',
                'line': market_spread,
                'edge': spread_edge,
                'stake': min(confidence * 100, 250)
            })
    
    # Total bet
    total_edge = abs(predicted_total - market_total)
    if total_edge >= 1.5 and confidence >= 0.55:
        # Determine over/under
        if predicted_total < market_total:
            # Under
            bets.append({
                'type': 'total',
                'side': 'under',
                'line': market_total,
                'edge': total_edge,
                'stake': min(confidence * 100, 250)
            })
        else:
            # Over
            bets.append({
                'type': 'total',
                'side': 'over',
                'line': market_total,
                'edge': total_edge,
                'stake': min(confidence * 100, 250)
            })
    
    return bets

def grade_bet(bet: Dict, actual_margin: float, actual_total: float, closing_spread: float = None, closing_total: float = None) -> Dict:
    """
    Grade a bet and calculate profit/loss
    
    Also calculates CLV (Closing Line Value) if closing lines provided
    CLV = (closing_line - bet_line) * side_sign
    Positive CLV means we got a better line than the closing line
    """
    if bet['type'] == 'spread':
        if bet['side'] == 'home':
            # We bet home, did home cover?
            diff = actual_margin - bet['line']
            side_sign = 1  # Home perspective
        else:
            # We bet away, did away cover?
            diff = bet['line'] - actual_margin  # Flip for away
            side_sign = -1  # Away perspective
        
        # Check for push (exact tie on the line) - use float tolerance
        if abs(diff) < 1e-9:
            result = 'PUSH'
            profit = 0
        elif diff > 0:
            result = True
            profit = bet['stake'] * 0.909  # Win $100 for every $110 bet
        else:
            result = False
            profit = -bet['stake']
        
        # Calculate CLV for spread
        clv = None
        if closing_spread is not None:
            # CLV = how much better our line was than closing
            # If we bet home and closing moved to home -4 from -3, we got worse line (negative CLV)
            # If we bet home and closing moved to home -2 from -3, we got better line (positive CLV)
            clv = (bet['line'] - closing_spread) * side_sign
    
    elif bet['type'] == 'total':
        if bet['side'] == 'under':
            diff = bet['line'] - actual_total  # Under wins if actual < line
            side_sign = -1  # Under = want lower
        else:
            diff = actual_total - bet['line']  # Over wins if actual > line
            side_sign = 1  # Over = want higher
        
        # Check for push (exact tie on the line) - use float tolerance
        if abs(diff) < 1e-9:
            result = 'PUSH'
            profit = 0
        elif diff > 0:
            result = True
            profit = bet['stake'] * 0.909
        else:
            result = False
            profit = -bet['stake']
        
        # Calculate CLV for total
        clv = None
        if closing_total is not None:
            # If we bet over and closing moved up, we got worse line (negative CLV)
            # If we bet over and closing moved down, we got better line (positive CLV)
            clv = (closing_total - bet['line']) * side_sign
    
    return {
        **bet,
        'result': 'WIN' if result is True else ('PUSH' if result == 'PUSH' else 'LOSS'),
        'profit': profit,
        'clv': clv
    }

# ============================================================================
# MAIN BACKTEST
# ============================================================================

def load_opening_closing_lines() -> tuple:
    """Load opening and closing lines from CSV"""
    lines_file = ARTIFACTS_DIR / 'opening_closing_lines_weeks_1-7_20251027.csv'
    if lines_file.exists():
        print(f"✅ Loading opening/closing lines from {lines_file.name}")
        df = pd.read_csv(lines_file)
        opening = df[df['line_type'] == 'opening'].copy()
        closing = df[df['line_type'] == 'closing'].copy()
        print(f"   Opening lines: {len(opening)} games")
        print(f"   Closing lines: {len(closing)} games")
        return opening, closing
    else:
        print("⚠️  No opening/closing lines file found")
        return pd.DataFrame(), pd.DataFrame()

def run_backtest():
    """Run full backtest on Weeks 1-8"""
    
    print("=" * 80)
    print("RESIDUAL MODEL BACKTEST - Weeks 1-8 (2025 NFL Season)")
    print("=" * 80)
    print()
    
    # Load opening and closing lines
    opening_lines, closing_lines = load_opening_closing_lines()
    print()
    
    all_results = []
    total_bets = 0
    total_wins = 0
    total_pushes = 0
    total_profit = 0
    total_risked = 0  # Actual sum of stakes for correct ROI calculation
    total_clv = 0
    positive_clv_count = 0
    
    # Walk-forward tracking
    train_bets = 0
    train_wins = 0
    train_profit = 0
    train_risked = 0
    train_clv = 0
    train_positive_clv = 0
    
    test_bets = 0
    test_wins = 0
    test_profit = 0
    test_risked = 0
    test_clv = 0
    test_positive_clv = 0
    
    for week in WEEKS_TO_TEST:
        print(f"\n{'='*80}")
        print(f"WEEK {week}")
        print(f"{'='*80}")
        
        # Load predictions for this week
        pred_files = list(ARTIFACTS_DIR.glob(f"predictions_2025_week{week}_*.csv"))
        if not pred_files:
            # Try current week format
            pred_files = list(ARTIFACTS_DIR.glob(f"predictions_2025_*.csv"))
            pred_files = [f for f in pred_files if f'_week{week}_' in f.name or (week == 8 and '_week' not in f.name)]
        
        if not pred_files:
            print(f"  ⚠️  No prediction file found for week {week}")
            continue
        
        pred_file = pred_files[0]
        predictions = pd.read_csv(pred_file)
        
        # Fetch actual scores
        actual_scores = fetch_espn_scores(week)
        
        if not actual_scores:
            print(f"  ⚠️  No actual scores found for week {week} (games may not have been played yet)")
            continue
        
        print(f"  Found {len(actual_scores)} completed games with scores")
        
        week_bets = 0
        week_wins = 0
        week_pushes = 0
        week_profit = 0
        week_risked = 0
        week_clv = 0
        week_positive_clv = 0
        games_evaluated = 0
        game_exposure = {}  # Track bets per game for exposure control
        
        # Process each game
        for _, row in predictions.iterrows():
            away = row['away']
            home = row['home']
            game_key = f"{away}@{home}"
            
            # Get OPENING lines for bet placement (this is when we'd place the bet)
            opening_game = opening_lines[(opening_lines['week'] == week) & 
                                        (opening_lines['away'] == away) & 
                                        (opening_lines['home'] == home)]
            
            if opening_game.empty:
                # Skip if no opening line (can't bet without a line)
                continue
            
            bet_spread = opening_game.iloc[0]['spread']
            bet_total = opening_game.iloc[0]['total']
            
            # Get CLOSING lines for CLV calculation
            closing_game = closing_lines[(closing_lines['week'] == week) & 
                                         (closing_lines['away'] == away) & 
                                         (closing_lines['home'] == home)]
            
            if not closing_game.empty:
                closing_spread = closing_game.iloc[0]['spread']
                closing_total = closing_game.iloc[0]['total']
            else:
                # If no closing line, use opening as fallback (not ideal but better than nothing)
                closing_spread = bet_spread
                closing_total = bet_total
            
            # Get model predictions
            model_spread = row.get('Model spread home-', bet_spread)
            model_total = row.get('Model total', bet_total)
            
            # Get model confidence signals
            home_win_pct = row.get('Home win %', 50)
            ev_spread = row.get('EV_spread', 0)
            ev_total = row.get('EV_total', 0)
            
            # Get actual outcome
            actual = actual_scores.get(game_key)
            if not actual:
                continue
            
            games_evaluated += 1
            
            # Calculate residual prediction using OPENING lines (bet placement)
            residual_pred = calculate_residual_prediction(
                bet_spread, bet_total,
                model_spread, model_total,
                away, home, week,
                home_win_pct, ev_spread, ev_total
            )
            
            # Evaluate bet opportunities using OPENING lines
            bets = evaluate_bet_opportunities(
                bet_spread,
                bet_total,
                residual_pred['predicted_margin'],
                residual_pred['predicted_total'],
                residual_pred['confidence']
            )
            
            # EXPOSURE CONTROL: Max 1 spread + 1 total per game
            if game_key not in game_exposure:
                game_exposure[game_key] = {'spread': 0, 'total': 0}
            
            filtered_bets = []
            for bet in bets:
                if bet['type'] == 'spread' and game_exposure[game_key]['spread'] == 0:
                    filtered_bets.append(bet)
                    game_exposure[game_key]['spread'] += 1
                elif bet['type'] == 'total' and game_exposure[game_key]['total'] == 0:
                    filtered_bets.append(bet)
                    game_exposure[game_key]['total'] += 1
            
            bets = filtered_bets
            
            # Debug: Show why no bet was placed (only for first 2 games per week)
            if not bets and games_evaluated <= 2:
                spread_edge = abs(residual_pred['predicted_margin'] - bet_spread)
                total_edge = abs(residual_pred['predicted_total'] - bet_total)
                print(f"    {game_key}: No bet (Spread edge: {spread_edge:.1f}, Total edge: {total_edge:.1f}, Confidence: {residual_pred['confidence']:.0%})")
            
            # Grade bets using CLOSING lines for TRUE CLV
            for bet in bets:
                graded = grade_bet(bet, actual['margin'], actual['total'], 
                                 closing_spread=closing_spread, 
                                 closing_total=closing_total)
                
                week_bets += 1
                total_bets += 1
                week_risked += bet['stake']
                total_risked += bet['stake']
                
                if graded['result'] == 'WIN':
                    week_wins += 1
                    total_wins += 1
                elif graded['result'] == 'PUSH':
                    week_pushes += 1
                    total_pushes += 1
                
                week_profit += graded['profit']
                total_profit += graded['profit']
                
                # Track CLV
                if graded['clv'] is not None:
                    week_clv += graded['clv']
                    total_clv += graded['clv']
                    if graded['clv'] > 0:
                        week_positive_clv += 1
                        positive_clv_count += 1
                
                # Walk-forward tracking
                if week in TRAIN_WEEKS:
                    train_bets += 1
                    train_risked += bet['stake']
                    if graded['result'] == 'WIN':
                        train_wins += 1
                    train_profit += graded['profit']
                    if graded['clv'] and graded['clv'] > 0:
                        train_positive_clv += 1
                    if graded['clv']:
                        train_clv += graded['clv']
                elif week in TEST_WEEKS:
                    test_bets += 1
                    test_risked += bet['stake']
                    if graded['result'] == 'WIN':
                        test_wins += 1
                    test_profit += graded['profit']
                    if graded['clv'] and graded['clv'] > 0:
                        test_positive_clv += 1
                    if graded['clv']:
                        test_clv += graded['clv']
                
                # Store result
                all_results.append({
                    'week': week,
                    'game': game_key,
                    'bet_type': bet['type'],
                    'bet_side': bet['side'],
                    'line': bet['line'],
                    'edge': bet['edge'],
                    'stake': bet['stake'],
                    'result': graded['result'],
                    'profit': graded['profit'],
                    'actual_margin': actual['margin'],
                    'actual_total': actual['total'],
                    'predicted_margin': residual_pred['predicted_margin'],
                    'predicted_total': residual_pred['predicted_total'],
                    'confidence': residual_pred['confidence'],
                    'clv': graded['clv']
                })
                
                # Print bet details
                result_icon = "✅" if graded['result'] == 'WIN' else "❌"
                clv_str = f", CLV: {graded['clv']:+.1f}" if graded['clv'] and graded['clv'] != 0 else ""
                print(f"  {result_icon} {game_key} ({actual['away_score']}-{actual['home_score']})")
                print(f"     {bet['type'].upper()} {bet['side'].upper()} {bet['line']:.1f} "
                      f"(Edge: {bet['edge']:.1f}, Confidence: {residual_pred['confidence']:.0%})")
                print(f"     Opening: Spread {bet_spread:+.1f}, Total {bet_total:.1f}")
                print(f"     Closing: Spread {closing_spread:+.1f}, Total {closing_total:.1f}{clv_str}")
                print(f"     Actual: Margin {actual['margin']:+d}, Total {actual['total']}")
                print(f"     Result: {graded['result']} (Stake: ${bet['stake']:.0f}, Profit: ${graded['profit']:+.2f})")
                print()
        
        # Week summary
        if week_bets > 0:
            week_win_rate = (week_wins / week_bets) * 100
            week_roi = (week_profit / week_risked) * 100  # Correct: profit / total risked
            week_avg_clv = week_clv / week_bets if week_bets > 0 else 0
            week_clv_pct = (week_positive_clv / week_bets * 100) if week_bets > 0 else 0
            print(f"\n  Week {week} Summary: {week_wins}/{week_bets} wins ({week_win_rate:.1f}%), "
                  f"Risked: ${week_risked:.0f}, Profit: ${week_profit:.2f}, ROI: {week_roi:.1f}%")
            print(f"  CLV: Avg {week_avg_clv:+.2f} pts, {week_clv_pct:.0f}% positive")
        else:
            print(f"\n  Week {week} Summary: No bets placed (evaluated {games_evaluated} games)")
    
    # Overall summary
    print("\n" + "=" * 80)
    print("OVERALL BACKTEST RESULTS")
    print("=" * 80)
    
    if total_bets > 0:
        win_rate = (total_wins / total_bets) * 100
        roi = (total_profit / total_risked) * 100  # Correct ROI
        avg_clv = total_clv / total_bets
        clv_pct = (positive_clv_count / total_bets) * 100
        
        print(f"\nTotal Bets: {total_bets}")
        print(f"Wins: {total_wins}")
        print(f"Pushes: {total_pushes}")
        print(f"Losses: {total_bets - total_wins - total_pushes}")
        print(f"Win Rate: {win_rate:.1f}% (excluding pushes)")
        print(f"\nTotal Risked: ${total_risked:.2f}")
        print(f"Total Profit: ${total_profit:.2f}")
        print(f"ROI: {roi:.1f}%")
        print(f"Average Profit per Bet: ${total_profit/total_bets:.2f}")
        print(f"\nCLV (Closing Line Value):")
        print(f"  Average CLV: {avg_clv:+.2f} points")
        print(f"  Positive CLV: {clv_pct:.1f}% of bets")
        
        if clv_pct > 50:
            print(f"  ✅ POSITIVE CLV - Edge is real and sustainable")
        elif clv_pct > 45:
            print(f"  ⚠️  MARGINAL CLV - Edge exists but small")
        else:
            print(f"  ❌ NEGATIVE CLV - No sustainable edge")
        
        # Walk-forward validation results
        print("\n" + "=" * 80)
        print("WALK-FORWARD VALIDATION")
        print("=" * 80)
        
        if train_bets > 0:
            train_win_rate = (train_wins / train_bets) * 100
            train_roi = (train_profit / train_risked) * 100
            train_avg_clv = train_clv / train_bets
            train_clv_pct = (train_positive_clv / train_bets) * 100
            
            print(f"\nTRAIN (Weeks 1-4):")
            print(f"  Bets: {train_bets}")
            print(f"  Win Rate: {train_win_rate:.1f}%")
            print(f"  ROI: {train_roi:.1f}%")
            print(f"  Avg CLV: {train_avg_clv:+.2f} pts")
            print(f"  Positive CLV: {train_clv_pct:.1f}%")
        
        if test_bets > 0:
            test_win_rate = (test_wins / test_bets) * 100
            test_roi = (test_profit / test_risked) * 100
            test_avg_clv = test_clv / test_bets
            test_clv_pct = (test_positive_clv / test_bets) * 100
            
            print(f"\nTEST (Weeks 5-7):")
            print(f"  Bets: {test_bets}")
            print(f"  Win Rate: {test_win_rate:.1f}%")
            print(f"  ROI: {test_roi:.1f}%")
            print(f"  Avg CLV: {test_avg_clv:+.2f} pts")
            print(f"  Positive CLV: {test_clv_pct:.1f}%")
            
            # Verdict
            if test_clv_pct > 50:
                print(f"\n  ✅ TEST CLV POSITIVE - Model generalizes!")
            elif test_clv_pct > 45:
                print(f"\n  ⚠️  TEST CLV MARGINAL - Weak generalization")
            else:
                print(f"\n  ❌ TEST CLV NEGATIVE - Model does not generalize")
    else:
        print("\n❌ No bets were placed (confidence/edge thresholds not met)")
    
    # Save detailed results
    if all_results:
        results_df = pd.DataFrame(all_results)
        output_file = ARTIFACTS_DIR / f"residual_model_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\n📊 Detailed results saved to: {output_file}")
    
    print("\n" + "=" * 80)

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    run_backtest()

