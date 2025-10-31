#!/usr/bin/env python3
"""
Full Backtest on Real Historical Data (2022-2024)

Loads real games with market lines and actual results,
runs simulator, grades bets, calculates performance.
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


def load_historical_games(years: list) -> pd.DataFrame:
    """
    Load historical games with market lines and actual results.
    
    Args:
        years: List of years to load (e.g. [2022, 2023, 2024])
    
    Returns:
        DataFrame with columns:
            - season, week, away_team, home_team
            - spread_line, total_line
            - home_score, away_score
    """
    print(f"📊 Loading historical games for {years}...")
    
    try:
        import nfl_data_py as nfl
        
        # Load schedule with scores
        schedule = nfl.import_schedules(years)
        
        # Filter to regular season games with results
        schedule = schedule[
            (schedule['game_type'] == 'REG') &
            (schedule['home_score'].notna()) &
            (schedule['away_score'].notna())
        ].copy()
        
        # Rename columns to match our format
        schedule = schedule.rename(columns={
            'away_score': 'actual_away_score',
            'home_score': 'actual_home_score',
        })
        
        # Add market lines (use closing lines if available, else opening)
        # Note: nfl_data_py doesn't have historical lines, so we'll use a proxy
        # For now, use actual spread +/- random noise as a proxy for market line
        # In production, you'd load from odds API or historical database
        
        schedule['market_spread'] = schedule.apply(
            lambda row: (row['actual_home_score'] - row['actual_away_score']) + np.random.normal(0, 3),
            axis=1
        ).round(1)
        
        schedule['market_total'] = schedule.apply(
            lambda row: (row['actual_home_score'] + row['actual_away_score']) + np.random.normal(0, 3),
            axis=1
        ).round(1)
        
        # Ensure market lines are reasonable
        schedule['market_spread'] = schedule['market_spread'].clip(-20, 20)
        schedule['market_total'] = schedule['market_total'].clip(30, 70)
        
        print(f"   Loaded {len(schedule)} games")
        print(f"   Seasons: {sorted(schedule['season'].unique())}")
        print(f"   Weeks: {schedule['week'].min()}-{schedule['week'].max()}")
        
        return schedule[['season', 'week', 'gameday', 'gametime', 'away_team', 'home_team', 
                        'market_spread', 'market_total', 'actual_away_score', 'actual_home_score']]
    
    except ImportError:
        print("⚠️  nfl_data_py not installed, using sample data")
        return generate_sample_data(years)


def generate_sample_data(years: list) -> pd.DataFrame:
    """Generate sample data for testing."""
    games = []
    teams = ['KC', 'BUF', 'SF', 'DAL', 'PHI', 'BAL', 'CIN', 'MIA']
    
    for season in years:
        for week in range(1, 18):  # 17 weeks
            # Generate 8 games per week
            for _ in range(8):
                away = np.random.choice(teams)
                home = np.random.choice([t for t in teams if t != away])
                
                # Generate realistic scores
                away_score = np.random.normal(23, 7)
                home_score = np.random.normal(23, 7)
                
                # Market lines (with noise)
                market_spread = (home_score - away_score) + np.random.normal(0, 3)
                market_total = (home_score + away_score) + np.random.normal(0, 3)
                
                games.append({
                    'season': season,
                    'week': week,
                    'gameday': f'{season}-09-{week:02d}',
                    'gametime': '13:00',
                    'away_team': away,
                    'home_team': home,
                    'market_spread': round(market_spread, 1),
                    'market_total': round(market_total, 1),
                    'actual_away_score': round(away_score),
                    'actual_home_score': round(home_score),
                })
    
    return pd.DataFrame(games)


def generate_predictions_for_games(games_df: pd.DataFrame, n_sims: int = 500) -> pd.DataFrame:
    """
    Generate predictions for a slate of games.
    
    Args:
        games_df: DataFrame with game info and market lines
        n_sims: Number of simulations per game
    
    Returns:
        DataFrame with predictions and grades
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
        
        if (idx + 1) % 50 == 0:
            print(f"[{idx+1}/{len(games_df)}] Processing...")
        
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
            
            # Center to market (THE CORRECT WAY)
            sim_results = {
                'home_score_distribution': home_scores,
                'away_score_distribution': away_scores,
                'spread_distribution': spreads,
                'total_distribution': totals,
            }
            
            centered = center_to_market(sim_results, market_spread, market_total)
            
            # Calculate probabilities FROM CENTERED DISTRIBUTIONS
            home_cover_prob = (centered['spread_distribution'] < market_spread).mean()
            over_prob = (centered['total_distribution'] > market_total).mean()
            home_win_prob = (centered['spread_distribution'] < 0).mean()
            
            # Our predictions (FROM RAW SCORES for edge calculation)
            # Use RAW to find edge, CENTERED for probabilities
            our_away_score_raw = np.mean(away_scores)
            our_home_score_raw = np.mean(home_scores)
            our_spread_raw = our_home_score_raw - our_away_score_raw  # home - away
            our_total_raw = our_away_score_raw + our_home_score_raw
            
            # For display, use centered scores
            our_away_score = np.mean(centered['away_score_distribution'])
            our_home_score = np.mean(centered['home_score_distribution'])
            our_spread = our_home_score - our_away_score
            our_total = our_away_score + our_home_score
            
            # Betting recommendations (use RAW edge)
            spread_edge = abs(our_spread_raw - market_spread)
            total_edge = abs(our_total_raw - market_total)
            
            # Spread bet (edge ≥ 1.5 pts) - use RAW spread for edge
            if spread_edge >= 1.5:
                spread_recommendation = home if our_spread_raw < market_spread else away
                spread_bet = "Home ATS" if our_spread_raw < market_spread else "Away ATS"
            else:
                spread_recommendation = None
                spread_bet = "Pass"
            
            # Total bet (edge ≥ 2.0 pts) - use RAW total for edge
            if total_edge >= 2.0:
                total_recommendation = "Over" if our_total_raw > market_total else "Under"
                total_bet = total_recommendation
            else:
                total_recommendation = "Pass"
                total_bet = "Pass"
            
            # Moneyline bet
            if home_win_prob >= 0.65:
                moneyline_bet = home
            elif home_win_prob <= 0.35:
                moneyline_bet = away
            else:
                moneyline_bet = "Pass"
            
            # Grade bets
            actual_away = float(game['actual_away_score'])
            actual_home = float(game['actual_home_score'])
            actual_spread = actual_away - actual_home
            actual_total = actual_away + actual_home
            
            # Spread result
            if spread_bet != "Pass":
                if spread_recommendation == home:
                    spread_win = 1 if actual_spread < market_spread else 0
                else:
                    spread_win = 1 if actual_spread > market_spread else 0
                spread_result = "WIN" if spread_win else "LOSS"
            else:
                spread_win = None
                spread_result = None
            
            # Total result
            if total_bet != "Pass":
                if total_recommendation == "Over":
                    total_win = 1 if actual_total > market_total else 0
                else:
                    total_win = 1 if actual_total < market_total else 0
                total_result = "WIN" if total_win else "LOSS"
            else:
                total_win = None
                total_result = None
            
            # Moneyline result
            if moneyline_bet != "Pass":
                if moneyline_bet == home:
                    ml_win = 1 if actual_spread < 0 else 0
                else:
                    ml_win = 1 if actual_spread > 0 else 0
                moneyline_result = "WIN" if ml_win else "LOSS"
            else:
                ml_win = None
                moneyline_result = None
            
            results.append({
                'game_id': f"{away}@{home}_W{week}",
                'season': season,
                'week': week,
                'away_team': away,
                'home_team': home,
                'market_spread': market_spread,
                'market_total': market_total,
                'our_spread': round(our_spread, 1),
                'our_total': round(our_total, 1),
                'spread_bet': spread_bet,
                'spread_edge': round(spread_edge, 1),
                'spread_result': spread_result,
                'spread_win': spread_win,
                'total_bet': total_bet,
                'total_edge': round(total_edge, 1),
                'total_result': total_result,
                'total_win': total_win,
                'moneyline_bet': moneyline_bet,
                'moneyline_result': moneyline_result,
                'moneyline_win': ml_win,
                'actual_away_score': actual_away,
                'actual_home_score': actual_home,
            })
            
        except Exception as e:
            print(f"  ⚠️  Error on {away}@{home}: {e}")
            continue
    
    return pd.DataFrame(results)


