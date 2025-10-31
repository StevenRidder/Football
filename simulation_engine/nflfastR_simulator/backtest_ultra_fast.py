#!/usr/bin/env python3
"""
ULTRA FAST Backtest - 2024 Weeks 1-8
Uses minimal simulations and aggressive parallelization
"""

# Kill hidden oversubscription
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
import time

sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile
from simulator.market_centering import center_scores_to_market

# Breakeven probability at -110 odds
BREAKEVEN = 0.5238
EDGE_THRESHOLD = 0.025

def load_games_2024() -> pd.DataFrame:
    """Load 2024 weeks 1-8 with closing lines."""
    import nfl_data_py as nfl
    
    # Load odds
    odds_file = Path("/Users/steveridder/Git/Football/artifacts/historical_odds_daily/daily_odds_2022_2024_20251028.csv")
    odds_df = pd.read_csv(odds_file)
    odds_df['commence_dt'] = pd.to_datetime(odds_df['commence_dt'])
    odds_df['snapshot_dt'] = pd.to_datetime(odds_df['snapshot_dt'])
    
    # Filter to 2024 only
    odds_df = odds_df[odds_df['season'] == 2024].copy()
    print(f"   Found {len(odds_df)} odds snapshots for 2024")
    
    # Get closing lines
    odds_df = odds_df.sort_values(['game_id', 'snapshot_dt'])
    closing_lines = odds_df.groupby('game_id', as_index=False).last()
    print(f"   Extracted {len(closing_lines)} closing lines")
    
    # Team mapping
    team_map = {
        'Los Angeles Rams': 'LAR',
        'Los Angeles Chargers': 'LAC',
        'Washington Commanders': 'WAS',
        'Washington Football Team': 'WAS',
        'Washington Redskins': 'WAS',
        'Arizona Cardinals': 'ARI',
        'Atlanta Falcons': 'ATL',
        'Baltimore Ravens': 'BAL',
        'Buffalo Bills': 'BUF',
        'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN',
        'Cleveland Browns': 'CLE',
        'Dallas Cowboys': 'DAL',
        'Denver Broncos': 'DEN',
        'Detroit Lions': 'DET',
        'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU',
        'Indianapolis Colts': 'IND',
        'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC',
        'Las Vegas Raiders': 'LV',
        'Miami Dolphins': 'MIA',
        'Minnesota Vikings': 'MIN',
        'New England Patriots': 'NE',
        'New Orleans Saints': 'NO',
        'New York Giants': 'NYG',
        'New York Jets': 'NYJ',
        'Philadelphia Eagles': 'PHI',
        'Pittsburgh Steelers': 'PIT',
        'San Francisco 49ers': 'SF',
        'Seattle Seahawks': 'SEA',
        'Tampa Bay Buccaneers': 'TB',
        'Tennessee Titans': 'TEN',
    }
    
    closing_lines['home_team'] = closing_lines['home_team'].replace(team_map)
    closing_lines['away_team'] = closing_lines['away_team'].replace(team_map)
    closing_lines = closing_lines.rename(columns={'total': 'closing_total'})
    
    # Extract week from commence_dt
    closing_lines['week'] = closing_lines['commence_dt'].dt.isocalendar().week - closing_lines['commence_dt'].dt.year.map(lambda y: pd.Timestamp(f'{y}-09-01').isocalendar().week) + 1
    # Simpler: just use the date to infer week (Sep 5-11 = week 1, etc.)
    closing_lines['commence_date'] = closing_lines['commence_dt'].dt.date
    # Map dates to NFL weeks for 2024
    # Week 1: Sep 5-9, Week 2: Sep 12-16, etc.
    def get_nfl_week_2024(date):
        import datetime
        season_start = datetime.date(2024, 9, 5)  # Thursday Sep 5, 2024
        if date < season_start:
            return 0
        days_since_start = (date - season_start).days
        return (days_since_start // 7) + 1
    
    closing_lines['week'] = closing_lines['commence_date'].apply(get_nfl_week_2024)
    
    # Load schedule
    schedule = nfl.import_schedules([2024])
    print(f"   Loaded {len(schedule)} games from nfl_data_py")
    schedule = schedule[(schedule['week'] >= 1) & (schedule['week'] <= 8)].copy()
    print(f"   Filtered to {len(schedule)} games in weeks 1-8")
    
    # Filter closing lines to weeks 1-8
    closing_lines = closing_lines[(closing_lines['week'] >= 1) & (closing_lines['week'] <= 8)].copy()
    print(f"   Filtered odds to {len(closing_lines)} games in weeks 1-8")
    
    # Merge on season, week, home_team, away_team
    spread_col = 'spread_home' if 'spread_home' in closing_lines.columns else 'spread_line'
    merged = schedule.merge(
        closing_lines[['season', 'week', 'home_team', 'away_team', spread_col, 'closing_total']],
        on=['season', 'week', 'home_team', 'away_team'],
        how='inner',
        suffixes=('', '_odds')
    )
    
    # Rename to standard column name
    if spread_col == 'spread_home':
        merged = merged.rename(columns={'spread_home': 'spread_line'})
    
    print(f"✅ Loaded {len(merged)} games from 2024 weeks 1-8")
    return merged


def load_games_2025() -> pd.DataFrame:
    """Load 2025 weeks 1-8 with market lines from NFLfastR."""
    import nfl_data_py as nfl
    
    # Load schedule - NFLfastR already has spread_line and total_line
    schedule = nfl.import_schedules([2025])
    print(f"   Loaded {len(schedule)} games from nfl_data_py")
    
    # Filter to weeks 1-8
    schedule = schedule[(schedule['week'] >= 1) & (schedule['week'] <= 8)].copy()
    print(f"   Filtered to {len(schedule)} games in weeks 1-8")
    
    # NFLfastR uses home - away convention for spread_line (positive = home favored)
    # We need to ensure consistency with our simulator convention
    # The simulator expects: spread_line = home - away (positive = home favored)
    # NFLfastR already uses this convention, so we're good
    
    # Rename columns to match expected format
    result = schedule.rename(columns={
        'total_line': 'closing_total',
        'spread_line': 'spread_line'
    }).copy()
    
    # Ensure we have required columns
    required_cols = ['season', 'week', 'home_team', 'away_team', 'spread_line', 'closing_total', 
                     'home_score', 'away_score']
    for col in required_cols:
        if col not in result.columns:
            print(f"⚠️  Warning: Missing column {col}")
    
    # Filter to games with lines
    result = result[result['spread_line'].notna() & result['closing_total'].notna()].copy()
    
    print(f"✅ Loaded {len(result)} games from 2025 weeks 1-8")
    print(f"   Weeks: {sorted(result['week'].unique())}")
    print(f"   Games with results: {(result['home_score'].notna()).sum()}/{len(result)}")
    
    return result


def simulate_one_game(args):
    """Simulate a single game - worker function."""
    idx, row, n_sims = args
    
    try:
        # Extract values safely
        away = str(row.get('away_team', ''))
        home = str(row.get('home_team', ''))
        season = int(row.get('season', 2024))
        week = int(row.get('week', 1))
        spread_line = float(row.get('spread_line', 0.0))
        total_line = float(row.get('closing_total', 45.0))
        
        if not away or not home:
            print(f"❌ Game {idx}: Missing team names - away={away}, home={home}")
            return None
        
        # Load team profiles ONCE per game
        data_dir = Path(__file__).parent / "data" / "nflfastR"
        away_profile = TeamProfile(away, season, week, data_dir)
        home_profile = TeamProfile(home, season, week, data_dir)
        
        # Create simulator ONCE
        simulator = GameSimulator(away_profile, home_profile)
        
        # Use local RNG per worker
        seed = np.uint32(hash(f"{season}-{week}-{away}-{home}") & 0xFFFFFFFF)
        rng = np.random.default_rng(seed)
        
        # Run simulations with different seeds
        home_scores = []
        away_scores = []
        
        for sim_idx in range(n_sims):
            sim_seed = rng.integers(0, 2**32, dtype=np.uint32)
            np.random.seed(int(sim_seed))
            
            result = simulator.simulate_game()
            
            home_scores.append(result['home_score'])
            away_scores.append(result['away_score'])
        
        # Center to market - convert to arrays and validate
        home_scores = np.asarray(home_scores)
        away_scores = np.asarray(away_scores)
        home_c, away_c = center_scores_to_market(
            home_scores, away_scores, spread_line, total_line
        )
        
        spreads_c = home_c - away_c
        totals_c = home_c + away_c
        
        # Track variance for analysis (but don't enforce yet)
        spread_sd = spreads_c.std()
        total_sd = totals_c.std()
        
        # Validate centering (allow 0.25 tolerance for small sample sizes)
        assert abs(spreads_c.mean() - spread_line) < 0.25, f"Spread centering failed: {spreads_c.mean():.3f} vs {spread_line:.3f}"
        assert abs(totals_c.mean() - total_line) < 0.25, f"Total centering failed: {totals_c.mean():.3f} vs {total_line:.3f}"
        
        # Calculate probabilities with strict inequalities
        # spreads_c is already (home - away), so compare directly to spread_line
        # Home covers if spread > line (e.g., if line is -3, home covers if they win by >3)
        p_home_cover = np.mean(spreads_c > spread_line)
        p_over = np.mean(totals_c > total_line)
        
        # Betting decisions
        bet_spread = 'HOME' if p_home_cover > (BREAKEVEN + EDGE_THRESHOLD) else \
                     'AWAY' if p_home_cover < (1 - BREAKEVEN - EDGE_THRESHOLD) else None
        bet_total = 'OVER' if p_over > (BREAKEVEN + EDGE_THRESHOLD) else \
                    'UNDER' if p_over < (1 - BREAKEVEN - EDGE_THRESHOLD) else None
        
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
            'p_home_cover': p_home_cover,
            'p_over': p_over,
            'bet_spread': bet_spread,
            'bet_total': bet_total,
            'actual_home_score': row.get('home_score', row.get('home_final')),
            'actual_away_score': row.get('away_score', row.get('away_final')),
            'spread_sd': spread_sd,  # Track variance for analysis
            'total_sd': total_sd,
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Error on game {idx} ({away}@{home}): {e}")
        print(f"   Row keys: {list(row.keys())[:10]}")
        traceback.print_exc()
        return None


def grade_bets(df: pd.DataFrame) -> pd.DataFrame:
    """Grade spread and total bets."""
    df = df.copy()
    
    # Calculate actuals
    df['actual_spread'] = df['actual_home_score'] - df['actual_away_score']
    df['actual_total'] = df['actual_home_score'] + df['actual_away_score']
    
    # Add outcome columns for CI gates
    df['home_covered'] = df.apply(
        lambda row: (1.0 if row['actual_spread'] > row['spread_line'] 
                     else (0.0 if row['actual_spread'] < row['spread_line'] else None)),
        axis=1
    )
    
    df['over_hit'] = df.apply(
        lambda row: (1.0 if row['actual_total'] > row['total_line']
                     else (0.0 if row['actual_total'] < row['total_line'] else None)),
        axis=1
    )
    
    # Grade spread bets
    def grade_spread(row):
        if pd.isna(row['bet_spread']) or row['bet_spread'] is None:
            return None
        
        actual = row['actual_spread']
        line = row['spread_line']
        
        if row['bet_spread'] == 'HOME':
            if actual > line:
                return 1.0  # Win
            elif actual == line:
                return 0.5  # Push
            else:
                return 0.0  # Loss
        else:  # AWAY
            if actual < line:
                return 1.0
            elif actual == line:
                return 0.5
            else:
                return 0.0
    
    # Grade total bets
    def grade_total(row):
        if pd.isna(row['bet_total']) or row['bet_total'] is None:
            return None
        
        actual = row['actual_total']
        line = row['total_line']
        
        if row['bet_total'] == 'OVER':
            if actual > line:
                return 1.0
            elif actual == line:
                return 0.5
            else:
                return 0.0
        else:  # UNDER
            if actual < line:
                return 1.0
            elif actual == line:
                return 0.5
            else:
                return 0.0
    
    df['spread_result'] = df.apply(grade_spread, axis=1)
    df['total_result'] = df.apply(grade_total, axis=1)
    
    return df


def print_summary(df: pd.DataFrame):
    """Print betting performance summary."""
    print("\n" + "="*60)
    print("BETTING PERFORMANCE - 2024 Weeks 1-8")
    print("="*60)
    
    # Spread bets
    spread_bets = df[df['bet_spread'].notna()]
    if len(spread_bets) > 0:
        wins = (spread_bets['spread_result'] == 1.0).sum()
        losses = (spread_bets['spread_result'] == 0.0).sum()
        pushes = (spread_bets['spread_result'] == 0.5).sum()
        
        # ROI calculation (pushes don't count)
        units_risked = len(spread_bets)
        units_won = wins * 0.909 - losses  # -110 odds
        roi = (units_won / units_risked) * 100 if units_risked > 0 else 0
        
        print(f"\n📊 SPREAD BETS: {len(spread_bets)} total")
        print(f"   Wins: {wins} | Losses: {losses} | Pushes: {pushes}")
        print(f"   Win Rate: {wins/len(spread_bets)*100:.1f}%")
        print(f"   ROI: {roi:+.1f}%")
    else:
        print("\n📊 SPREAD BETS: 0 (no edges found)")
    
    # Total bets
    total_bets = df[df['bet_total'].notna()]
    if len(total_bets) > 0:
        wins = (total_bets['total_result'] == 1.0).sum()
        losses = (total_bets['total_result'] == 0.0).sum()
        pushes = (total_bets['total_result'] == 0.5).sum()
        
        units_risked = len(total_bets)
        units_won = wins * 0.909 - losses
        roi = (units_won / units_risked) * 100 if units_risked > 0 else 0
        
        print(f"\n📊 TOTAL BETS: {len(total_bets)} total")
        print(f"   Wins: {wins} | Losses: {losses} | Pushes: {pushes}")
        print(f"   Win Rate: {wins/len(total_bets)*100:.1f}%")
        print(f"   ROI: {roi:+.1f}%")
    else:
        print("\n📊 TOTAL BETS: 0 (no edges found)")
    
    print("\n" + "="*60 + "\n")


def main():
    """Run ultra-fast backtest."""
    start_time = time.time()
    
    # Load games
    games_df = load_games_2024()
    n_games = len(games_df)
    n_sims = 50  # Only 50 sims per game for speed
    
    # Cap workers sanely
    n_workers = min(cpu_count(), n_games)
    
    print(f"\n🚀 Running {n_games} games × {n_sims} sims = {n_games * n_sims:,} total")
    print(f"   Using {n_workers} CPU cores\n")
    
    # Prepare args - pass dicts, not Series (cheaper to pickle)
    args = [(i, games_df.iloc[i].to_dict(), n_sims) for i in range(n_games)]
    
    # Run in parallel with sensible chunksize
    chunksize = max(1, len(args) // (n_workers * 4))
    print(f"   Chunksize: {chunksize}\n")
    
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        futures = ex.map(simulate_one_game, args, chunksize=chunksize)
    
    results = [r for r in futures if r is not None]
    print(f"\n   Completed all {len(results)} games")
    
    # Create DataFrame
    predictions_df = pd.DataFrame(results)
    
    # Grade bets
    predictions_df = grade_bets(predictions_df)
    
    # Print summary
    elapsed = time.time() - start_time
    print(f"\n✅ Completed in {elapsed:.1f} seconds")
    
    print_summary(predictions_df)
    
    # Save
    output_file = Path(__file__).parent / "artifacts" / "backtest_2024_w1-8.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_file, index=False)
    print(f"💾 Saved to: {output_file}")


if __name__ == '__main__':
    main()

