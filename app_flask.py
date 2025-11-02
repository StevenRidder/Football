"""
NFL Alpha Model - Clean Flask App
Simple betting interface with alpha XGBoost predictions
"""
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import nfl_data_py as nfl

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Cache for nflverse results
_results_cache = None
_results_cache_time = None

def load_alpha_predictions():
    """Load latest alpha model predictions."""
    # Look for predictions_alpha_*.csv files
    pred_files = sorted(Path(".").glob("predictions_alpha_*.csv"), reverse=True)
    
    if not pred_files:
        return None
    
    latest = pred_files[0]
    print(f"📂 Loading: {latest.name}")
    
    df = pd.read_csv(latest)
    return df

def load_simulator_predictions(force_reload=False):
    """Load simulator predictions from backtest_all_games_conviction.py (formatted for frontend)."""
    simulator_file = Path("artifacts") / "simulator_predictions.csv"
    
    if simulator_file.exists():
        # Get file modification time for cache busting
        mtime = simulator_file.stat().st_mtime
        print(f"✅ Loading simulator predictions from {simulator_file} (modified: {mtime})")
        df = pd.read_csv(simulator_file)
        return df
    return None

def load_latest_predictions():
    """Load pre-computed graded results from backend"""
    import glob
    
    # Priority 1: Simulator predictions (from backtest_all_games_conviction.py)
    simulator_df = load_simulator_predictions()
    if simulator_df is not None:
        return simulator_df
    
    # Priority 2: Pre-computed graded results (from grade_predictions_simple.py)
    graded_files = glob.glob('artifacts/graded_results/graded_bets_*.csv')
    if graded_files:
        latest_file = sorted(graded_files)[-1]
        print(f"✅ Loading pre-computed results from {latest_file}")
        df = pd.read_csv(latest_file)
        
        # Map backend columns to Flask expected columns
        df = df.rename(columns={
            'spread_bet_side': 'our_spread_pick',
            'total_bet_side': 'our_total_pick',
            'spread_win': 'spread_result_numeric',
            'total_win': 'total_result_numeric',
            'moneyline_win': 'moneyline_result_numeric'
        })
        
        # Convert numeric results to text
        df['spread_result'] = df['spread_result_numeric'].apply(
            lambda x: 'WIN' if x == 1 else 'LOSS' if x == 0 else None
        )
        df['total_result'] = df['total_result_numeric'].apply(
            lambda x: 'WIN' if x == 1 else 'LOSS' if x == 0 else None
        )
        df['moneyline_result'] = df['moneyline_result_numeric'].apply(
            lambda x: 'WIN' if x == 1 else 'LOSS' if x == 0 else None
        )
        
        # Add spread_bet and total_bet in expected format
        df['spread_bet'] = df.apply(
            lambda row: 'Pass' if pd.isna(row['our_spread_pick']) else 
                       ('Away ATS' if row['our_spread_pick'] == row['away_team'] else 'Home ATS'),
            axis=1
        )
        df['total_bet'] = df.apply(
            lambda row: 'Pass' if pd.isna(row['our_total_pick']) else row['our_total_pick'],
            axis=1
        )
        
        # Rename score columns to match Flask expectations
        df = df.rename(columns={
            'predicted_away_score': 'our_away_score',
            'predicted_home_score': 'our_home_score'
        })
        
        # Add is_completed field (True if game has actual scores)
        df['is_completed'] = df['actual_away_score'].notna() & df['actual_home_score'].notna()
        
        # Add recommendation fields (template expects these)
        df['spread_recommendation'] = df['our_spread_pick'].apply(
            lambda x: x if pd.notna(x) else 'Pass'
        )
        df['total_recommendation'] = df['our_total_pick'].apply(
            lambda x: x if pd.notna(x) else 'Pass'
        )
        
        # Calculate market-implied scores from spread and total
        # Market total / 2 gives average score per team
        # Market spread tells us the difference
        # If market_spread is negative (away favored), away gets more points
        df['closing_total'] = df['market_total']
        df['closing_spread'] = df['market_spread']
        
        def calc_market_scores(row):
            total = row['market_total']
            spread = row['market_spread']  # Negative = away favored, positive = home favored
            
            if pd.notna(total) and pd.notna(spread):
                # Average score per team
                avg_score = total / 2.0
                # Home gets: avg + (spread/2), Away gets: avg - (spread/2)
                home_score = avg_score + (spread / 2.0)
                away_score = avg_score - (spread / 2.0)
                return away_score, home_score
            return None, None
        
        df[['closing_away_score', 'closing_home_score']] = df.apply(
            lambda row: pd.Series(calc_market_scores(row)), axis=1
        )
        
        return df
    
    # Priority 2: Alpha predictions
    alpha_files = glob.glob('predictions_alpha_*.csv')
    if alpha_files:
        latest_file = sorted(alpha_files)[-1]
        print(f"✅ Loading alpha predictions from {latest_file}")
        df = pd.read_csv(latest_file)
        return df
    
    # Priority 3: Artifacts folder
    artifacts = Path("artifacts")
    csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
    if not csvs:
        csvs = sorted(artifacts.glob("week_*_projections.csv"))
    if not csvs:
        # Fall back to alpha predictions
        return load_alpha_predictions()
    
    # Get the most recent file that doesn't have "week" in the name (current week)
    # Files with "week1", "week2" etc are historical backfills
    current_week_files = [f for f in csvs if '_week' not in f.name]
    if current_week_files:
        df = pd.read_csv(current_week_files[-1])
    else:
        df = pd.read_csv(csvs[-1])
    return df