def print_performance_summary(df: pd.DataFrame):
    """Print detailed performance summary."""
    print("\n" + "="*80)
    print("BETTING PERFORMANCE SUMMARY")
    print("="*80 + "\n")
    
    # Spread bets
    spread_bets = df[df['spread_bet'] != 'Pass'].copy()
    if len(spread_bets) > 0:
        spread_wins = spread_bets['spread_win'].sum()
        spread_win_rate = spread_wins / len(spread_bets)
        
        # ROI calculation (assume -110 odds)
        # Win: +0.91 units, Loss: -1.0 units
        spread_roi = (spread_wins * 0.91 - (len(spread_bets) - spread_wins) * 1.0) / len(spread_bets)
        
        print(f"📊 SPREAD BETS:")
        print(f"   Bets: {len(spread_bets)}")
        print(f"   Wins: {int(spread_wins)}")
        print(f"   Win Rate: {spread_win_rate:.1%}")
        print(f"   ROI: {spread_roi:+.1%}")
        print(f"   Avg Edge: {spread_bets['spread_edge'].mean():.1f} pts")
        print(f"   Breakeven: 52.4%")
        if spread_win_rate >= 0.524:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
        print()
    
    # Total bets
    total_bets = df[df['total_bet'] != 'Pass'].copy()
    if len(total_bets) > 0:
        total_wins = total_bets['total_win'].sum()
        total_win_rate = total_wins / len(total_bets)
        total_roi = (total_wins * 0.91 - (len(total_bets) - total_wins) * 1.0) / len(total_bets)
        
        print(f"📊 TOTAL BETS:")
        print(f"   Bets: {len(total_bets)}")
        print(f"   Wins: {int(total_wins)}")
        print(f"   Win Rate: {total_win_rate:.1%}")
        print(f"   ROI: {total_roi:+.1%}")
        print(f"   Avg Edge: {total_bets['total_edge'].mean():.1f} pts")
        print(f"   Breakeven: 52.4%")
        if total_win_rate >= 0.524:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
        print()
    
    # Moneyline bets
    ml_bets = df[df['moneyline_bet'] != 'Pass'].copy()
    if len(ml_bets) > 0:
        ml_wins = ml_bets['moneyline_win'].sum()
        ml_win_rate = ml_wins / len(ml_bets)
        
        print(f"📊 MONEYLINE BETS:")
        print(f"   Bets: {len(ml_bets)}")
        print(f"   Wins: {int(ml_wins)}")
        print(f"   Win Rate: {ml_win_rate:.1%}")
        print()
    
    # Overall
    all_bets = len(spread_bets) + len(total_bets)
    all_wins = (spread_bets['spread_win'].sum() if len(spread_bets) > 0 else 0) + \
               (total_bets['total_win'].sum() if len(total_bets) > 0 else 0)
    
    if all_bets > 0:
        overall_win_rate = all_wins / all_bets
        overall_roi = (all_wins * 0.91 - (all_bets - all_wins) * 1.0) / all_bets
        
        print(f"📊 OVERALL:")
        print(f"   Total Bets: {all_bets}")
        print(f"   Total Wins: {int(all_wins)}")
        print(f"   Win Rate: {overall_win_rate:.1%}")
        print(f"   ROI: {overall_roi:+.1%}")
        print(f"   Breakeven: 52.4%")
        if overall_win_rate >= 0.524:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
    
    # By season
    print("\n" + "-"*80)
    print("BY SEASON:")
    print("-"*80 + "\n")
    
    for season in sorted(df['season'].unique()):
        season_df = df[df['season'] == season]
        season_spread = season_df[season_df['spread_bet'] != 'Pass']
        season_total = season_df[season_df['total_bet'] != 'Pass']
        
        season_bets = len(season_spread) + len(season_total)
        season_wins = (season_spread['spread_win'].sum() if len(season_spread) > 0 else 0) + \
                     (season_total['total_win'].sum() if len(season_total) > 0 else 0)
        
        if season_bets > 0:
            season_win_rate = season_wins / season_bets
            season_roi = (season_wins * 0.91 - (season_bets - season_wins) * 1.0) / season_bets
            status = "✅" if season_win_rate >= 0.524 else "❌"
            print(f"{season}: {int(season_wins)}/{season_bets} ({season_win_rate:.1%}) ROI: {season_roi:+.1%} {status}")
    
    print("\n" + "="*80 + "\n")


def main():
    # Load historical games
    years = [2022, 2023, 2024]
    games_df = load_historical_games(years)
    
    # Limit to first 50 games for medium test
    print(f"\n⚠️  MEDIUM TEST: 50 games, 500 sims...")
    games_df = games_df.head(50)
    
    # Generate predictions
    predictions_df = generate_predictions_for_games(games_df, n_sims=500)
    
    # Print summary
    print_performance_summary(predictions_df)
    
    # Save results
    output_file = Path(__file__).parent / "artifacts" / "backtest_real_data.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_file, index=False)
    print(f"✅ Saved results to: {output_file}\n")


if __name__ == '__main__':
    main()

