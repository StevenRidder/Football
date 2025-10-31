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

def load_simulator_predictions():
    """Load simulator predictions from backtest_all_games_conviction.py (formatted for frontend)."""
    simulator_file = Path("artifacts") / "simulator_predictions.csv"
    
    if simulator_file.exists():
        print(f"✅ Loading simulator predictions from {simulator_file}")
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
    
    # Find the specific game
    if week:
        game = df_pred[(df_pred['away'] == away) & (df_pred['home'] == home) & (df_pred['week'] == week)]
    else:
        game = df_pred[(df_pred['away'] == away) & (df_pred['home'] == home)]
    
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
    except Exception as e:
        print(f"⚠️ Could not fetch ESPN data: {e}", flush=True)
        game_data['espn_data'] = {
            'away': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': []},
            'home': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': []},
            'game_summary': {}
        }
    
    # Build team stats from ESPN data if available
    espn = game_data.get('espn_data', {})
    away_splits = espn.get('away', {}).get('splits', {})
    home_splits = espn.get('home', {}).get('splits', {})
    
    game_data['team_stats'] = {
        'away': {
            'team': away,
            'games': away_splits.get('overall', {}).get('games', 0),
            'ppg': away_splits.get('overall', {}).get('ppg', 0),
            'pa_pg': away_splits.get('overall', {}).get('papg', 0),
            'off_epa': 0,
            'def_epa': 0,
            'pass_epa': 0,
            'rush_epa': 0,
            'def_pass_epa': 0,
            'def_rush_epa': 0,
            'passing_yards': 0,
            'rushing_yards': 0,
            'turnovers': 0,
            'sacks_taken': 0,
            'takeaways': 0,
            'last_5_ppg': 0,
            'last_5_pa': 0,
        },
        'home': {
            'team': home,
            'games': home_splits.get('overall', {}).get('games', 0),
            'ppg': home_splits.get('overall', {}).get('ppg', 0),
            'pa_pg': home_splits.get('overall', {}).get('papg', 0),
            'off_epa': 0,
            'def_epa': 0,
            'pass_epa': 0,
            'rush_epa': 0,
            'def_pass_epa': 0,
            'def_rush_epa': 0,
            'passing_yards': 0,
            'rushing_yards': 0,
            'turnovers': 0,
            'sacks_taken': 0,
            'takeaways': 0,
            'last_5_ppg': 0,
            'last_5_pa': 0,
        }
    }
    
    # Get recent games from ESPN
    away_recent = espn.get('away', {}).get('last_five', [])
    home_recent = espn.get('home', {}).get('last_five', [])
    
    # Format for template
    external_predictions = {
        'your_model': {
            'away_win': round(100 - game_data.get('Home win %', 50), 1),
            'home_win': round(game_data.get('Home win %', 50), 1),
            'spread': f"{home} {game_data.get('Spread used (home-)', 0):+.1f}",
            'total': round(game_data.get('Total used', 0), 1),
            'source': 'Your Model (Ridge + Monte Carlo)'
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
        'future_stress': 'generate_future_stress_features.py'
    }
    
    if script_name not in script_map:
        return jsonify({'success': False, 'error': 'Invalid script name'}), 400
    
    script_file = script_map[script_name]
    
    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, script_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
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

if __name__ == '__main__':
    app.run(debug=False, port=9876, host='0.0.0.0')

