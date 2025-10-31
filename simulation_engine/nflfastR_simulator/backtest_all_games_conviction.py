"""
Comprehensive Backtest: ALL GAMES with Conviction Tiers

Bet on every game, categorized by edge size:
- LOW conviction: 0-2% edge
- MEDIUM conviction: 2-4% edge  
- HIGH conviction: 4%+ edge
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_scores_to_market
from concurrent.futures import ProcessPoolExecutor
import time

# Conviction tiers (edge thresholds) - ADJUSTED for better distribution
# Based on actual edge distribution analysis
LOW_EDGE = 0.0      # Bet everything
MEDIUM_EDGE = 0.03  # 3% edge (was 2%)
HIGH_EDGE = 0.06    # 6% edge (was 4%)

BREAKEVEN = 0.524
N_SIMS = 100

def simulate_one_game(args):
    """Simulate one game and return betting opportunities."""
    idx, row, n_sims = args
    
    try:
        away = row['away_team']
        home = row['home_team']
        season = int(row.get('season', 2024))
        week = int(row.get('week', 1))
        spread_line = float(row.get('spread_line', 0.0))
        total_line = float(row.get('closing_total', 45.0))
        
        # Load team profiles (debug=False for speed, set to True to see data loading)
        data_dir = Path(__file__).parent / "data" / "nflfastR"
        home_profile = TeamProfile(home, season, week, data_dir=data_dir, debug=False)
        away_profile = TeamProfile(away, season, week, data_dir=data_dir, debug=False)
        
        # Run simulation (pass game info for situational factors if available)
        game_id = row.get('game_id', f"{season}_{week:02d}_{away}_{home}")
        sim = GameSimulator(home_profile, away_profile, 
                           game_id=game_id, season=season, week=week)
        home_scores = []
        away_scores = []
        
        for sim_i in range(n_sims):
            np.random.seed(idx * 10000 + sim_i)
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
        
        home_c, away_c = center_scores_to_market(
            home_scores, away_scores, spread_line, total_line
        )
        
        spreads_c = home_c - away_c
        totals_c = home_c + away_c
        
        # Calculate probabilities - THREE METHODS (priority order):
        # 1. Centered (for display/comparison) - always calculate
        p_home_cover_centered = np.mean(spreads_c > spread_line)
        p_away_cover_centered = 1 - p_home_cover_centered
        p_over_centered = np.mean(totals_c > total_line)
        p_under_centered = 1 - p_over_centered
        
        # 2. Linear calibration (score-level) - DEFAULT for betting
        # Uses: calibrated_mean = 26.45 + 0.571 * raw_mean
        #       calibrated_sd = 0.571 * raw_sd (proportional scaling)
        LINEAR_ALPHA = 26.45
        LINEAR_BETA = 0.571
        
        from scipy.stats import norm
        
        # Calibrate totals - PRESERVE VARIANCE for better discrimination
        calibrated_total_mean = LINEAR_ALPHA + LINEAR_BETA * total_raw_mean
        # Use raw SD (don't scale) to preserve variance and create sharper probabilities
        calibrated_total_sd = total_raw_sd  # Changed: was LINEAR_BETA * total_raw_sd
        
        # Calibrate spread (calibrate home/away separately, then subtract)
        raw_home_mean = (total_raw_mean + spread_raw_mean) / 2.0
        raw_away_mean = (total_raw_mean - spread_raw_mean) / 2.0
        calibrated_home_mean = LINEAR_ALPHA / 2.0 + LINEAR_BETA * raw_home_mean
        calibrated_away_mean = LINEAR_ALPHA / 2.0 + LINEAR_BETA * raw_away_mean
        calibrated_spread_mean = calibrated_home_mean - calibrated_away_mean
        # Use raw SD for spread too - preserves variance
        calibrated_spread_sd = spread_raw_sd  # Changed: was LINEAR_BETA * spread_raw_sd
        
        # Calculate probabilities using normal approximation
        # Using raw SD preserves more variance → sharper probabilities → better conviction distribution
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
        
        # 3. Probability calibrator (isotonic/Platt) - fallback if available
        # Initialize to linear calibration as default
        p_home_cover = p_home_cover_linear
        p_away_cover = p_away_cover_linear
        p_over = p_over_linear
        p_under = p_under_linear
        use_calibration = 'linear'
        
        # Try to load and use calibrators
        try:
            import pickle
            artifacts_dir = Path(__file__).parent / "artifacts"
            
            spread_cal_file = artifacts_dir / "spread_calibrator_isotonic.pkl"
            total_cal_file = artifacts_dir / "total_calibrator_isotonic.pkl"
            
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
            
            if spread_calibrator and spread_calibrator.is_fitted:
                from simulator.probability_calibration import calibrate_probabilities
                spread_result = calibrate_probabilities(
                    spread_raw_mean, spread_raw_sd, spread_line, spread_calibrator
                )
                p_home_cover = spread_result['p_home_cover']
                p_away_cover = spread_result['p_away_cover']
                use_calibration = 'isotonic'  # Override linear if available
            
            if total_calibrator and total_calibrator.is_fitted:
                from simulator.probability_calibration import calibrate_total_probabilities
                total_result = calibrate_total_probabilities(
                    total_raw_mean, total_raw_sd, total_line, total_calibrator
                )
                p_over = total_result['p_over']
                p_under = total_result['p_under']
                use_calibration = True
        except Exception:
            # Fallback to centered if calibration fails
            pass
        
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
            total_edge = p_over - BREAKEVEN
        elif p_under > BREAKEVEN:
            total_bet = 'UNDER'
            total_edge = p_under - BREAKEVEN
        
        if total_bet:
            if total_edge >= HIGH_EDGE:
                total_conviction = 'HIGH'
            elif total_edge >= MEDIUM_EDGE:
                total_conviction = 'MEDIUM'
            else:
                total_conviction = 'LOW'
        
        return {
            'game_id': row.get('game_id', f"{season}_{week}_{away}_{home}"),
            'season': season,
            'week': week,
            'away_team': away,
            'home_team': home,
            'spread_line': spread_line,
            'total_line': total_line,
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
            # Store centered for comparison
            'p_home_cover_centered': p_home_cover_centered,
            'p_over_centered': p_over_centered,
            # Store calibration method used
            'calibration_method': use_calibration,
            'spread_bet': spread_bet,
            'spread_edge': spread_edge,
            'spread_conviction': spread_conviction,
            'total_bet': total_bet,
            'total_edge': total_edge,
            'total_conviction': total_conviction,
            'actual_home_score': row.get('home_score', np.nan),
            'actual_away_score': row.get('away_score', np.nan),
            'actual_spread': row.get('home_score', 0) - row.get('away_score', 0),
            'actual_total': row.get('home_score', 0) + row.get('away_score', 0),
        }
    
    except Exception as e:
        print(f"❌ Error on game {idx} ({away}@{home}): {e}")
        return None

def grade_bets(df):
    """Grade all bets and add result columns."""
    # Calculate actual spreads and totals if not present
    if 'actual_spread' not in df.columns:
        if 'actual_home_score' in df.columns and 'actual_away_score' in df.columns:
            df['actual_spread'] = df['actual_home_score'] - df['actual_away_score']
        else:
            print("⚠️  Missing actual scores - cannot grade bets")
            return df
    
    if 'actual_total' not in df.columns:
        if 'actual_home_score' in df.columns and 'actual_away_score' in df.columns:
            df['actual_total'] = df['actual_home_score'] + df['actual_away_score']
    
    # Grade spreads
    df['home_covered'] = df.apply(
        lambda row: (1.0 if pd.notna(row.get('actual_spread')) and pd.notna(row.get('spread_line')) and row['actual_spread'] > row['spread_line'] 
                     else (0.0 if pd.notna(row.get('actual_spread')) and pd.notna(row.get('spread_line')) and row['actual_spread'] < row['spread_line'] else None)),
        axis=1
    )
    
    df['spread_result'] = df.apply(
        lambda row: (row['home_covered'] if row['spread_bet'] == 'HOME'
                     else (1.0 - row['home_covered'] if row['spread_bet'] == 'AWAY' and pd.notna(row['home_covered'])
                           else None)),
        axis=1
    )
    
    # Grade totals
    df['over_hit'] = df.apply(
        lambda row: (1.0 if pd.notna(row.get('actual_total')) and pd.notna(row.get('total_line')) and row['actual_total'] > row['total_line']
                     else (0.0 if pd.notna(row.get('actual_total')) and pd.notna(row.get('total_line')) and row['actual_total'] < row['total_line'] else None)),
        axis=1
    )
    
    df['total_result'] = df.apply(
        lambda row: (row['over_hit'] if row['total_bet'] == 'OVER'
                     else (1.0 - row['over_hit'] if row['total_bet'] == 'UNDER' and pd.notna(row['over_hit'])
                           else None)),
        axis=1
    )
    
    return df

def print_summary(df):
    """Print comprehensive summary by conviction tier."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE BACKTEST - ALL GAMES BY CONVICTION")
    print("=" * 70)
    print(f"\nTotal games analyzed: {len(df)}")
    
    # Overall spread performance
    spread_bets = df[df['spread_bet'].notna()]
    if len(spread_bets) > 0:
        print(f"\n📊 SPREAD BETS: {len(spread_bets)} total")
        
        for conviction in ['HIGH', 'MEDIUM', 'LOW']:
            tier_bets = spread_bets[spread_bets['spread_conviction'] == conviction]
            if len(tier_bets) == 0:
                continue
            
            wins = (tier_bets['spread_result'] == 1.0).sum()
            losses = (tier_bets['spread_result'] == 0.0).sum()
            pushes = tier_bets['spread_result'].isna().sum()
            
            if wins + losses > 0:
                win_rate = wins / (wins + losses) * 100
                roi = ((wins * 0.909 - losses) / len(tier_bets)) * 100
                avg_edge = tier_bets['spread_edge'].mean() * 100
                
                print(f"\n   {conviction} Conviction ({len(tier_bets)} bets, avg edge: {avg_edge:.1f}%):")
                print(f"      {wins}W-{losses}L-{pushes}P | Win Rate: {win_rate:.1f}% | ROI: {roi:+.1f}%")
    
    # Overall total performance
    total_bets = df[df['total_bet'].notna()]
    if len(total_bets) > 0:
        print(f"\n📊 TOTAL BETS: {len(total_bets)} total")
        
        for conviction in ['HIGH', 'MEDIUM', 'LOW']:
            tier_bets = total_bets[total_bets['total_conviction'] == conviction]
            if len(tier_bets) == 0:
                continue
            
            wins = (tier_bets['total_result'] == 1.0).sum()
            losses = (tier_bets['total_result'] == 0.0).sum()
            pushes = tier_bets['total_result'].isna().sum()
            
            if wins + losses > 0:
                win_rate = wins / (wins + losses) * 100
                roi = ((wins * 0.909 - losses) / len(tier_bets)) * 100
                avg_edge = tier_bets['total_edge'].mean() * 100
                
                print(f"\n   {conviction} Conviction ({len(tier_bets)} bets, avg edge: {avg_edge:.1f}%):")
                print(f"      {wins}W-{losses}L-{pushes}P | Win Rate: {win_rate:.1f}% | ROI: {roi:+.1f}%")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    # Load 2025 weeks 1-8 data
    from backtest_ultra_fast import load_games_2025
    
    print("Loading 2025 weeks 1-8 games...")
    games = load_games_2025()
    print(f"✅ Loaded {len(games)} games\n")
    
    print(f"🚀 Running {len(games)} games × {N_SIMS} sims = {len(games) * N_SIMS:,} total")
    print(f"   Betting on ALL games with conviction tiers")
    print(f"   Using 8 CPU cores\n")
    
    games_list = games.to_dict('records')
    args_list = [(idx, row, N_SIMS) for idx, row in enumerate(games_list)]
    
    start = time.time()
    
    with ProcessPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(simulate_one_game, args_list, chunksize=3))
    
    elapsed = time.time() - start
    
    print(f"\n   Completed all {len(games)} games")
    print(f"✅ Completed in {elapsed:.1f} seconds")
    
    # Process results
    results = [r for r in results if r is not None]
    df = pd.DataFrame(results)
    df = grade_bets(df)
    
    # Print summary
    print_summary(df)
    
    # Save results
    output_file = Path(__file__).parent / "artifacts" / "backtest_all_games_conviction.csv"
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved to: {output_file}")