@app.route('/')
def index():
    """Main dashboard with all games."""
    df = load_latest_predictions()
    
    if df is None:
        return "<h1>No predictions found. Run generate_alpha_predictions.py first.</h1>"
    
    # Get all weeks available
    all_weeks = sorted(df['week'].unique())
    
    # Determine current week based on today's date
    from datetime import datetime
    today = datetime.now().date()
    
    # Load actual schedule to check which week is current
    import nfl_data_py as nfl
    sched = nfl.import_schedules([2025])
    sched_reg = sched[sched['game_type'] == 'REG']
    
    # Find the week with games starting this week or next
    current_week = None
    for week in sorted(sched_reg['week'].unique()):
        week_games = sched_reg[sched_reg['week'] == week]
        # Check if any games haven't been played yet
        if week_games['away_score'].isna().any():
            current_week = int(week)
            break
    
    if current_week is None:
        current_week = int(df['week'].max())
    
    return render_template('alpha_index_v3.html', 
                          current_week=current_week,
                          all_weeks=all_weeks,
                          total_games=len(df))

@app.route('/api/games')
def api_games():
    """API endpoint for game predictions."""
    df = load_latest_predictions()
    
    if df is None:
        return jsonify({'error': 'No predictions found'}), 404
    
    # Filter to specific week if requested
    week = request.args.get('week', type=int)
    if week:
        df = df[df['week'] == week]
    
    # Convert to JSON, replacing NaN with None
    games = df.replace({pd.NA: None, float('nan'): None}).to_dict('records')
    
    return jsonify({
        'games': games,
        'total': len(games)
    })

@app.route('/api/best-bets')
def api_best_bets():
    """API endpoint for best bets (high confidence picks)."""
    df = load_alpha_predictions()
    
    if df is None:
        return jsonify({'error': 'No predictions found'}), 404
    
    # Filter to upcoming games with high confidence
    upcoming = df[df['game_date'] != '']
    best_bets = upcoming[upcoming['is_high_confidence']].copy()
    
    # Sort by confidence
    best_bets = best_bets.sort_values('best_bet_confidence', ascending=False)
    
    # Convert to dict, replacing NaN with None
    bets = best_bets.replace({pd.NA: None, float('nan'): None}).to_dict('records')
    
    return jsonify({
        'best_bets': bets,
        'total': len(bets)
    })

def load_nflverse_results():
    """Load actual game results from nflverse (cached)."""
    global _results_cache, _results_cache_time
    
    # Cache for 5 minutes
    if _results_cache is not None:
        if _results_cache_time and (datetime.now() - _results_cache_time).seconds < 300:
            return _results_cache
    
    # Load 2025 schedule with results
    sched = nfl.import_schedules([2025])
    sched = sched[sched['game_type'] == 'REG'].copy()
    
    # Normalize team names
    from nfl_edge.team_mapping import normalize_team
    sched['away'] = sched['away_team'].apply(normalize_team)
    sched['home'] = sched['home_team'].apply(normalize_team)
    
    _results_cache = sched
    _results_cache_time = datetime.now()
    
    return sched

