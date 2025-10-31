#!/usr/bin/env python3
"""
Proper Backtest with Real Historical Odds

Fixes:
1. Uses real market lines from nfl_data_py
2. Correct spread convention (home - away)
3. Bets based on probability vs breakeven, not point edge
4. Proper grading with correct inequalities
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_scores_to_market


# Breakeven probability at -110 odds
BREAKEVEN = 0.5238
EDGE_THRESHOLD = 0.048  # Need 4.8% edge over breakeven to bet


def load_historical_games_with_odds(years: list) -> pd.DataFrame:
    """
    Load historical games with REAL closing lines from daily odds file.
    
    Args:
        years: List of years to load
    
    Returns:
        DataFrame with columns:
            - season, week, away_team, home_team
            - spread_line (home - away, negative = home favored)
            - total_line
            - home_score, away_score (actual results)
    """
    print(f"📊 Loading historical games with odds for {years}...")
    
    try:
        import nfl_data_py as nfl
        
        # Load daily odds file
        odds_file = Path("/Users/steveridder/Git/Football/artifacts/historical_odds_daily/daily_odds_2022_2024_20251028.csv")
        if not odds_file.exists():
            raise RuntimeError(f"Historical odds file not found: {odds_file}")
        
        odds_df = pd.read_csv(odds_file)
        print(f"   Loaded {len(odds_df)} daily odds snapshots")
        
        # Get closing lines (last snapshot before game)
        odds_df['commence_dt'] = pd.to_datetime(odds_df['commence_dt'])
        odds_df['snapshot_dt'] = pd.to_datetime(odds_df['snapshot_dt'])
        
        # Sort and get last snapshot per game
        odds_df = odds_df.sort_values(['game_id', 'snapshot_dt'])
        closing_lines = odds_df.groupby('game_id', as_index=False).last()
        
        print(f"   Extracted {len(closing_lines)} closing lines")
        print(f"   Closing lines columns: {closing_lines.columns.tolist()}")
        
        # Load schedule with actual results
        schedule = nfl.import_schedules(years)
        schedule = schedule[
            (schedule['game_type'] == 'REG') &
            (schedule['home_score'].notna()) &
            (schedule['away_score'].notna())
        ].copy()
        
        # Map full team names to abbreviations
        team_map = {
            'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LA', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
            'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS', 'Washington Football Team': 'WAS'
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
        
        # Ensure numeric types in closing_lines before merge
        closing_lines['spread_home'] = pd.to_numeric(closing_lines['spread_home'], errors='coerce')
        closing_lines['total'] = pd.to_numeric(closing_lines['total'], errors='coerce')
        
        # Merge odds with schedule (rename to avoid conflicts)
        merged = schedule.merge(
            closing_lines[['merge_key', 'spread_home', 'total']].rename(columns={'total': 'closing_total'}),
            on='merge_key',
            how='inner'
        )
        
        # Drop rows with missing odds
        merged = merged[merged['spread_home'].notna() & merged['closing_total'].notna()].copy()
        
        print(f"   Merged {len(merged)} games with valid closing lines")
        print(f"   Seasons: {sorted(merged['season'].unique())}")
        print(f"   Weeks: {merged['week'].min()}-{merged['week'].max()}")
        
        # Rename columns for consistency
        merged = merged.rename(columns={
            'spread_home': 'spread_line',
            'closing_total': 'total_line'
        })
        
        print(f"   Final dataset: {len(merged)} games with valid odds\n")
        
        # Select only needed columns and ensure no duplicates
        result = merged[['season', 'week', 'gameday', 'gametime', 'away_team', 'home_team', 
                        'spread_line', 'total_line', 'away_score', 'home_score']].copy()
        
        # Remove duplicate columns if any
        result = result.loc[:, ~result.columns.duplicated()]
        
        return result
    
    except Exception as e:
        import traceback
        print(f"\n❌ Error details:")
        traceback.print_exc()
        raise RuntimeError(f"Failed to load historical odds: {e}")


def generate_predictions_proper(games_df: pd.DataFrame, n_sims: int = 500) -> pd.DataFrame:
    """
    Generate predictions with proper centering and probability-based betting.
    
    Args:
        games_df: DataFrame with game info and market lines
        n_sims: Number of simulations per game
    
    Returns:
        DataFrame with predictions and grades
    """
    print(f"\n🎲 Generating predictions for {len(games_df)} games...")
    print(f"   Simulations per game: {n_sims}\n")
    
    results = []
    
    for idx in range(len(games_df)):
        game = games_df.iloc[idx]
        away = game['away_team']
        home = game['home_team']
        season = int(game['season'])
        week = int(game['week'])
        
        # Market lines (home - away convention)
        # Use .item() to get scalar value from potential Series
        market_spread_home = game['spread_line'] if isinstance(game['spread_line'], (int, float)) else game['spread_line'].item()
        market_total = game['total_line'] if isinstance(game['total_line'], (int, float)) else game['total_line'].item()
        
        if (idx + 1) % 25 == 0:
            print(f"[{idx+1}/{len(games_df)}] Processing...")
        
        try:
            # Load profiles
            data_dir = Path(__file__).parent / "data" / "nflfastR"
            away_profile = TeamProfile(away, season, week, data_dir)
            home_profile = TeamProfile(home, season, week, data_dir)
            
            # Run simulation
            simulator = GameSimulator(away_profile, home_profile)
            
            home_scores = []
            away_scores = []
            
            for _ in range(n_sims):
                result = simulator.simulate_game()
                away_scores.append(result['away_score'])
                home_scores.append(result['home_score'])
            
            home_scores = np.array(home_scores)
            away_scores = np.array(away_scores)
            
            # Store raw stats
            raw_spread_mean = np.mean(home_scores - away_scores)
            raw_total_mean = np.mean(home_scores + away_scores)
            
            # CENTER TO MARKET (THE CORRECT WAY)
            home_adj, away_adj = center_scores_to_market(
                home_scores, away_scores, market_spread_home, market_total
            )
            
            # Derive centered distributions
            spread_sim = home_adj - away_adj  # home - away
            total_sim = home_adj + away_adj
            
            # Verify centering
            centered_spread_mean = np.mean(spread_sim)
            centered_total_mean = np.mean(total_sim)
            
            if idx < 3:  # Print first 3 for verification
                print(f"\n{away} @ {home}:")
                print(f"  RAW: spread={raw_spread_mean:.2f}, total={raw_total_mean:.2f}")
                print(f"  CENTERED: spread={centered_spread_mean:.2f}, total={centered_total_mean:.2f}")
                print(f"  MARKET: spread={market_spread_home:.2f}, total={market_total:.2f}")
            
            # Calculate probabilities FROM CENTERED DISTRIBUTIONS
            p_home_cover = np.mean((spread_sim - market_spread_home) > 0)
            p_away_cover = 1 - p_home_cover
            p_over = np.mean(total_sim > market_total)
            p_under = 1 - p_over
            p_home_win = np.mean(spread_sim > 0)
            
            # BETTING DECISIONS BASED ON PROBABILITY VS BREAKEVEN
            # Spread bet
            if p_home_cover > BREAKEVEN + EDGE_THRESHOLD:
                spread_bet = "Home ATS"
                spread_confidence = p_home_cover
            elif p_away_cover > BREAKEVEN + EDGE_THRESHOLD:
                spread_bet = "Away ATS"
                spread_confidence = p_away_cover
            else:
                spread_bet = "Pass"
                spread_confidence = max(p_home_cover, p_away_cover)
            
            # Total bet
            if p_over > BREAKEVEN + EDGE_THRESHOLD:
                total_bet = "Over"
                total_confidence = p_over
            elif p_under > BREAKEVEN + EDGE_THRESHOLD:
                total_bet = "Under"
                total_confidence = p_under
            else:
                total_bet = "Pass"
                total_confidence = max(p_over, p_under)
            
            # Moneyline bet (for tracking only, no grading without ML odds)
            if p_home_win >= 0.65:
                moneyline_bet = home
            elif p_home_win <= 0.35:
                moneyline_bet = away
            else:
                moneyline_bet = "Pass"
            
            # GRADING WITH ACTUAL RESULTS
            actual_home = float(game['home_score'])
            actual_away = float(game['away_score'])
            actual_margin = actual_home - actual_away  # home - away
            actual_total = actual_home + actual_away
            
            # Grade spread bet (CORRECT INEQUALITIES)
            spread_win = None
            if spread_bet == "Home ATS":
                # Home covers if actual margin beats the spread
                spread_win = int((actual_margin - market_spread_home) > 0)
            elif spread_bet == "Away ATS":
                # Away covers if home fails to cover
                spread_win = int((actual_margin - market_spread_home) < 0)
            
            # Grade total bet
            total_win = None
            if total_bet == "Over":
                total_win = int(actual_total > market_total)
            elif total_bet == "Under":
                total_win = int(actual_total < market_total)
            
            # Grade moneyline (for tracking)
            ml_win = None
            if moneyline_bet == home:
                ml_win = int(actual_margin > 0)
            elif moneyline_bet == away:
                ml_win = int(actual_margin < 0)
            
            results.append({
                'game_id': f"{away}@{home}_W{week}",
                'season': season,
                'week': week,
                'away_team': away,
                'home_team': home,
                
                # Market
                'market_spread': market_spread_home,
                'market_total': market_total,
                
                # Our predictions (centered)
                'our_spread': round(centered_spread_mean, 1),
                'our_total': round(centered_total_mean, 1),
                
                # Raw predictions (for diagnostics)
                'raw_spread': round(raw_spread_mean, 1),
                'raw_total': round(raw_total_mean, 1),
                
                # Probabilities
                'p_home_cover': round(p_home_cover, 3),
                'p_away_cover': round(p_away_cover, 3),
                'p_over': round(p_over, 3),
                'p_under': round(p_under, 3),
                'p_home_win': round(p_home_win, 3),
                
                # Bets
                'spread_bet': spread_bet,
                'spread_confidence': round(spread_confidence, 3),
                'total_bet': total_bet,
                'total_confidence': round(total_confidence, 3),
                'moneyline_bet': moneyline_bet,
                
                # Actual results
                'actual_home': actual_home,
                'actual_away': actual_away,
                'actual_margin': actual_margin,
                'actual_total': actual_total,
                
                # Grading
                'spread_win': spread_win,
                'total_win': total_win,
                'ml_win': ml_win,
            })
            
        except Exception as e:
            print(f"  ⚠️  Error on {away}@{home}: {e}")
            continue
    
    return pd.DataFrame(results)


def print_performance_summary(df: pd.DataFrame):
    """Print detailed performance summary."""
    print("\n" + "="*80)
    print("BETTING PERFORMANCE SUMMARY (PROPER SCORING)")
    print("="*80 + "\n")
    
    # Spread bets
    spread_bets = df[df['spread_bet'] != 'Pass'].copy()
    if len(spread_bets) > 0:
        spread_wins = spread_bets['spread_win'].sum()
        spread_win_rate = spread_wins / len(spread_bets)
        
        # ROI calculation (assume -110 odds)
        spread_roi = (spread_wins * 0.909 - (len(spread_bets) - spread_wins) * 1.0) / len(spread_bets)
        
        print(f"📊 SPREAD BETS:")
        print(f"   Bets: {len(spread_bets)}")
        print(f"   Wins: {int(spread_wins)}")
        print(f"   Win Rate: {spread_win_rate:.1%}")
        print(f"   ROI: {spread_roi:+.1%}")
        print(f"   Avg Confidence: {spread_bets['spread_confidence'].mean():.1%}")
        print(f"   Breakeven: {BREAKEVEN:.1%}")
        if spread_win_rate >= BREAKEVEN:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
        print()
    
    # Total bets
    total_bets = df[df['total_bet'] != 'Pass'].copy()
    if len(total_bets) > 0:
        total_wins = total_bets['total_win'].sum()
        total_win_rate = total_wins / len(total_bets)
        total_roi = (total_wins * 0.909 - (len(total_bets) - total_wins) * 1.0) / len(total_bets)
        
        print(f"📊 TOTAL BETS:")
        print(f"   Bets: {len(total_bets)}")
        print(f"   Wins: {int(total_wins)}")
        print(f"   Win Rate: {total_win_rate:.1%}")
        print(f"   ROI: {total_roi:+.1%}")
        print(f"   Avg Confidence: {total_bets['total_confidence'].mean():.1%}")
        print(f"   Breakeven: {BREAKEVEN:.1%}")
        if total_win_rate >= BREAKEVEN:
            print(f"   ✅ PROFITABLE")
        else:
            print(f"   ❌ NOT PROFITABLE")
        print()
    
    # Overall
    all_bets = len(spread_bets) + len(total_bets)
    all_wins = (spread_bets['spread_win'].sum() if len(spread_bets) > 0 else 0) + \
               (total_bets['total_win'].sum() if len(total_bets) > 0 else 0)
    
    if all_bets > 0:
        overall_win_rate = all_wins / all_bets
        overall_roi = (all_wins * 0.909 - (all_bets - all_wins) * 1.0) / all_bets
        
        print(f"📊 OVERALL:")
        print(f"   Total Bets: {all_bets}")
        print(f"   Total Wins: {int(all_wins)}")
        print(f"   Win Rate: {overall_win_rate:.1%}")
        print(f"   ROI: {overall_roi:+.1%}")
        print(f"   Breakeven: {BREAKEVEN:.1%}")
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
        season_wins = (season_spread['spread_win'].sum() if len(season_spread) > 0 else 0) + \
                     (season_total['total_win'].sum() if len(season_total) > 0 else 0)
        
        if season_bets > 0:
            season_win_rate = season_wins / season_bets
            season_roi = (season_wins * 0.909 - (season_bets - season_wins) * 1.0) / season_bets
            status = "✅" if season_win_rate >= BREAKEVEN else "❌"
            print(f"{season}: {int(season_wins)}/{season_bets} ({season_win_rate:.1%}) ROI: {season_roi:+.1%} {status}")
    
    print("\n" + "="*80 + "\n")


def main():
    # Load historical games with REAL odds
    years = [2022, 2023, 2024]
    
    try:
        games_df = load_historical_games_with_odds(years)
    except RuntimeError as e:
        print(f"❌ {e}")
        return
    
    # Full backtest on ALL games
    print(f"\n🚀 FULL BACKTEST: {len(games_df)} games, 500 sims each...")
    print(f"   Estimated time: ~{len(games_df) * 10 / 60:.0f} minutes...\n")
    # games_df = games_df.head(50)  # Comment out - use all games
    
    # Generate predictions
    predictions_df = generate_predictions_proper(games_df, n_sims=500)
    
    # Print summary
    print_performance_summary(predictions_df)
    
    # Save results
    output_file = Path(__file__).parent / "artifacts" / "backtest_proper.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_file, index=False)
    print(f"✅ Saved results to: {output_file}\n")


if __name__ == '__main__':
    main()

