"""
Generate predictions for Week 9 and 10 games using the simulator.

This script runs simulations for future games without results.
Uses the same calibration approach as backtest_all_games_conviction.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_scores_to_market
from concurrent.futures import ProcessPoolExecutor
import time
from scipy.stats import norm

# Conviction tiers (same as backtest_all_games_conviction.py)
LOW_EDGE = 0.0
MEDIUM_EDGE = 0.03
HIGH_EDGE = 0.06
MAX_EDGE_CAP = 0.25

BREAKEVEN = 0.524
N_SIMS = 2000  # Increased from 100 for more accurate conviction levels

# Linear calibration parameters
LINEAR_ALPHA = 26.45
LINEAR_BETA = 0.571

def simulate_one_game(args):
    """Simulate one game and return predictions."""
    idx, row, n_sims = args
    
    try:
        away = row['away_team']
        home = row['home_team']
        season = int(row.get('season', 2025))
        week = int(row.get('week', 9))
        spread_line = float(row.get('spread_line', 0.0))
        total_line = float(row.get('closing_total', row.get('total_line', 45.0)))
        
        # Load team profiles
        data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
        home_profile = TeamProfile(home, season, week, data_dir=data_dir, debug=False)
        away_profile = TeamProfile(away, season, week, data_dir=data_dir, debug=False)
        
        # Run simulation
        game_id = row.get('game_id', f"{season}_{week:02d}_{away}_{home}")
        sim = GameSimulator(home_profile, away_profile, 
                           game_id=game_id, season=season, week=week)
        home_scores = []
        away_scores = []
        
        for sim_i in range(n_sims):
            np.random.seed(hash(f"{game_id}_{sim_i}") % (2**32))
            result = sim.simulate_game()
            home_scores.append(result['home_score'])
            away_scores.append(result['away_score'])
        
        home_scores = np.asarray(home_scores)
        away_scores = np.asarray(away_scores)
        
        # Store raw (pre-centered) stats for calibration
        spreads_raw = home_scores - away_scores
        totals_raw = home_scores + away_scores
        spread_raw_mean = float(np.mean(spreads_raw))
        total_raw_mean = float(np.mean(totals_raw))
        spread_raw_sd = float(np.std(spreads_raw))
        total_raw_sd = float(np.std(totals_raw))
        
        # Market centering (OPTIONAL - same as backtest)
        USE_MARKET_CENTERING = True
        
        if USE_MARKET_CENTERING:
            home_c, away_c = center_scores_to_market(
                home_scores, away_scores, spread_line, total_line
            )
        else:
            home_c, away_c = home_scores, away_scores
        
        spreads_c = home_c - away_c
        totals_c = home_c + away_c
        
        # Calculate probabilities - same approach as backtest_all_games_conviction.py
        p_home_cover_centered = np.mean(spreads_c > spread_line)
        p_over_centered = np.mean(totals_c > total_line)
        
        # Linear calibration (score-level)
        calibrated_total_mean = LINEAR_ALPHA + LINEAR_BETA * total_raw_mean
        calibrated_total_sd = total_raw_sd  # Preserve variance
        
        raw_home_mean = (total_raw_mean + spread_raw_mean) / 2.0
        raw_away_mean = (total_raw_mean - spread_raw_mean) / 2.0
        calibrated_home_mean = LINEAR_ALPHA / 2.0 + LINEAR_BETA * raw_home_mean
        calibrated_away_mean = LINEAR_ALPHA / 2.0 + LINEAR_BETA * raw_away_mean
        calibrated_spread_mean = calibrated_home_mean - calibrated_away_mean
        calibrated_spread_sd = spread_raw_sd  # Preserve variance
        
        # Store calibrated mean scores for frontend display (NOT market-centered)
        # CRITICAL: Use calibrated values, NOT market-centered values
        home_score_mean = calibrated_home_mean  # This is: LINEAR_ALPHA/2 + LINEAR_BETA * raw_home_mean
        away_score_mean = calibrated_away_mean  # This is: LINEAR_ALPHA/2 + LINEAR_BETA * raw_away_mean
        
        # DEBUG: Verify calibration was applied
        if abs(home_score_mean - np.mean(home_c)) < 0.1:
            # This would mean calibrated = market-centered, which is wrong
            print(f"⚠️  WARNING: {away}@{home}: Calibrated score matches market-centered! This should not happen.")
            print(f"   Raw: {raw_away_mean:.2f}-{raw_home_mean:.2f}")
            print(f"   Calibrated: {calibrated_away_mean:.2f}-{calibrated_home_mean:.2f}")
            print(f"   Market-centered: {np.mean(away_c):.2f}-{np.mean(home_c):.2f}")
        
        # Calculate probabilities using normal approximation
        p_home_cover_linear = 1 - norm.cdf(
            (spread_line - calibrated_spread_mean) / max(calibrated_spread_sd, 1e-6)
        )
        p_away_cover_linear = 1 - p_home_cover_linear
        p_over_linear = 1 - norm.cdf(
            (total_line - calibrated_total_mean) / max(calibrated_total_sd, 1e-6)
        )
        p_under_linear = 1 - p_over_linear
        
        # Clip to valid range
        p_home_cover_linear = np.clip(p_home_cover_linear, 0.01, 0.99)
        p_over_linear = np.clip(p_over_linear, 0.01, 0.99)
        p_away_cover_linear = 1 - p_home_cover_linear
        p_under_linear = 1 - p_over_linear
        
        # Try isotonic calibrators (priority over linear)
        p_home_cover = p_home_cover_linear
        p_away_cover = p_away_cover_linear
        p_over = p_over_linear
        p_under = p_under_linear
        use_calibration = 'linear'
        
        try:
            import pickle
            artifacts_dir = Path(__file__).parent.parent / "artifacts"
            isotonic_file = artifacts_dir / "isotonic_calibrators.pkl"
            
            if isotonic_file.exists():
                with open(isotonic_file, 'rb') as f:
                    isotonic_calibrators = pickle.load(f)
                
                if 'spread' in isotonic_calibrators:
                    spread_cal = isotonic_calibrators['spread']
                    if spread_cal.is_fitted:
                        p_home_cover_isotonic = spread_cal.predict(
                            np.array([spread_raw_mean]),
                            np.array([spread_raw_sd]),
                            np.array([spread_line])
                        )[0]
                        p_home_cover = np.clip(p_home_cover_isotonic, 0.01, 0.99)
                        p_away_cover = 1 - p_home_cover
                        use_calibration = 'isotonic'
                
                if 'total' in isotonic_calibrators:
                    total_cal = isotonic_calibrators['total']
                    if total_cal.is_fitted:
                        p_over_isotonic = total_cal.predict(
                            np.array([total_raw_mean]),
                            np.array([total_raw_sd]),
                            np.array([total_line])
                        )[0]
                        p_over = np.clip(p_over_isotonic, 0.01, 0.99)
                        p_under = 1 - p_over
        except Exception:
            pass  # Fall back to linear
        
        # Determine bets with conviction levels
        spread_bet = None
        spread_edge = 0
        spread_conviction = None
        
        if p_home_cover > BREAKEVEN:
            spread_bet = 'HOME'
            spread_edge = min(p_home_cover - BREAKEVEN, MAX_EDGE_CAP)
        elif p_away_cover > BREAKEVEN:
            spread_bet = 'AWAY'
            spread_edge = min(p_away_cover - BREAKEVEN, MAX_EDGE_CAP)
        
        if spread_bet:
            if spread_edge >= HIGH_EDGE:
                spread_conviction = 'HIGH'
            elif spread_edge >= MEDIUM_EDGE:
                spread_conviction = 'MEDIUM'
            else:
                spread_conviction = 'LOW'
        
        total_bet = None
        total_edge = 0
        total_conviction = None
        
        if p_over > BREAKEVEN:
            total_bet = 'OVER'
            total_edge = min(p_over - BREAKEVEN, MAX_EDGE_CAP)
        elif p_under > BREAKEVEN:
            total_bet = 'UNDER'
            total_edge = min(p_under - BREAKEVEN, MAX_EDGE_CAP)
        
        if total_bet:
            if total_edge >= HIGH_EDGE:
                total_conviction = 'HIGH'
            elif total_edge >= MEDIUM_EDGE:
                total_conviction = 'MEDIUM'
            else:
                total_conviction = 'LOW'
        
        return {
            'game_id': row.get('game_id', f"{season}_{week:02d}_{away}_{home}"),
            'season': season,
            'week': week,
            'away_team': away,
            'home_team': home,
            'spread_line': spread_line,
            'total_line': total_line,
            # Mean scores (centered) for frontend display - THIS IS "OUR SCORE"
            'home_score_mean': home_score_mean,
            'away_score_mean': away_score_mean,
            'spread_mean': spreads_c.mean(),
            'total_mean': totals_c.mean(),
            'spread_sd': spreads_c.std(),
            'total_sd': totals_c.std(),
            # Raw (pre-centered) for calibration
            'spread_raw': spread_raw_mean,
            'spread_raw_sd': spread_raw_sd,
            'total_raw': total_raw_mean,
            'total_raw_sd': total_raw_sd,
            'p_home_cover': p_home_cover,
            'p_away_cover': p_away_cover,
            'p_over': p_over,
            'p_under': p_under,
            'p_home_cover_centered': p_home_cover_centered,
            'p_over_centered': p_over_centered,
            'calibration_method': use_calibration,
            'spread_bet': spread_bet,
            'spread_edge': spread_edge,
            'spread_conviction': spread_conviction,
            'total_bet': total_bet,
            'total_edge': total_edge,
            'total_conviction': total_conviction,
            # No actual scores for future games
            'actual_home_score': np.nan,
            'actual_away_score': np.nan,
            'actual_spread': np.nan,
            'actual_total': np.nan,
        }
    
    except Exception as e:
        print(f"❌ Error on game {idx} ({away}@{home}): {e}")
        return None

def load_week_games(week):
    """Load games for a specific week, prioritizing Odds API data."""
    import nfl_data_py as nfl
    
    schedule = nfl.import_schedules([2025])
    schedule = schedule[schedule['game_type'] == 'REG'].copy()
    schedule = schedule[schedule['week'] == week].copy()
    
    # CRITICAL: Fetch odds from Odds API first (real-time market data)
    print(f"   📡 Fetching odds from Odds API for Week {week}...")
    try:
        from scripts.fetch_week9_odds import fetch_week9_odds
        odds_dict = fetch_week9_odds()
        
        if odds_dict:
            print(f"   ✅ Found odds for {len(odds_dict)} games from Odds API")
            
            # Merge Odds API data into schedule
            def apply_odds(row):
                key = (row['away_team'], row['home_team'])
                if key in odds_dict:
                    odds = odds_dict[key]
                    return pd.Series({
                        'spread_line': odds['spread_line'],
                        'closing_total': odds['total_line'],
                        'total_line': odds['total_line']
                    })
                else:
                    # Fallback to nfl_data_py if Odds API doesn't have this game
                    return pd.Series({
                        'spread_line': row.get('spread_line', 0.0),
                        'closing_total': row.get('total_line', 45.0),
                        'total_line': row.get('total_line', 45.0)
                    })
            
            odds_df = schedule.apply(apply_odds, axis=1)
            schedule['spread_line'] = odds_df['spread_line']
            schedule['closing_total'] = odds_df['closing_total']
            schedule['total_line'] = odds_df['total_line']
            
            print(f"   ✅ Applied Odds API data to {len(schedule)} games")
        else:
            print(f"   ⚠️  Odds API returned no data, using nfl_data_py fallback")
            # Fallback to nfl_data_py
            schedule = schedule.rename(columns={
                'total_line': 'closing_total',
                'spread_line': 'spread_line'
            }).copy()
            schedule['spread_line'] = schedule['spread_line'].fillna(0.0)
            schedule['closing_total'] = schedule['closing_total'].fillna(45.0)
            schedule['total_line'] = schedule['closing_total']
    except Exception as e:
        print(f"   ⚠️  Error fetching Odds API: {e}, using nfl_data_py fallback")
        import traceback
        traceback.print_exc()
        # Fallback to nfl_data_py
        schedule = schedule.rename(columns={
            'total_line': 'closing_total',
            'spread_line': 'spread_line'
        }).copy()
        schedule['spread_line'] = schedule['spread_line'].fillna(0.0)
        schedule['closing_total'] = schedule['closing_total'].fillna(45.0)
        schedule['total_line'] = schedule['closing_total']
    
    schedule['season'] = 2025
    schedule['game_id'] = schedule.apply(
        lambda row: f"{row['season']}_{int(row['week']):02d}_{row['away_team']}_{row['home_team']}",
        axis=1
    )
    
    # Verify we have valid odds data
    print(f"   📊 Odds verification:")
    print(f"      Spread range: {schedule['spread_line'].min():.2f} to {schedule['spread_line'].max():.2f}")
    print(f"      Total range: {schedule['closing_total'].min():.2f} to {schedule['closing_total'].max():.2f}")
    if (schedule['closing_total'] == 45.0).all():
        print(f"      ⚠️  WARNING: All totals are 45.0 - may be placeholder values!")
    
    return schedule

if __name__ == "__main__":
    print("="*70)
    print("GENERATE WEEK 9 & 10 PREDICTIONS")
    print("="*70)
    
    all_games = []
    
    for week in [9, 10]:
        print(f"\n📥 Loading Week {week} games...")
        games = load_week_games(week)
        games['week'] = week
        all_games.append(games)
        print(f"   Found {len(games)} games")
    
    if not all_games:
        print("❌ No games found for weeks 9-10")
        sys.exit(1)
    
    games_df = pd.concat(all_games, ignore_index=True)
    print(f"\n✅ Loaded {len(games_df)} total games (weeks 9-10)")
    
    print(f"\n🚀 Running {len(games_df)} games × {N_SIMS} sims = {len(games_df) * N_SIMS:,} total")
    print(f"   Using 8 CPU cores\n")
    
    games_list = games_df.to_dict('records')
    args_list = [(idx, row, N_SIMS) for idx, row in enumerate(games_list)]
    
    start = time.time()
    
    with ProcessPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(simulate_one_game, args_list, chunksize=3))
    
    elapsed = time.time() - start
    
    print(f"\n   Completed all {len(games_df)} games")
    print(f"✅ Completed in {elapsed:.1f} seconds")
    
    # Process results
    results = [r for r in results if r is not None]
    df = pd.DataFrame(results)
    
    if len(df) == 0:
        print("❌ No valid results")
        sys.exit(1)
    
    # Save results
    output_file = Path(__file__).parent.parent / "artifacts" / "backtest_week9_10_predictions.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print(f"\n💾 Saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   Spread bets: {(df['spread_bet'].notna()).sum()}")
    print(f"   Total bets: {(df['total_bet'].notna()).sum()}")
    
    spread_bets = df[df['spread_bet'].notna()]
    total_bets = df[df['total_bet'].notna()]
    
    if len(spread_bets) > 0:
        high = spread_bets[spread_bets['spread_conviction'] == 'HIGH']
        med = spread_bets[spread_bets['spread_conviction'] == 'MEDIUM']
        low = spread_bets[spread_bets['spread_conviction'] == 'LOW']
        print(f"   Spread convictions: HIGH={len(high)}, MEDIUM={len(med)}, LOW={len(low)}")
    
    if len(total_bets) > 0:
        high = total_bets[total_bets['total_conviction'] == 'HIGH']
        med = total_bets[total_bets['total_conviction'] == 'MEDIUM']
        low = total_bets[total_bets['total_conviction'] == 'LOW']
        print(f"   Total convictions: HIGH={len(high)}, MEDIUM={len(med)}, LOW={len(low)}")