def fetch_live_odds():
    """Fetch current live odds from The Odds API for Week 9/10."""
    import requests
    import os
    
    API_KEY = os.getenv('ODDS_API_KEY', '8349c09e3dae852bd7e9bc724819cdd0')
    
    try:
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
        params = {
            'apiKey': API_KEY,
            'regions': 'us',
            'markets': 'spreads,totals',
            'oddsFormat': 'american'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Odds API error: {response.status_code}")
            return {}
        
        games = response.json()
        live_lines = {}
        
        for game in games:
            away = game['away_team'].split()[-1].upper()[:3]  # Simple team mapping
            home = game['home_team'].split()[-1].upper()[:3]
            
            if game.get('bookmakers'):
                book = game['bookmakers'][0]  # Use first book
                spread_line = None
                total_line = None
                
                for market in book['markets']:
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == game['away_team']:
                                spread_line = outcome['point']
                    elif market['key'] == 'totals':
                        total_line = market['outcomes'][0]['point']
                
                if spread_line is not None and total_line is not None:
                    live_lines[(away, home)] = {
                        'spread': spread_line,
                        'total': total_line
                    }
        
        print(f"✅ Fetched live odds for {len(live_lines)} games")
        return live_lines
    except Exception as e:
        print(f"⚠️ Could not fetch live odds: {e}")
        return {}

@app.route('/api/games/graded')
def api_games_graded():
    """API endpoint for games with actual results - SERVES PRE-COMPUTED BACKEND DATA."""
    df = load_latest_predictions()
    
    if df is None:
        return jsonify({'error': 'No predictions found'}), 404
    
    # Filter to specific week if requested
    week = request.args.get('week', type=int)
    if week:
        df = df[df['week'] == week]
    
    # Convert to JSON - all calculations already done in backend
    games = df.replace({pd.NA: None, float('nan'): None}).to_dict('records')
    
    return jsonify({
        'games': games,
        'total': len(games)
    })

@app.route('/api/simulator-predictions')
def api_simulator_predictions():
    """API endpoint for simulator predictions with conviction badges."""
    df = load_simulator_predictions()
    
    if df is None:
        return jsonify({'error': 'No simulator predictions found. Run backtest_all_games_conviction.py and format_for_frontend.py'}), 404
    
    # Filter to specific week if requested
    week = request.args.get('week', type=int)
    if week:
        df = df[df['week'] == week]
    
    # Convert to JSON
    games = df.replace({pd.NA: None, float('nan'): None}).to_dict('records')
    
    return jsonify({
        'games': games,
        'total': len(games)
    })

@app.route('/bets')
def bets():
    """My Bets Dashboard - Database Version"""
    from nfl_edge.bets.db import BettingDB
    
    db = BettingDB()
    
    try:
        # Get all bets (will show pending and settled)
        conn = db.connect()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    b.*,
                    COALESCE(
                        (SELECT COUNT(*) FROM bets b2 WHERE b2.round_robin_parent = b.ticket_id),
                        0
                    ) as round_robin_count
                FROM bets b
                WHERE is_round_robin = FALSE OR round_robin_parent IS NULL
                ORDER BY date DESC, ticket_id
            """)
            all_bets = cur.fetchall()
        
        # Format for template
        bets_data = []
        for bet in all_bets:
            bet_dict = dict(bet)
            # Convert date to string for template
            bet_dict['date'] = bet_dict['date'].strftime('%m/%d/%Y') if bet_dict['date'] else ''
            # Rename bet_type to type for template compatibility
            bet_dict['type'] = bet_dict.pop('bet_type')
            
            # Add sub_bets if it's a round robin parent
            if bet_dict.get('round_robin_count', 0) > 0:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM bets 
                        WHERE round_robin_parent = %s 
                        ORDER BY ticket_id
                    """, (bet_dict['ticket_id'],))
                    sub_bets = cur.fetchall()
                bet_dict['sub_bets'] = [dict(sb) for sb in sub_bets]
            
            bets_data.append(bet_dict)
        
        # Get summary
        summary = db.get_performance_summary()
        
        # Handle empty summary
        if summary is None:
            summary = {
                'total_bets': 0,
                'pending_count': 0,
                'won_count': 0,
                'lost_count': 0,
                'total_wagered': 0,
                'pending_to_win': 0,
                'total_profit': 0,
                'pending_amount': 0,
                'win_rate': 0
            }
        
        summary_data = {
            'total_bets': summary.get('total_bets') or 0,
            'pending': summary.get('pending_count') or 0,
            'won': summary.get('won_count') or 0,
            'lost': summary.get('lost_count') or 0,
            'total_risked': f"${summary.get('total_wagered') or 0:.2f}",
            'total_to_win': f"${summary.get('pending_to_win') or 0:.2f}",
            'total_profit': summary.get('total_profit') or 0,
            'total_amount': summary.get('total_wagered') or 0,
            'pending_amount': summary.get('pending_amount') or 0,
            'potential_win': summary.get('pending_to_win') or 0,
            'won_count': summary.get('won_count') or 0,
            'lost_count': summary.get('lost_count') or 0,
            'pending_count': summary.get('pending_count') or 0,
            'win_rate': float(summary.get('win_rate') or 0)
        }
        
    finally:
        db.close()
    
    return render_template('bets.html', 
                         bets=bets_data,
                         summary=summary_data)

@app.route('/performance')
def performance():
    """Betting Performance Analytics - Database Version"""
    from nfl_edge.bets.db import BettingDB
    
    db = BettingDB()
    
    try:
        # Get overall stats
        summary = db.get_performance_summary()
        
        stats = {
            'total_profit': summary['total_profit'],
            'total_wagered': summary['total_wagered'],
            'roi': summary['roi'],
            'win_rate': summary['win_rate'],
            'total_bets': summary['total_bets'],
            'won_count': summary['won_count'],
            'lost_count': summary['lost_count'],
            'pending_count': summary['pending_count'],
            'pending_amount': summary['pending_amount']
        }
        
        # Performance by bet type
        by_type_list = db.get_performance_by_type()
        by_type = {}
        for bt in by_type_list:
            by_type[bt['bet_type']] = {
                'count': bt['total_bets'],
                'wagered': bt['total_wagered'],
                'won': bt['won_count'],
                'lost': bt['lost_count'],
                'profit': bt['total_profit'],
                'win_rate': bt['win_rate_percentage'],
                'roi': bt['roi_percentage']
            }
        
        # Weekly P/L (from database)
        conn = db.connect()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    TO_CHAR(date, 'MM/DD') as week_key,
                    SUM(profit) as profit
                FROM bets
                WHERE status IN ('Won', 'Lost')
                AND (is_round_robin = FALSE OR round_robin_parent IS NULL)
                GROUP BY week_key
                ORDER BY MIN(date)
            """)
            weekly_data = cur.fetchall()
        
        weekly_pl = {
            'weeks': [w['week_key'] for w in weekly_data],
            'values': [float(w['profit']) for w in weekly_data]
        }
        
        # Bet type distribution
        type_distribution = {
            'labels': list(by_type.keys()),
            'values': [by_type[k]['count'] for k in by_type.keys()]
        }
        
        # Recent settled bets
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM bets 
                WHERE status IN ('Won', 'Lost')
                AND (is_round_robin = FALSE OR round_robin_parent IS NULL)
                ORDER BY date DESC, updated_at DESC
                LIMIT 10
            """)
            recent_bets = cur.fetchall()
        
        # Format recent bets for template
        recent_settled = []
        for bet in recent_bets:
            bet_dict = dict(bet)
            bet_dict['date'] = bet_dict['date'].strftime('%m/%d/%Y') if bet_dict['date'] else ''
            bet_dict['type'] = bet_dict.pop('bet_type')
            recent_settled.append(bet_dict)
        
    finally:
        db.close()
    
    return render_template('performance.html',
                         stats=stats,
                         by_type=by_type,
                         weekly_pl=weekly_pl,
                         type_distribution=type_distribution,
                         recent_settled=recent_settled)

