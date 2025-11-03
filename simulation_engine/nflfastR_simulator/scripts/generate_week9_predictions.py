"""
Generate predictions for Week 9 games using the simulator.

This script runs simulations for week 9 games (future games without results).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_scores_to_market
from backtest_ultra_fast import load_games_2025

# Conviction tiers (same as backtest)
LOW_EDGE = 0.0
MEDIUM_EDGE = 0.02
HIGH_EDGE = 0.04

BREAKEVEN = 0.524
N_SIMS = 100

def get_conviction_level(edge):
    """Get conviction level based on edge."""
    if edge >= HIGH_EDGE:
        return 'HIGH'
    elif edge >= MEDIUM_EDGE:
        return 'MEDIUM'
    else:
        return 'LOW'

def simulate_week9_game(row):
    """Simulate one week 9 game."""
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
        
        for sim_i in range(N_SIMS):
            np.random.seed(hash(f"{game_id}_{sim_i}") % (2**32))
            result = sim.simulate_game()
            home_scores.append(result['home_score'])
            away_scores.append(result['away_score'])
        
        home_scores = np.asarray(home_scores)
        away_scores = np.asarray(away_scores)
        
        # Store raw (pre-centered) scores and SDs for calibration
        spreads_raw = home_scores - away_scores
        totals_raw = home_scores + away_scores
        home_raw_mean = float(np.mean(home_scores))
        away_raw_mean = float(np.mean(away_scores))
        spread_raw_mean = float(np.mean(spreads_raw))
        total_raw_mean = float(np.mean(totals_raw))
        spread_raw_sd = float(np.std(spreads_raw))
        total_raw_sd = float(np.std(totals_raw))
        
        # Center to market
        home_c, away_c = center_scores_to_market(
            home_scores, away_scores, spread_line, total_line
        )
        
        spreads_c = home_c - away_c
        totals_c = home_c + away_c
        
        # Calculate distribution metrics (THIS IS WHERE THE EDGE COMES FROM)
        spread_std = float(np.std(spreads_c))
        total_std = float(np.std(totals_c))
        
        # Tail probabilities (edge indicators)
        blowout_prob = float(np.mean(np.abs(spreads_c) > 14))
        close_game_prob = float(np.mean(np.abs(spreads_c) <= 3))
        low_total_prob = float(np.mean(totals_c < 40))
        high_total_prob = float(np.mean(totals_c > 50))
        
        # Calculate probabilities - TWO METHODS:
        # 1. Current (centered): from centered distribution (for display)
        p_home_cover_centered = np.mean(spreads_c > spread_line)
        p_away_cover_centered = 1 - p_home_cover_centered
        p_over_centered = np.mean(totals_c > total_line)
        p_under_centered = 1 - p_over_centered
        
        # 2. Calibrated (if calibrator available): from raw simulator using z-scores
        # Initialize defaults
        p_home_cover = p_home_cover_centered
        p_away_cover = p_away_cover_centered
        p_over = p_over_centered
        p_under = p_under_centered
        use_calibration_spread = False
        use_calibration_total = False
        
        # Load calibrators if available
        try:
            import pickle
            from pathlib import Path
            artifacts_dir = Path(__file__).parent.parent / "artifacts"
            
            spread_cal_file = artifacts_dir / "spread_calibrator_isotonic.pkl"
            total_cal_file = artifacts_dir / "total_calibrator_isotonic.pkl"
            
            # Try isotonic first, then platt
            if not spread_cal_file.exists():
                spread_cal_file = artifacts_dir / "spread_calibrator_platt.pkl"
            if not total_cal_file.exists():
                total_cal_file = artifacts_dir / "total_calibrator_platt.pkl"
            
            spread_calibrator = None
            total_calibrator = None
            
            if spread_cal_file.exists():
                with open(spread_cal_file, 'rb') as f:
                    spread_calibrator = pickle.load(f)
            
            if total_cal_file.exists():
                with open(total_cal_file, 'rb') as f:
                    total_calibrator = pickle.load(f)
            
            # Use calibrated probabilities if available
            if spread_calibrator and spread_calibrator.is_fitted:
                from simulator.probability_calibration import calibrate_probabilities
                spread_result = calibrate_probabilities(
                    spread_raw_mean, spread_raw_sd, spread_line, spread_calibrator
                )
                p_home_cover = spread_result['p_home_cover']
                p_away_cover = spread_result['p_away_cover']
                use_calibration_spread = True
            
            if total_calibrator and total_calibrator.is_fitted:
                from simulator.probability_calibration import calibrate_total_probabilities
                total_result = calibrate_total_probabilities(
                    total_raw_mean, total_raw_sd, total_line, total_calibrator
                )
                p_over = total_result['p_over']
                p_under = total_result['p_under']
                use_calibration_total = True
            
        except Exception as e:
            # Fallback to centered if calibration fails
            pass  # Already initialized to centered values above
        
        use_calibration = use_calibration_spread or use_calibration_total
        
        # Determine bets with conviction levels
        spread_bet = None
        spread_edge = 0
        spread_conviction = None
        
        if p_home_cover > BREAKEVEN:
            spread_bet = 'HOME'
            spread_edge = p_home_cover - BREAKEVEN
        elif p_away_cover > BREAKEVEN:
            spread_bet = 'AWAY'
            spread_edge = p_away_cover - BREAKEVEN
        
        if spread_edge > 0:
            spread_conviction = get_conviction_level(spread_edge)
        
        total_bet = None
        total_edge = 0
        total_conviction = None
        
        if p_over > BREAKEVEN:
            total_bet = 'OVER'
            total_edge = p_over - BREAKEVEN
        elif p_under > BREAKEVEN:
            total_bet = 'UNDER'
            total_edge = p_under - BREAKEVEN
        
        if total_edge > 0:
            total_conviction = get_conviction_level(total_edge)
        
        return {
            'away_team': away,
            'home_team': home,
            'season': season,
            'week': week,
            'spread_line': spread_line,
            'closing_total': total_line,
            # Raw (pre-centered) scores and SDs for calibration
            'home_score_raw': home_raw_mean,
            'away_score_raw': away_raw_mean,
            'spread_raw': spread_raw_mean,
            'spread_raw_sd': spread_raw_sd,
            'total_raw': total_raw_mean,
            'total_raw_sd': total_raw_sd,
            # Centered (market-adjusted) scores
            'home_score_mean': float(np.mean(home_c)),
            'away_score_mean': float(np.mean(away_c)),
            
            # Distribution metrics (THE REAL EDGE)
            'spread_std': spread_std,
            'total_std': total_std,
            'blowout_prob': blowout_prob,
            'close_game_prob': close_game_prob,
            'low_total_prob': low_total_prob,
            'high_total_prob': high_total_prob,
            
            # Cover probabilities (from distribution shape)
            'p_home_cover': float(p_home_cover),
            'p_away_cover': float(p_away_cover),
            'p_over': float(p_over),
            'p_under': float(p_under),
            # Centered probabilities (for comparison/display)
            'p_home_cover_centered': float(p_home_cover_centered),
            'p_away_cover_centered': float(p_away_cover_centered),
            'p_over_centered': float(p_over_centered),
            'p_under_centered': float(p_under_centered),
            # Calibration method used
            'calibration_method': 'calibrated' if use_calibration else 'centered',
            'calibration_method_spread': 'calibrated' if use_calibration_spread else 'centered',
            'calibration_method_total': 'calibrated' if use_calibration_total else 'centered',
            
            'spread_bet': spread_bet,
            'spread_edge': spread_edge,
            'spread_conviction': spread_conviction,
            'total_bet': total_bet,
            'total_edge': total_edge,
            'total_conviction': total_conviction,
            'spread_result': None,  # No results for future games
            'total_result': None,
            'home_score': None,
            'away_score': None,
        }
    except Exception as e:
        print(f"❌ Error simulating {row.get('away_team')} @ {row.get('home_team')}: {e}")
        return None

if __name__ == "__main__":
    print("="*80)
    print("GENERATE WEEK 9 PREDICTIONS")
    print("="*80)
    
    # Load 2025 schedule directly (not filtered to weeks 1-8)
    print("\n📊 Loading 2025 schedule...")
    import nfl_data_py as nfl
    sched = nfl.import_schedules([2025])
    sched_reg = sched[sched['game_type'] == 'REG'].copy()
    
    # Filter to week 9
    week9_games = sched_reg[sched_reg['week'] == 9].copy()
    
    if len(week9_games) == 0:
        print("❌ No week 9 games found")
        sys.exit(1)
    
    # Normalize team names
    week9_games['away_team'] = week9_games['away_team'].str.upper().str[:3]
    week9_games['home_team'] = week9_games['home_team'].str.upper().str[:3]
    
    # Get market lines from Odds API
    print("\n📥 Fetching Week 9 odds from Odds API...")
    from scripts.fetch_week9_odds import fetch_week9_odds
    odds_dict = fetch_week9_odds()
    
    if not odds_dict:
        print("⚠️  Could not fetch odds, using nflfastR schedule lines...")
        week9_games['spread_line'] = week9_games.get('spread_line', 0.0)
        week9_games['closing_total'] = week9_games.get('total_line', 45.0)
        week9_games['total_line'] = week9_games.get('total_line', 45.0)
    else:
        # Merge odds into games
        def get_odds(row):
            key = (row['away_team'], row['home_team'])
            if key in odds_dict:
                return pd.Series({
                    'spread_line': odds_dict[key]['spread_line'],
                    'total_line': odds_dict[key]['total_line'],
                    'closing_total': odds_dict[key]['total_line']
                })
            else:
                # Fallback to schedule if available
                return pd.Series({
                    'spread_line': row.get('spread_line', 0.0),
                    'total_line': row.get('total_line', 45.0),
                    'closing_total': row.get('total_line', 45.0)
                })
        
        odds_df = week9_games.apply(get_odds, axis=1)
        week9_games['spread_line'] = odds_df['spread_line']
        week9_games['total_line'] = odds_df['total_line']
        week9_games['closing_total'] = odds_df['closing_total']
        
        print(f"✅ Merged odds for {len(week9_games[week9_games['spread_line'] != 0.0])} games")
    week9_games['season'] = 2025
    week9_games['game_id'] = week9_games.apply(
        lambda row: f"{row['season']}_{int(row['week']):02d}_{row['away_team']}_{row['home_team']}",
        axis=1
    )
    
    print(f"✅ Found {len(week9_games)} week 9 games\n")
    
    # Simulate each game
    print(f"🚀 Running {len(week9_games)} games × {N_SIMS} sims = {len(week9_games) * N_SIMS:,} total\n")
    
    results = []
    for idx, row in week9_games.iterrows():
        result = simulate_week9_game(row.to_dict())
        if result:
            results.append(result)
        print(f"   Completed: {result['away_team']} @ {result['home_team']}")
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Save to CSV
    output_file = Path(__file__).parent.parent / "artifacts" / "backtest_week9_predictions.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Generated {len(results)} predictions")
    print(f"💾 Saved to: {output_file}")
    
    # Summary
    spread_bets = df[df['spread_bet'].notna()]
    total_bets = df[df['total_bet'].notna()]
    
    print(f"\n📊 Summary:")
    print(f"   Spread bets: {len(spread_bets)}")
    print(f"   Total bets: {len(total_bets)}")
    
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

