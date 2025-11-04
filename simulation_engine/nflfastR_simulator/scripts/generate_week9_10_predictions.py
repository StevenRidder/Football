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
import os

# Define paths at module level for multiprocessing safety
# This script is in: simulation_engine/nflfastR_simulator/scripts/
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # Goes to nflfastR_simulator/
DATA_DIR = BASE_DIR / "data" / "nflfastR"
ARTIFACTS_DIR = BASE_DIR / "artifacts" / "traces"

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
        
        # Load team profiles (use module-level paths for multiprocessing safety)
        home_profile = TeamProfile(home, season, week, data_dir=DATA_DIR, debug=False)
        away_profile = TeamProfile(away, season, week, data_dir=DATA_DIR, debug=False)
        
        # Run simulation with trace (only for first simulation to save space)
        game_id = row.get('game_id', f"{season}_{week:02d}_{away}_{home}")
        
        # Create trace for first simulation only (use module-level paths)
        try:
            from simulator.tracing import SimTrace
            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            trace_path = ARTIFACTS_DIR / f"{away}_{home}_{week}_{season}.jsonl"
        except Exception as e:
            # If tracing fails, continue without it (shouldn't break predictions)
            trace_path = None
            SimTrace = None
        
        # Create trace for first simulation (if tracing is available)
        if SimTrace is not None and trace_path is not None:
            trace = SimTrace(game_id=game_id, out_path=trace_path, seed=hash(f"{game_id}_0") % (2**32))
            trace.enable = True  # Enable for first sim
        else:
            trace = None
        
        sim = GameSimulator(home_profile, away_profile, 
                           game_id=game_id, season=season, week=week,
                           trace=trace, seed=hash(f"{game_id}_0") % (2**32) if trace else None)
        
        # Run first simulation with trace
        np.random.seed(hash(f"{game_id}_0") % (2**32))
        result_0 = sim.simulate_game()
        home_scores = [result_0['home_score']]
        away_scores = [result_0['away_score']]
        
        # Disable trace for remaining simulations (if tracing enabled)
        if trace is not None:
            trace.enable = False
        
        # Run remaining simulations (faster, no trace)
        for sim_i in range(1, n_sims):
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
        
        # Log distribution_params (before/after calibration) - after all sims complete
        if trace is not None:
            trace.enable = True  # Re-enable for logging
            trace.log("distribution_params", {
            "spread": {
                "raw_mean": float(spread_raw_mean),
                "raw_sd": float(spread_raw_sd),
                "calibrated_mean": float(calibrated_spread_mean),
                "calibrated_sd": float(calibrated_spread_sd),
                "market_line": float(spread_line)
            },
            "total": {
                "raw_mean": float(total_raw_mean),
                "raw_sd": float(total_raw_sd),
                "calibrated_mean": float(calibrated_total_mean),
                "calibrated_sd": float(calibrated_total_sd),
                "market_line": float(total_line)
            }
        })
        
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
        
        # Log calibration block per game (predicted probabilities, bin id, eventual hit)
        if trace is not None and trace_path is not None:
            # Bin probabilities into 0.1-width bins for reliability curves
            spread_bin_id = int(p_home_cover * 10) if spread_bet else None
            total_bin_id = int(p_over * 10) if total_bet else None
            
            trace.log("calibration", {
                "spread": {
                    "predicted_prob": float(p_home_cover if spread_bet == 'HOME' else p_away_cover),
                    "bin_id": spread_bin_id,
                    "bet_side": spread_bet,
                    "market_line": float(spread_line),
                    "eventual_hit": None  # Will be filled when game completes
                },
                "total": {
                    "predicted_prob": float(p_over if total_bet == 'OVER' else p_under),
                    "bin_id": total_bin_id,
                    "bet_side": total_bet,
                    "market_line": float(total_line),
                    "eventual_hit": None  # Will be filled when game completes
                },
                "calibration_method": use_calibration
            })
            
            # Save trace summary
            trace.save_summary(trace_path.with_suffix('.summary.json'))
        
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
    import sys
    
    # Allow command-line argument to specify which week(s) to generate
    # Usage: python3 generate_week9_10_predictions.py [week_number]
    # If no argument, generates current week + next week
    if len(sys.argv) > 1:
        try:
            weeks_to_generate = [int(sys.argv[1])]
            print("="*70)
            print(f"GENERATE WEEK {weeks_to_generate[0]} PREDICTIONS")
            print("="*70)
        except ValueError:
            print(f"❌ Invalid week number: {sys.argv[1]}")
            sys.exit(1)
    else:
        # Default: generate current week + next week (determined dynamically)
        import nfl_data_py as nfl
        from datetime import datetime
        today = datetime.now().date()
        sched = nfl.import_schedules([2025])
        sched_reg = sched[sched['game_type'] == 'REG']
        
        # Find current week (first week with games not yet played)
        current_week = None
        for week in sorted(sched_reg['week'].unique()):
            week_games = sched_reg[sched_reg['week'] == week]
            if week_games['away_score'].isna().any():
                current_week = int(week)
                break
        
        if current_week is None:
            current_week = int(sched_reg['week'].max())
        
        # Generate current week + next week
        weeks_to_generate = [current_week, current_week + 1]
        print("="*70)
        print(f"GENERATE WEEKS {weeks_to_generate[0]} & {weeks_to_generate[1]} PREDICTIONS")
        print("="*70)
    
    all_games = []
    
    for week in weeks_to_generate:
        print(f"\n📥 Loading Week {week} games...")
        games = load_week_games(week)
        games['week'] = week
        all_games.append(games)
        print(f"   Found {len(games)} games")
    
    if not all_games:
        print(f"❌ No games found for week(s) {weeks_to_generate}")
        sys.exit(1)
    
    games_df = pd.concat(all_games, ignore_index=True)
    weeks_str = f"week {weeks_to_generate[0]}" if len(weeks_to_generate) == 1 else f"weeks {weeks_to_generate[0]} & {weeks_to_generate[1]}"
    print(f"\n✅ Loaded {len(games_df)} total games ({weeks_str})")
    
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
    
    # FIXED: Automatically format for frontend and save to simulator_predictions.csv
    print(f"\n🔄 Formatting for frontend...")
    try:
        from scripts.format_for_frontend import convert_backtest_to_frontend
        frontend_output = Path(__file__).parent.parent.parent.parent / "artifacts" / "simulator_predictions.csv"
        convert_backtest_to_frontend(output_file, frontend_output)
        print(f"✅ Frontend predictions saved to: {frontend_output}")
    except Exception as e:
        print(f"⚠️  Warning: Could not format for frontend: {e}")
        print(f"   You can manually run: python3 scripts/format_for_frontend.py {output_file}")
    
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

