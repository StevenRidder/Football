"""
Backtest on 2022-2024 full seasons for statistical confidence

CRITICAL RULES:
1. Market sets the mean - we only shape the distribution
2. All features are zero-mean relative to market
3. Centering happens AFTER raw simulation
4. Never judge model by raw simulator means
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backtest_ultra_fast import *

def load_games_2022_2024():
    """Load games from 2022-2024 seasons."""
    # Load odds
    odds_file = Path("/Users/steveridder/Git/Football/artifacts/historical_odds_daily/daily_odds_2022_2024_20251028.csv")
    odds_df = pd.read_csv(odds_file)
    odds_df['commence_dt'] = pd.to_datetime(odds_df['commence_time'])
    
    # Filter to 2022-2024
    odds_df = odds_df[odds_df['season'].isin([2022, 2023, 2024])].copy()
    print(f"   Found {len(odds_df)} odds snapshots for 2022-2024")
    
    # Get closing lines (last snapshot before game)
    odds_df = odds_df.sort_values(['season', 'home_team', 'away_team', 'commence_dt'])
    
    # Create game_id
    odds_df['game_id'] = (
        odds_df['season'].astype(str) + '_' +
        odds_df['home_team'] + '_' + 
        odds_df['away_team']
    )
    
    closing_lines = odds_df.groupby('game_id', as_index=False).last()
    print(f"   Extracted {len(closing_lines)} closing lines")
    
    # Rename columns
    closing_lines = closing_lines.rename(columns={
        'spread_home': 'spread_line',
        'total': 'total_line'
    })
    
    # Convert to numeric
    closing_lines['spread_line'] = pd.to_numeric(closing_lines['spread_line'], errors='coerce')
    closing_lines['total_line'] = pd.to_numeric(closing_lines['total_line'], errors='coerce')
    closing_lines = closing_lines.dropna(subset=['spread_line', 'total_line'])
    
    # Load actual game results from nfl_data_py
    import nfl_data_py as nfl
    
    games_list = []
    for season in [2022, 2023, 2024]:
        print(f"   Loading {season} games from nfl_data_py...")
        schedule = nfl.import_schedules([season])
        schedule['season'] = season
        games_list.append(schedule)
    
    schedule = pd.concat(games_list, ignore_index=True)
    print(f"   Loaded {len(schedule)} games from nfl_data_py")
    
    # Map team names
    team_map = {
        'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
        'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
        'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
        'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
        'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
        'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
        'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
        'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS', 'Washington Football Team': 'WAS'
    }
    
    closing_lines['home_team'] = closing_lines['home_team'].map(team_map)
    closing_lines['away_team'] = closing_lines['away_team'].map(team_map)
    
    # Merge
    result = schedule.merge(
        closing_lines[['season', 'home_team', 'away_team', 'spread_line', 'total_line']],
        on=['season', 'home_team', 'away_team'],
        how='inner',
        suffixes=('', '_odds')
    )
    
    # Remove duplicate columns
    result = result.loc[:, ~result.columns.duplicated()]
    
    # Filter to completed games only
    result = result[result['home_score'].notna() & result['away_score'].notna()].copy()
    
    print(f"   Merged to {len(result)} games with odds and results")
    
    return result

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("BACKTEST 2022-2024 (FULL SAMPLE)")
    print(f"{'='*60}")
    print("Market sets mean. Simulator sets shape.")
    print(f"{'='*60}\n")
    
    games = load_games_2022_2024()
    n_games = len(games)
    
    print(f"\n✅ Loaded {n_games} games")
    print(f"   2022: {len(games[games['season']==2022])} games")
    print(f"   2023: {len(games[games['season']==2023])} games")
    print(f"   2024: {len(games[games['season']==2024])} games")
    
    # Convert to list of dicts
    games_list = games.to_dict('records')
    
    # Prepare args (use 100 sims for speed on large sample)
    N_SIMS = 100
    args_list = [
        (idx, row, N_SIMS)
        for idx, row in enumerate(games_list)
    ]
    
    # Run in parallel
    n_workers = min(8, os.cpu_count() or 1)
    chunksize = max(1, n_games // (n_workers * 4))
    
    print(f"\n🚀 Running {n_games} games × {N_SIMS} sims = {n_games * N_SIMS:,} total")
    print(f"   Using {n_workers} CPU cores")
    print(f"   Estimated time: ~{n_games * 1.5 / 60:.0f} minutes\n")
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        results = list(ex.map(simulate_one_game, args_list, chunksize=chunksize))
    
    print(f"\n   Completed all {n_games} games\n")
    
    elapsed = time.time() - start_time
    print(f"✅ Completed in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)\n")
    
    # Filter out None results
    results = [r for r in results if r is not None]
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Grade bets
    df = grade_bets(df)
    
    # Print summary
    print_summary(df)
    
    # Save results
    output_file = Path("artifacts/backtest_2022_2024.csv")
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved to: {output_file}")
    
    # Additional stats
    print(f"\n{'='*60}")
    print("SAMPLE SIZE ANALYSIS")
    print(f"{'='*60}")
    
    spread_bets = df[df['bet_spread'].notna()]
    total_bets = df[df['bet_total'].notna()]
    
    print(f"\n📊 TOTAL BETS:")
    print(f"   Spread: {len(spread_bets)} {'✅ (>100)' if len(spread_bets) >= 100 else '⚠️ (<100)'}")
    print(f"   Total: {len(total_bets)} {'✅ (>100)' if len(total_bets) >= 100 else '⚠️ (<100)'}")
    
    if len(spread_bets) >= 100:
        print(f"\n✅ Sufficient sample size for statistical confidence")
    
    print(f"\n{'='*60}")

