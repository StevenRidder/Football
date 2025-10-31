"""
Backtest on 2023 and 2024 seasons.
Uses the same linear calibration approach as backtest_all_games_conviction.py
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
from scipy.stats import norm

# Conviction tiers (edge thresholds) - ADJUSTED for better distribution
LOW_EDGE = 0.0      # Bet everything
MEDIUM_EDGE = 0.03  # 3% edge
HIGH_EDGE = 0.06    # 6% edge

BREAKEVEN = 0.524
N_SIMS = 100

# Linear calibration parameters
LINEAR_ALPHA = 26.45
LINEAR_BETA = 0.571

def load_games_2023_2024():
    """Load 2023 and 2024 games with market lines."""
    import nfl_data_py as nfl
    
    games = []
    for season in [2023, 2024]:
        print(f"📥 Loading {season} games...")
        
        # Load schedule
        schedule = nfl.import_schedules([season])
        schedule = schedule[schedule['game_type'] == 'REG'].copy()
        
        # NFLfastR has spread_line and total_line
        # Rename to match expected format
        schedule = schedule.rename(columns={
            'total_line': 'closing_total',
            'spread_line': 'spread_line'
        }).copy()
        
        # Filter to games with lines and results
        schedule = schedule[
            schedule['spread_line'].notna() & 
            schedule['closing_total'].notna() &
            schedule['home_score'].notna() &
            schedule['away_score'].notna()
        ].copy()
        
        schedule['season'] = season
        games.append(schedule)
        print(f"   Found {len(schedule)} games with results")
    
    result = pd.concat(games, ignore_index=True)
    print(f"✅ Loaded {len(result)} total games from 2023-2024")
    
    return result

def simulate_one_game(args):
    """Simulate one game and return betting opportunities."""
    idx, row, n_sims = args
    
    try:
        away = row['away_team']
        home = row['home_team']
        season = int(row['season'])
        week = int(row['week'])
        spread_line = float(row['spread_line'])
        total_line = float(row.get('closing_total', row.get('total_line', 45.0)))
        
        # Load team profiles
        data_dir = Path(__file__).parent / "data" / "nflfastR"
        home_profile = TeamProfile(home, season, week, data_dir=data_dir, debug=False)
        away_profile = TeamProfile(away, season, week, data_dir=data_dir, debug=False)
        
        # Run simulation
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
        
        spreads_raw = home_scores - away_scores
        totals_raw = home_scores + away_scores
        
        spread_raw_mean = spreads_raw.mean()
        spread_raw_sd = spreads_raw.std()
        total_raw_mean = totals_raw.mean()
        total_raw_sd = totals_raw.std()
        
        # Center for display (preserve raw for calibration)
        home_c, away_c = center_scores_to_market(
            home_scores, away_scores, spread_line, total_line
        )
        
        spreads_c = home_c - away_c
        totals_c = home_c + away_c
        
        # Calculate probabilities - LINEAR CALIBRATION with raw SD
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
        
        # Calculate probabilities using normal approximation
        p_home_cover = 1 - norm.cdf(
            (spread_line - calibrated_spread_mean) / max(calibrated_spread_sd, 1e-6)
        )
        p_away_cover = 1 - p_home_cover
        p_over = 1 - norm.cdf(
            (total_line - calibrated_total_mean) / max(calibrated_total_sd, 1e-6)
        )
        p_under = 1 - p_over
        
        # Clip to valid range
        p_home_cover = np.clip(p_home_cover, 0.01, 0.99)
        p_over = np.clip(p_over, 0.01, 0.99)
        p_away_cover = 1 - p_home_cover
        p_under = 1 - p_over
        
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
            'game_id': row.get('game_id', f"{season}_{week:02d}_{away}_{home}"),
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
            # Raw for calibration
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
            'calibration_method': 'linear',
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
    if 'actual_spread' not in df.columns:
        if 'actual_home_score' in df.columns and 'actual_away_score' in df.columns:
            df['actual_spread'] = df['actual_home_score'] - df['actual_away_score']
        else:
            print("⚠️  Missing actual scores - cannot grade bets")
            return df
    
    if 'actual_total' not in df.columns:
        if 'actual_home_score' in df.columns and 'actual_away_score' in df.columns:
            df['actual_total'] = df['actual_home_score'] + df['actual_away_score']
        else:
            print("⚠️  Missing actual scores - cannot grade bets")
            return df
    
    # Grade spread bets
    def grade_spread(row):
        if pd.isna(row.get('spread_bet')):
            return np.nan
        bet = row['spread_bet']
        line = row['spread_line']
        actual = row['actual_spread']
        
        if bet == 'HOME':
            return 1.0 if actual > line else (0.5 if abs(actual - line) < 0.1 else 0.0)
        elif bet == 'AWAY':
            return 1.0 if actual < line else (0.5 if abs(actual - line) < 0.1 else 0.0)
        return np.nan
    
    # Grade total bets
    def grade_total(row):
        if pd.isna(row.get('total_bet')):
            return np.nan
        bet = row['total_bet']
        line = row['total_line']
        actual = row['actual_total']
        
        if bet == 'OVER':
            return 1.0 if actual > line else (0.5 if abs(actual - line) < 0.1 else 0.0)
        elif bet == 'UNDER':
            return 1.0 if actual < line else (0.5 if abs(actual - line) < 0.1 else 0.0)
        return np.nan
    
    df['spread_result'] = df.apply(grade_spread, axis=1)
    df['total_result'] = df.apply(grade_total, axis=1)
    
    return df

if __name__ == "__main__":
    print("="*70)
    print("BACKTEST 2023-2024 SEASONS")
    print("="*70)
    
    games = load_games_2023_2024()
    
    if len(games) == 0:
        print("❌ No games found")
        sys.exit(1)
    
    print(f"\n🚀 Running {len(games)} games × {N_SIMS} sims = {len(games) * N_SIMS:,} total")
    print(f"   Betting on ALL games with conviction tiers")
    
    import os
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    
    import multiprocessing
    n_workers = min(8, multiprocessing.cpu_count())
    print(f"   Using {n_workers} CPU cores")
    
    args_list = [(idx, row, N_SIMS) for idx, row in games.iterrows()]
    
    start_time = time.time()
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        results = list(executor.map(simulate_one_game, args_list))
    
    elapsed = time.time() - start_time
    print(f"\n   Completed all {len(games)} games")
    print(f"✅ Completed in {elapsed:.1f} seconds")
    
    # Filter out None results
    results = [r for r in results if r is not None]
    df = pd.DataFrame(results)
    
    if len(df) == 0:
        print("❌ No valid results")
        sys.exit(1)
    
    # Grade bets
    df = grade_bets(df)
    
    # Print results by conviction
    print("\n" + "="*70)
    print("COMPREHENSIVE BACKTEST - 2023-2024 SEASONS")
    print("="*70)
    
    print(f"\nTotal games analyzed: {len(df)}")
    
    # Spread bets by conviction
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
    
    # Total bets by conviction
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
    
    print("\n" + "="*70)
    
    # Save results
    output_file = Path(__file__).parent / "artifacts" / "backtest_2023_2024.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved to: {output_file}")

