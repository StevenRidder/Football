#!/usr/bin/env python3
"""
FAST Backtest with Parallelization

Fixes:
1. Correct team abbreviations (LAR, WAS)
2. Push handling (3-way grading)
3. Parallel game processing
4. 200 random games, 200 sims
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from multiprocessing import Pool, cpu_count

sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_scores_to_market


# Breakeven probability at -110 odds
BREAKEVEN = 0.5238
EDGE_THRESHOLD = 0.025  # 2.5% edge (not 4.8%)


def load_historical_games_with_odds(years: list) -> pd.DataFrame:
    """Load historical games with REAL closing lines."""
    print(f"📊 Loading historical games with odds for {years}...")
    
    try:
        import nfl_data_py as nfl
        
        # Load daily odds file
        odds_file = Path("/Users/steveridder/Git/Football/artifacts/historical_odds_daily/daily_odds_2022_2024_20251028.csv")
        if not odds_file.exists():
            raise RuntimeError(f"Historical odds file not found: {odds_file}")
        
        odds_df = pd.read_csv(odds_file)
        print(f"   Loaded {len(odds_df)} daily odds snapshots")
        
        # Get closing lines
        odds_df['commence_dt'] = pd.to_datetime(odds_df['commence_dt'])
        odds_df['snapshot_dt'] = pd.to_datetime(odds_df['snapshot_dt'])
        odds_df = odds_df.sort_values(['game_id', 'snapshot_dt'])
        closing_lines = odds_df.groupby('game_id', as_index=False).last()
        
        print(f"   Extracted {len(closing_lines)} closing lines")
        
        # Load schedule
        schedule = nfl.import_schedules(years)
        schedule = schedule[
            (schedule['game_type'] == 'REG') &
            (schedule['home_score'].notna()) &
            (schedule['away_score'].notna())
        ].copy()
        
        # FIXED team map (LAR, WAS)
        team_map = {
            'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LAR',  # FIXED: was LA
            'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
            'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN', 
            'Washington Commanders': 'WAS',  # All WAS
            'Washington Football Team': 'WAS',
            'Washington Redskins': 'WAS'
        }
        
        closing_lines['away_team_abbr'] = closing_lines['away_team'].map(team_map)
        closing_lines['home_team_abbr'] = closing_lines['home_team'].map(team_map)
        
        # Create merge key
        closing_lines['merge_key'] = (closing_lines['away_team_abbr'] + '_' + 
                                      closing_lines['home_team_abbr'] + '_' + 
                                      closing_lines['season'].astype(str))
        schedule['merge_key'] = (schedule['away_team'] + '_' + 
                                schedule['home_team'] + '_' + 
                                schedule['season'].astype(str))
        
        # Ensure numeric
        closing_lines['spread_home'] = pd.to_numeric(closing_lines['spread_home'], errors='coerce')
        closing_lines['total'] = pd.to_numeric(closing_lines['total'], errors='coerce')
        
        # Merge
        merged = schedule.merge(
            closing_lines[['merge_key', 'spread_home', 'total']].rename(columns={'total': 'closing_total'}),
            on='merge_key',
            how='inner'
        )
        
        merged = merged[merged['spread_home'].notna() & merged['closing_total'].notna()].copy()
        
        print(f"   Merged {len(merged)} games with valid closing lines")
        
        # Select only needed columns BEFORE renaming
        result = merged[['season', 'week', 'gameday', 'gametime', 'away_team', 'home_team', 
                        'spread_home', 'closing_total', 'away_score', 'home_score']].copy()
        
        # Remove duplicates
        result = result.loc[:, ~result.columns.duplicated()]
        
        # Now rename
        result = result.rename(columns={
            'spread_home': 'spread_line',
            'closing_total': 'total_line'
        })
        
        # Sanity check odds
        print(f"\n📋 Odds sanity check:")
        print(f"   Spread range: {result['spread_line'].min():.1f} to {result['spread_line'].max():.1f}")
        print(f"   Total range: {result['total_line'].min():.1f} to {result['total_line'].max():.1f}\n")
        
        return result
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Failed to load historical odds: {e}")


def simulate_single_game(args):
    """Simulate a single game (for parallel processing)."""
    idx, game, n_sims, total_games = args
    
    away = game['away_team']
    home = game['home_team']
    season = int(game['season'])
    week = int(game['week'])
    
    # Print progress every 10 games
    if (idx + 1) % 10 == 0:
        print(f"   [{idx+1}/{total_games}] {away}@{home} completed")
    
    market_spread_home = game['spread_line'] if isinstance(game['spread_line'], (int, float)) else game['spread_line'].item()
    market_total = game['total_line'] if isinstance(game['total_line'], (int, float)) else game['total_line'].item()
    
    try:
        # Load profiles
        data_dir = Path(__file__).parent / "data" / "nflfastR"
        away_profile = TeamProfile(away, season, week, data_dir)
        home_profile = TeamProfile(home, season, week, data_dir)
        
        # Run simulation with fixed seed for reproducibility
        simulator = GameSimulator(away_profile, home_profile)
        np.random.seed(hash(f"{season}-{week}-{away}-{home}") % (2**32))
        
        home_scores = []
        away_scores = []
        
        for _ in range(n_sims):
            result = simulator.simulate_game()
            away_scores.append(result['away_score'])
            home_scores.append(result['home_score'])
        
        home_scores = np.array(home_scores)
        away_scores = np.array(away_scores)
        
        # Raw stats
        raw_spread_mean = np.mean(home_scores - away_scores)
        raw_total_mean = np.mean(home_scores + away_scores)
        
        # CENTER TO MARKET
        home_adj, away_adj = center_scores_to_market(
            home_scores, away_scores, market_spread_home, market_total
        )
        
        # Check for negative scores after centering
        neg_hits = (home_adj < 0).sum() + (away_adj < 0).sum()
        
        # Centered distributions
        spread_sim = home_adj - away_adj
        total_sim = home_adj + away_adj
        
        centered_spread_mean = np.mean(spread_sim)
        centered_total_mean = np.mean(total_sim)
        
        # Verify centering
        assert abs(centered_spread_mean - market_spread_home) < 0.1, f"Spread centering failed: {centered_spread_mean} vs {market_spread_home}"
        assert abs(centered_total_mean - market_total) < 0.1, f"Total centering failed: {centered_total_mean} vs {market_total}"
        
        # Probabilities
        p_home_cover = np.mean((spread_sim - market_spread_home) > 0)
        p_away_cover = 1 - p_home_cover
        p_over = np.mean(total_sim > market_total)
        p_under = 1 - p_over
        p_home_win = np.mean(spread_sim > 0)
        
        # BETTING DECISIONS (2.5% edge threshold)
        if p_home_cover > BREAKEVEN + EDGE_THRESHOLD:
            spread_bet = "Home ATS"
            spread_confidence = p_home_cover
        elif p_away_cover > BREAKEVEN + EDGE_THRESHOLD:
            spread_bet = "Away ATS"
            spread_confidence = p_away_cover
        else:
            spread_bet = "Pass"
            spread_confidence = max(p_home_cover, p_away_cover)
        
        if p_over > BREAKEVEN + EDGE_THRESHOLD:
            total_bet = "Over"
            total_confidence = p_over
        elif p_under > BREAKEVEN + EDGE_THRESHOLD:
            total_bet = "Under"
            total_confidence = p_under
        else:
            total_bet = "Pass"
            total_confidence = max(p_over, p_under)
        
        # GRADING WITH PUSH HANDLING
        actual_home = float(game['home_score'])
        actual_away = float(game['away_score'])
        actual_margin = actual_home - actual_away
        actual_total = actual_home + actual_away
        
        # Spread grading (3-way: win/loss/push)
        spread_grade = None
        if spread_bet == "Home ATS":
            diff = actual_margin - market_spread_home
            spread_grade = 1.0 if diff > 0 else (0.0 if diff < 0 else 0.5)  # 0.5 = push
        elif spread_bet == "Away ATS":
            diff = actual_margin - market_spread_home
            spread_grade = 1.0 if diff < 0 else (0.0 if diff > 0 else 0.5)
        
        # Total grading (3-way)
        total_grade = None
        total_diff = actual_total - market_total
        if total_bet == "Over":
            total_grade = 1.0 if total_diff > 0 else (0.0 if total_diff < 0 else 0.5)
        elif total_bet == "Under":
            total_grade = 1.0 if total_diff < 0 else (0.0 if total_diff > 0 else 0.5)
        
        return {
            'game_id': f"{away}@{home}_W{week}",
            'season': season,
            'week': week,
            'away_team': away,
            'home_team': home,
            'market_spread': market_spread_home,
            'market_total': market_total,
            'our_spread': round(centered_spread_mean, 1),
            'our_total': round(centered_total_mean, 1),
            'raw_spread': round(raw_spread_mean, 1),
            'raw_total': round(raw_total_mean, 1),
            'p_home_cover': round(p_home_cover, 3),
            'p_over': round(p_over, 3),
            'p_home_win': round(p_home_win, 3),
            'spread_bet': spread_bet,
            'spread_confidence': round(spread_confidence, 3),
            'total_bet': total_bet,
            'total_confidence': round(total_confidence, 3),
            'actual_home': actual_home,
            'actual_away': actual_away,
            'actual_margin': actual_margin,
            'actual_total': actual_total,
            'spread_grade': spread_grade,
            'total_grade': total_grade,
            'neg_clips': neg_hits,
        }
        
    except Exception as e:
        print(f"  ⚠️  Error on {away}@{home}: {e}")
        return None


def print_performance_summary(df: pd.DataFrame):
    """Print performance summary with push handling."""
    print("\n" + "="*80)
    print("BETTING PERFORMANCE SUMMARY")
    print("="*80 + "\n")
    
    # Spread bets
    spread_bets = df[df['spread_bet'] != 'Pass'].copy()
    if len(spread_bets) > 0:
        wins = (spread_bets['spread_grade'] == 1.0).sum()
        pushes = (spread_bets['spread_grade'] == 0.5).sum()
        losses = (spread_bets['spread_grade'] == 0.0).sum()
        win_rate = wins / len(spread_bets)
        
        # ROI: wins get +0.909, losses get -1.0, pushes get 0
        roi = (wins * 0.909 - losses * 1.0) / len(spread_bets)
        
        print(f"📊 SPREAD BETS:")
        print(f"   Bets: {len(spread_bets)}")
        print(f"   Wins: {int(wins)} | Pushes: {int(pushes)} | Losses: {int(losses)}")
        print(f"   Win Rate: {win_rate:.1%}")
        print(f"   ROI: {roi:+.1%}")
        print(f"   Avg Confidence: {spread_bets['spread_confidence'].mean():.1%}")
        print(f"   Breakeven: {BREAKEVEN:.1%}")
        if win_rate >= BREAKEVEN:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
        print()
    
    # Total bets
    total_bets = df[df['total_bet'] != 'Pass'].copy()
    if len(total_bets) > 0:
        wins = (total_bets['total_grade'] == 1.0).sum()
        pushes = (total_bets['total_grade'] == 0.5).sum()
        losses = (total_bets['total_grade'] == 0.0).sum()
        win_rate = wins / len(total_bets)
        roi = (wins * 0.909 - losses * 1.0) / len(total_bets)
        
        print(f"📊 TOTAL BETS:")
        print(f"   Bets: {len(total_bets)}")
        print(f"   Wins: {int(wins)} | Pushes: {int(pushes)} | Losses: {int(losses)}")
        print(f"   Win Rate: {win_rate:.1%}")
        print(f"   ROI: {roi:+.1%}")
        print(f"   Avg Confidence: {total_bets['total_confidence'].mean():.1%}")
        if win_rate >= BREAKEVEN:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
        print()
    
    # Overall
    all_bets = len(spread_bets) + len(total_bets)
    if all_bets > 0:
        all_wins = ((spread_bets['spread_grade'] == 1.0).sum() if len(spread_bets) > 0 else 0) + \
                   ((total_bets['total_grade'] == 1.0).sum() if len(total_bets) > 0 else 0)
        all_losses = ((spread_bets['spread_grade'] == 0.0).sum() if len(spread_bets) > 0 else 0) + \
                     ((total_bets['total_grade'] == 0.0).sum() if len(total_bets) > 0 else 0)
        
        overall_win_rate = all_wins / all_bets
        overall_roi = (all_wins * 0.909 - all_losses * 1.0) / all_bets
        
        print(f"📊 OVERALL:")
        print(f"   Total Bets: {all_bets}")
        print(f"   Total Wins: {int(all_wins)}")
        print(f"   Win Rate: {overall_win_rate:.1%}")
        print(f"   ROI: {overall_roi:+.1%}")
        if overall_win_rate >= BREAKEVEN:
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
        season_wins = ((season_spread['spread_grade'] == 1.0).sum() if len(season_spread) > 0 else 0) + \
                     ((season_total['total_grade'] == 1.0).sum() if len(season_total) > 0 else 0)
        
        if season_bets > 0:
            season_win_rate = season_wins / season_bets
            status = "✅" if season_win_rate >= BREAKEVEN else "❌"
            print(f"{season}: {int(season_wins)}/{season_bets} ({season_win_rate:.1%}) {status}")
    
    print("\n" + "="*80 + "\n")


def main():
    years = [2022, 2023, 2024]
    
    try:
        games_df = load_historical_games_with_odds(years)
    except RuntimeError as e:
        print(f"❌ {e}")
        return
    
    # Sample 200 random games
    print(f"🎲 Sampling 200 random games from {len(games_df)} total...")
    games_df = games_df.sample(200, random_state=42)
    print(f"   Seasons covered: {sorted(games_df['season'].unique())}")
    print(f"   Weeks covered: {games_df['week'].min()}-{games_df['week'].max()}\n")
    
    # Parallel processing
    n_cores = cpu_count()
    print(f"🚀 Running on {n_cores} CPU cores in parallel...")
    print(f"   200 games × 200 sims = 40,000 game simulations")
    print(f"   Estimated time: ~3-5 minutes\n")
    
    # Prepare args
    total_games = len(games_df)
    args = [(i, games_df.iloc[i], 200, total_games) for i in range(total_games)]
    
    # Run in parallel
    print(f"Starting parallel simulation...\n")
    with Pool(n_cores) as pool:
        results = pool.map(simulate_single_game, args)
    
    # Filter out errors
    results = [r for r in results if r is not None]
    predictions_df = pd.DataFrame(results)
    
    print(f"\n✅ Completed {len(predictions_df)} games successfully")
    
    # Print summary
    print_performance_summary(predictions_df)
    
    # Save results
    output_file = Path(__file__).parent / "artifacts" / "backtest_fast.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_file, index=False)
    print(f"✅ Saved results to: {output_file}\n")


if __name__ == '__main__':
    main()