@app.route('/betting-guide')
def betting_guide():
    """Betting guide page."""
    return render_template('betting_guide.html')

@app.route('/game/<away>/<home>')
@app.route('/game/<away>/<home>/<int:week>')
def game_detail(away, home, week=None):
    """Detailed game view with team stats"""
    df_pred = load_latest_predictions()
    
    if df_pred is None:
        return render_template('error.html',
                             message="No predictions found. Run python3 run_week.py first.")
    
    # Normalize column names - simulator uses away_team/home_team, older format uses away/home
    if 'away_team' in df_pred.columns:
        away_col = 'away_team'
        home_col = 'home_team'
    else:
        away_col = 'away'
        home_col = 'home'
    
    # Find the specific game
    if week:
        game = df_pred[
            (df_pred[away_col] == away) & 
            (df_pred[home_col] == home) & 
            (df_pred['week'] == week)
        ]
    else:
        game = df_pred[
            (df_pred[away_col] == away) & 
            (df_pred[home_col] == home)
        ]
    
    if game.empty:
        return render_template('error.html',
                             message=f"Game {away} @ {home} not found.")
    
    game_data = game.iloc[0].to_dict()
    
    # Fetch comprehensive ESPN data
    print(f"Loading game {away} @ {home}...", flush=True)
    try:
        from espn_data_fetcher import ESPNDataFetcher
        espn_data = ESPNDataFetcher.fetch_comprehensive_game_data(away, home)
        game_data['espn_data'] = espn_data
        print(f"✓ ESPN data loaded for {away} @ {home}", flush=True)
    except ImportError as ie:
        print(f"⚠️ Could not import ESPNDataFetcher: {ie}", flush=True)
        game_data['espn_data'] = {
            'away': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': []},
            'home': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': []},
            'game_summary': {}
        }
    except Exception as e:
        print(f"⚠️ Could not fetch ESPN data: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        game_data['espn_data'] = {
            'away': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': []},
            'home': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': []},
            'game_summary': {}
        }
    
    # Build team stats from ESPN data if available
    espn = game_data.get('espn_data', {})
    away_splits = espn.get('away', {}).get('splits', {})
    home_splits = espn.get('home', {}).get('splits', {})
    
    # Try to load team stats from nflverse/nflfastR
    team_stats_away = {}
    team_stats_home = {}
    
    try:
        from nfl_edge.data_ingest import fetch_teamweeks_live
        season = int(game_data.get('season', 2025))
        teamweeks = fetch_teamweeks_live(season)
        
        # Get stats up to current week (prior weeks only)
        current_week = int(game_data.get('week', 9))
        away_stats = teamweeks[
            (teamweeks['team'] == away) & 
            (teamweeks['week'] < current_week)
        ]
        home_stats = teamweeks[
            (teamweeks['team'] == home) & 
            (teamweeks['week'] < current_week)
        ]
        
        if len(away_stats) > 0:
            team_stats_away = {
                'off_epa': float(away_stats['off_epa_per_play'].mean()),
                'def_epa': float(away_stats['def_epa_per_play'].mean()),
                'pass_epa': float(away_stats['off_epa_per_play'].mean() * 0.6),  # Estimate 60% passing
                'rush_epa': float(away_stats['off_epa_per_play'].mean() * 0.4),  # Estimate 40% rushing
                'def_pass_epa': float(away_stats['def_epa_per_play'].mean() * 0.6),
                'def_rush_epa': float(away_stats['def_epa_per_play'].mean() * 0.4),
                'passing_yards': float(away_stats['points'].mean() * 17),  # Estimate ~17 yards per point
                'rushing_yards': float(away_stats['points'].mean() * 10),  # Estimate ~10 yards per point
                'turnovers': int(away_stats['giveaways'].sum()),
                'sacks_taken': 0,  # Not available in this dataset
                'takeaways': int(away_stats['takeaways'].sum()),
            }
            
            # Last 5 games stats
            last_5_away = away_stats.tail(5)
            if len(last_5_away) > 0:
                team_stats_away['last_5_ppg'] = float(last_5_away['points'].mean()) if 'points' in last_5_away.columns else 0.0
                team_stats_away['last_5_pa'] = float(last_5_away['points_allowed'].mean()) if 'points_allowed' in last_5_away.columns else 0.0
        
        if len(home_stats) > 0:
            team_stats_home = {
                'off_epa': float(home_stats['off_epa_per_play'].mean()),
                'def_epa': float(home_stats['def_epa_per_play'].mean()),
                'pass_epa': float(home_stats['off_epa_per_play'].mean() * 0.6),  # Estimate 60% passing
                'rush_epa': float(home_stats['off_epa_per_play'].mean() * 0.4),  # Estimate 40% rushing
                'def_pass_epa': float(home_stats['def_epa_per_play'].mean() * 0.6),
                'def_rush_epa': float(home_stats['def_epa_per_play'].mean() * 0.4),
                'passing_yards': float(home_stats['points'].mean() * 17),  # Estimate ~17 yards per point
                'rushing_yards': float(home_stats['points'].mean() * 10),  # Estimate ~10 yards per point
                'turnovers': int(home_stats['giveaways'].sum()),
                'sacks_taken': 0,  # Not available in this dataset
                'takeaways': int(home_stats['takeaways'].sum()),
            }
            
            # Last 5 games stats
            last_5_home = home_stats.tail(5)
            if len(last_5_home) > 0:
                team_stats_home['last_5_ppg'] = float(last_5_home['points'].mean()) if 'points' in last_5_home.columns else 0.0
                team_stats_home['last_5_pa'] = float(last_5_home['points_allowed'].mean()) if 'points_allowed' in last_5_home.columns else 0.0
        
        print(f"✓ Loaded nflverse stats for {away} and {home}", flush=True)
    except Exception as e:
        print(f"⚠️ Could not load nflverse stats: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    # Merge ESPN data (PPG, PAPG) with nflverse data (EPA, yards, etc.)
    game_data['team_stats'] = {
        'away': {
            'team': away,
            'games': away_splits.get('overall', {}).get('games', 0),
            'ppg': away_splits.get('overall', {}).get('ppg', 0),
            'pa_pg': away_splits.get('overall', {}).get('papg', 0),
            'off_epa': team_stats_away.get('off_epa', 0),
            'def_epa': team_stats_away.get('def_epa', 0),
            'pass_epa': team_stats_away.get('pass_epa', 0),
            'rush_epa': team_stats_away.get('rush_epa', 0),
            'def_pass_epa': team_stats_away.get('def_pass_epa', 0),
            'def_rush_epa': team_stats_away.get('def_rush_epa', 0),
            'passing_yards': team_stats_away.get('passing_yards', 0),
            'rushing_yards': team_stats_away.get('rushing_yards', 0),
            'turnovers': team_stats_away.get('turnovers', 0),
            'sacks_taken': team_stats_away.get('sacks_taken', 0),
            'takeaways': team_stats_away.get('takeaways', 0),
            'last_5_ppg': team_stats_away.get('last_5_ppg', 0),
            'last_5_pa': team_stats_away.get('last_5_pa', 0),
        },
        'home': {
            'team': home,
            'games': home_splits.get('overall', {}).get('games', 0),
            'ppg': home_splits.get('overall', {}).get('ppg', 0),
            'pa_pg': home_splits.get('overall', {}).get('papg', 0),
            'off_epa': team_stats_home.get('off_epa', 0),
            'def_epa': team_stats_home.get('def_epa', 0),
            'pass_epa': team_stats_home.get('pass_epa', 0),
            'rush_epa': team_stats_home.get('rush_epa', 0),
            'def_pass_epa': team_stats_home.get('def_pass_epa', 0),
            'def_rush_epa': team_stats_home.get('def_rush_epa', 0),
            'passing_yards': team_stats_home.get('passing_yards', 0),
            'rushing_yards': team_stats_home.get('rushing_yards', 0),
            'turnovers': team_stats_home.get('turnovers', 0),
            'sacks_taken': team_stats_home.get('sacks_taken', 0),
            'takeaways': team_stats_home.get('takeaways', 0),
            'last_5_ppg': team_stats_home.get('last_5_ppg', 0),
            'last_5_pa': team_stats_home.get('last_5_pa', 0),
        }
    }
    
    # Get recent games from ESPN
    away_recent = espn.get('away', {}).get('last_five', [])
    home_recent = espn.get('home', {}).get('last_five', [])
    
    # Format for template - handle both simulator predictions and old format
    # Simulator predictions use p_home_cover, our_spread, our_total
    # Old format uses 'Home win %', 'Spread used (home-)', 'Total used'
    p_home_cover_val = game_data.get('p_home_cover')
    if 'p_home_cover' in game_data and p_home_cover_val is not None and (isinstance(p_home_cover_val, (int, float)) and not pd.isna(p_home_cover_val)):
        # Simulator predictions format
        home_win_pct = float(p_home_cover_val) * 100
        away_win_pct = float(game_data.get('p_away_cover', 0.5)) * 100
        spread_value = float(game_data.get('our_spread', 0)) if game_data.get('our_spread') is not None else 0
        total_value = float(game_data.get('our_total', 0)) if game_data.get('our_total') is not None else 0
    else:
        # Old format
        home_win_pct = float(game_data.get('Home win %', 50))
        away_win_pct = 100 - home_win_pct
        spread_value = float(game_data.get('Spread used (home-)', 0))
        total_value = float(game_data.get('Total used', 0))
    
    # Format for template
    external_predictions = {
        'your_model': {
            'away_win': round(away_win_pct, 1),
            'home_win': round(home_win_pct, 1),
            'spread': f"{home} {spread_value:+.1f}" if spread_value else f"{home} {0:+.1f}",
            'total': round(total_value, 1) if total_value else 0,
            'source': 'Simulator Model' if 'p_home_cover' in game_data else 'Your Model (Ridge + Monte Carlo)'
        }
    }
    
    return render_template('game_detail.html',
                         away=away,
                         home=home,
                         game=game_data,
                         away_season=game_data['team_stats']['away'],
                         home_season=game_data['team_stats']['home'],
                         away_recent=away_recent,
                         home_recent=home_recent,
                         external_predictions=external_predictions)

@app.route('/api/run-script/<script_name>', methods=['POST'])
def run_script(script_name):
    """Run data update scripts from the UI."""
    import subprocess
    import sys
    
    # Map script names to actual files
    script_map = {
        'ol_continuity': 'calculate_ol_continuity.py',
        'dl_pressure': 'calculate_dl_pressure.py',
        'matchup_stress': 'calculate_matchup_stress.py',
        'predictions': 'generate_alpha_predictions.py',
        'future_stress': 'generate_future_stress_features.py',
        # Simulator prediction scripts
        'sim_backtest': {
            'path': 'backtest_all_games_conviction.py',
            'cwd': 'simulation_engine/nflfastR_simulator'
        },
        'sim_week9_10': {
            'path': 'scripts/generate_week9_10_predictions.py',
            'cwd': 'simulation_engine/nflfastR_simulator'
        },
        'sim_format': {
            'path': 'scripts/format_for_frontend.py',
            'cwd': 'simulation_engine/nflfastR_simulator'
        },
        'sim_all': {
            'path': 'scripts/update_frontend_predictions.sh',
            'cwd': 'simulation_engine/nflfastR_simulator',
            'shell': True
        }
    }
    
    if script_name not in script_map:
        return jsonify({'success': False, 'error': 'Invalid script name'}), 400
    
    script_info = script_map[script_name]
    
    try:
        # Handle both simple string paths and dict configs
        if isinstance(script_info, dict):
            script_file = script_info['path']
            cwd_str = script_info.get('cwd', '.')
            # Resolve relative paths from project root
            if not Path(cwd_str).is_absolute():
                cwd = Path(__file__).parent / cwd_str
            else:
                cwd = Path(cwd_str)
            # Make script path relative to cwd or absolute
            if not Path(script_file).is_absolute():
                script_file = cwd / script_file
            else:
                script_file = Path(script_file)
            use_shell = script_info.get('shell', False)
        else:
            script_file = Path(script_info) if not Path(script_info).is_absolute() else Path(script_info)
            cwd = Path(__file__).parent
            use_shell = False
        
        # Build command - handle shell scripts differently
        if str(script_file).endswith('.sh'):
            cmd = ['bash', str(script_file)]
        else:
            cmd = [sys.executable, str(script_file)]
        
        # Run the script
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for simulator scripts
        )
        
        if result.returncode == 0:
            # Parse output for summary
            output = result.stdout
            lines = output.strip().split('\n')
            
            # Get last meaningful line as message
            message = 'Script completed successfully'
            for line in reversed(lines):
                if line and not line.startswith('=') and not line.startswith('-'):
                    message = line.strip()
                    break
            
            return jsonify({
                'success': True,
                'message': message,
                'output': output[-500:]  # Last 500 chars
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr or 'Script failed',
                'output': result.stdout
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Script timed out (5 min limit)'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reload-data', methods=['POST'])
def reload_data():
    """Reload predictions data from CSV (cache bust)."""
    try:
        # Force reload by directly calling the load function
        df = load_simulator_predictions(force_reload=True)
        
        if df is not None:
            completed = df[df['is_completed'] == True]
            spread_bets = completed[completed['spread_recommendation'].notna() & (completed['spread_recommendation'] != 'Pass')]
            wins = spread_bets[spread_bets['spread_result'] == 'WIN']
            
            return jsonify({
                'success': True,
                'message': 'Data reloaded successfully',
                'stats': {
                    'total_games': len(df),
                    'completed_games': len(completed),
                    'spread_bets': len(spread_bets),
                    'wins': len(wins),
                    'win_rate': f"{len(wins)/len(spread_bets)*100:.1f}%" if len(spread_bets) > 0 else "0%"
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No data file found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/explain-bet', methods=['POST'])
def explain_bet():
    """Generate an LLM explanation for a specific bet recommendation."""
    try:
        data = request.get_json()
        away_team = data.get('awayTeam')
        home_team = data.get('homeTeam')
        week = data.get('week')
        bet_type = data.get('betType', 'spread')
        
        # Load predictions data
        predictions_file = Path("artifacts") / "simulator_predictions.csv"
        if not predictions_file.exists():
            return jsonify({'success': False, 'error': 'Predictions file not found'}), 404
        
        df = pd.read_csv(predictions_file)
        
        # Find the game
        game = df[
            (df['away_team'] == away_team) & 
            (df['home_team'] == home_team) & 
            (df['week'] == week)
        ]
        
        if len(game) == 0:
            return jsonify({'success': False, 'error': 'Game not found'}), 404
        
        game_row = game.iloc[0]
        
        # Generate explanation
        explanation = generate_bet_explanation(game_row, bet_type)
        
        return jsonify({
            'success': True,
            'explanation': explanation
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def generate_bet_explanation(game, bet_type='spread'):
    """Generate a detailed natural language explanation of why we're betting this way."""
    
    if bet_type == 'spread':
        recommendation = game.get('spread_recommendation', 'Pass')
        if recommendation == 'Pass' or pd.isna(recommendation) or recommendation is None:
            return "<p><strong>No Bet Recommended</strong></p><p>The probability is too close to 50% to have an edge over the breakeven threshold (52.4%).</p>"
        
        # Extract data with safe defaults
        away = game['away_team']
        home = game['home_team']
        
        # Determine which team we're betting on
        if 'ATS' in str(recommendation):
            # New format: "BAL ATS" or "MIA ATS"
            bet_team = recommendation.replace(' ATS', '').strip()
            is_home_bet = (bet_team == home)
        else:
            # Old format: "Home ATS" or "Away ATS"
            is_home_bet = 'Home' in str(recommendation)
            bet_team = home if is_home_bet else away
        
        # Safe numeric extraction with fallbacks
        def safe_float(val, default=0.0):
            if val is None or pd.isna(val):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default
        
        market_spread = safe_float(game.get('closing_spread'), 0)
        our_spread = safe_float(game.get('our_spread'), safe_float(game.get('our_home_score')) - safe_float(game.get('our_away_score')))
        
        p_cover = safe_float(game.get('p_home_cover'), 0.5) if is_home_bet else safe_float(game.get('p_away_cover'), 0.5)
        edge = safe_float(game.get('spread_edge_pct'), 0)
        conviction = game.get('spread_conviction', 'MEDIUM')
        if pd.isna(conviction):
            conviction = 'MEDIUM'
        
        raw_home = safe_float(game.get('our_home_score_raw'), 0)
        raw_away = safe_float(game.get('our_away_score_raw'), 0)
        cal_home = safe_float(game.get('our_home_score'), 0)
        cal_away = safe_float(game.get('our_away_score'), 0)
        variance = safe_float(game.get('spread_std'), 11)
        
        # Build explanation
        html = f"""
        <div class="bet-explanation">
            <h4>🎯 {bet_team} to Cover Against the Spread</h4>
            
            <div class="alert alert-info">
                <strong>Bottom Line:</strong> We recommend betting <strong>{bet_team}</strong> with <strong>{conviction}</strong> conviction.
                Our model gives this bet a <strong>{p_cover*100:.1f}% probability</strong> of winning, which is <strong>{edge:.1f}%</strong> above the breakeven threshold.
            </div>
            
            <hr/>
            
            <h5>📊 How We Got Here</h5>
            
            <div class="mb-4">
                <h6>Step 1: Run 100 Play-by-Play Simulations</h6>
                <p>We ran 100 detailed game simulations using:</p>
                <ul>
                    <li>Team-specific offensive/defensive stats (YPP, EPA, red zone efficiency)</li>
                    <li>PFF grades for OL/DL matchups and passing vs coverage</li>
                    <li>QB pressure splits and situational tendencies</li>
                    <li>Drive-by-drive simulation with realistic variance</li>
                </ul>
                <p><strong>Raw Average Result:</strong> {away} {raw_away:.0f}, {home} {raw_home:.0f}</p>
                <p class="text-muted small">This is what the simulations predicted <em>before</em> any adjustments.</p>
            </div>
            
            <div class="mb-4">
                <h6>Step 2: Apply Linear Calibration</h6>
                <p>Raw simulator scores tend to be extreme. We apply a calibration formula learned from historical data:</p>
                <code>calibrated_score = 26.45 + 0.571 × raw_score</code>
                <p><strong>Calibrated Result:</strong> {away} {cal_away:.0f}, {home} {cal_home:.0f}</p>
                <p class="text-muted small">This brings scores closer to realistic NFL scoring levels (league avg ~23 ppg).</p>
            </div>
            
            <div class="mb-4">
                <h6>Step 3: Calculate Probability Distribution</h6>
                <p>The KEY insight: We don't just look at the average! We use the <strong>full distribution</strong> of 100 simulations.</p>
                <ul>
                    <li><strong>Average Spread:</strong> {our_spread:.1f} points</li>
                    <li><strong>Standard Deviation:</strong> {variance:.1f} points (variance matters!)</li>
                    <li><strong>Market Line:</strong> {market_spread:.1f} points</li>
                </ul>
                
                <p>Using a normal distribution with mean={our_spread:.1f} and σ={variance:.1f}, we calculate:</p>
                <p class="text-center"><strong>P({bet_team} covers {market_spread:.1f}) = {p_cover*100:.1f}%</strong></p>
            </div>
            
            <div class="mb-4">
                <h6>Step 4: Isotonic Calibration (Historical Adjustment)</h6>
                <p>Our model has historical biases. We apply an isotonic regression calibrator trained on past games to adjust the raw probability.</p>
                <p class="text-muted small">This accounts for systematic over/under-confidence in certain situations.</p>
            </div>
            
            <hr/>
            
            <h5>🎲 Why This Works</h5>
            
            <div class="alert alert-success">
                <p><strong>The Distribution Tells the Story</strong></p>
                <p>Even if our <em>average</em> prediction differs from the market, the <strong>variance</strong> means many simulations have outcomes beyond the market line.</p>
                
                <p>Example: If we predict {bet_team} wins by {abs(our_spread):.1f} on average (σ={variance:.1f}), then:</p>
                <ul>
                    <li>~16% of simulations are 1 standard deviation above the mean</li>
                    <li>~16% are 1 standard deviation below</li>
                    <li>This creates significant probability mass beyond any reasonable market line</li>
                </ul>
                
                <p class="mb-0">Our <strong>{p_cover*100:.1f}% probability</strong> accounts for this distribution, not just the average!</p>
            </div>
            
            <hr/>
            
            <h5>💰 The Bet</h5>
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title">Market</h6>
                            <p class="card-text">{bet_team} must cover {abs(market_spread):.1f}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-success text-white">
                        <div class="card-body">
                            <h6 class="card-title">Our Edge</h6>
                            <p class="card-text">+{edge:.1f}% over 52.4% breakeven</p>
                            <p class="card-text"><strong>Conviction: {conviction}</strong></p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="mt-3 alert alert-warning">
                <strong>⚠️ Remember:</strong> This is a probabilistic edge, not a guarantee. Even at {p_cover*100:.1f}%, we'll lose ~{(1-p_cover)*100:.0f}% of the time. Bet sizing and bankroll management are critical!
            </div>
        </div>
        """
        
        return html
    
    return "<p>Explanation not available for this bet type.</p>"


@app.route('/api/fetch-live-scores', methods=['POST'])
def fetch_live_scores():
    """Fetch live scores from ESPN and update predictions CSV (cloud-ready endpoint)."""
    import requests
    from datetime import datetime
    
    try:
        predictions_file = Path("artifacts") / "simulator_predictions.csv"
        
        if not predictions_file.exists():
            return jsonify({
                'success': False,
                'error': 'Predictions file not found'
            }), 404
        
        # Fetch scores for current season weeks
        season = 2025
        weeks_to_check = list(range(1, 11))  # Weeks 1-10
        
        total_updates = 0
        games_updated = []
        
        for week in weeks_to_check:
            try:
                url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
                params = {'seasontype': 2, 'week': week, 'year': season}
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse scores
                    scores = []
                    for event in data.get('events', []):
                        competition = event.get('competitions', [{}])[0]
                        competitors = competition.get('competitors', [])
                        status = competition.get('status', {})
                        
                        home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                        away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                        
                        if home_team and away_team:
                            game_state = status.get('type', {}).get('state', 'pre')
                            completed = status.get('type', {}).get('completed', False)
                            
                            if game_state != 'pre':  # Game has started or finished
                                scores.append({
                                    'week': week,
                                    'season': season,
                                    'home_team': home_team['team']['abbreviation'],
                                    'away_team': away_team['team']['abbreviation'],
                                    'home_score': int(home_team.get('score', 0)),
                                    'away_score': int(away_team.get('score', 0)),
                                    'completed': completed,
                                    'game_state': game_state
                                })
                    
                    # Update CSV
                    if scores:
                        df = pd.read_csv(predictions_file)
                        
                        for score in scores:
                            mask = (
                                (df['home_team'] == score['home_team']) & 
                                (df['away_team'] == score['away_team']) & 
                                (df['week'] == score['week']) &
                                (df['season'] == score['season'])
                            )
                            
                            matching_rows = df[mask]
                            
                            if len(matching_rows) > 0:
                                idx = matching_rows.index[0]
                                df.loc[idx, 'actual_home_score'] = score['home_score']
                                df.loc[idx, 'actual_away_score'] = score['away_score']
                                df.loc[idx, 'is_completed'] = score['completed']
                                df.loc[idx, 'final_score'] = f"{score['away_score']}-{score['home_score']}"
                                
                                # Calculate results if completed
                                if score['completed']:
                                    actual_spread = score['home_score'] - score['away_score']
                                    actual_total = score['home_score'] + score['away_score']
                                    
                                    closing_spread = df.loc[idx, 'closing_spread']
                                    closing_total = df.loc[idx, 'closing_total']
                                    
                                    spread_rec = df.loc[idx, 'spread_recommendation']
                                    if pd.notna(spread_rec) and spread_rec != 'Pass':
                                        if 'Home' in spread_rec:
                                            df.loc[idx, 'spread_result'] = 'WIN' if actual_spread > closing_spread else 'LOSS'
                                        elif 'Away' in spread_rec:
                                            df.loc[idx, 'spread_result'] = 'WIN' if actual_spread < closing_spread else 'LOSS'
                                    
                                    total_rec = df.loc[idx, 'total_recommendation']
                                    if pd.notna(total_rec) and total_rec != 'Pass':
                                        if 'Over' in total_rec:
                                            df.loc[idx, 'total_result'] = 'WIN' if actual_total > closing_total else 'LOSS'
                                        elif 'Under' in total_rec:
                                            df.loc[idx, 'total_result'] = 'WIN' if actual_total < closing_total else 'LOSS'
                                
                                total_updates += 1
                                games_updated.append({
                                    'game': f"{score['away_team']}@{score['home_team']}",
                                    'score': f"{score['away_score']}-{score['home_score']}",
                                    'status': 'FINAL' if score['completed'] else 'LIVE'
                                })
                        
                        # Save updated CSV
                        if total_updates > 0:
                            df.to_csv(predictions_file, index=False)
                            
            except Exception as e:
                print(f"Error fetching week {week}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Updated {total_updates} games',
            'games_updated': games_updated,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=False, port=9876, host='0.0.0.0')

