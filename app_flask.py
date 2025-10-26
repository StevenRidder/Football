"""
NFL Edge - Tabler Dashboard
Flask application serving NFL predictions with official Tabler UI
"""
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import pandas as pd
from datetime import date
import requests
import io
from nfl_edge.data_ingest import fetch_teamweeks_live
from nfl_edge.predictions_api import fetch_all_predictions
from nfl_edge.accuracy_tracker import create_tracker
from nfl_edge.bets.betonline_client import (
    fetch_all_bets, normalize_to_ledger, save_ledger, 
    load_ledger, get_weekly_summary, _headers_from_config, parse_curl_to_headers
)
from live_bet_tracker import LiveBetTracker

app = Flask(__name__)

# Load latest predictions
def load_latest_predictions():
    """Load most recent week's predictions"""
    artifacts = Path("artifacts")
    csvs = sorted(artifacts.glob("week_*_projections.csv"))
    if not csvs:
        return None
    
    df = pd.read_csv(csvs[-1])
    return df

def load_latest_aii():
    """Load most recent AII data"""
    artifacts = Path("artifacts")
    csvs = sorted(artifacts.glob("aii_*.csv"))
    if not csvs:
        return None
    
    return pd.read_csv(csvs[-1])

@app.route('/')
def index():
    """Main dashboard"""
    df = load_latest_predictions()
    
    if df is None:
        return render_template('error.html', 
                             message="No predictions found. Run python3 run_week.py first.")
    
    # Calculate summary stats
    total_games = len(df)
    avg_edge = df['EV_spread'].mean() * 100 if 'EV_spread' in df.columns else 0
    total_stake = df['Stake_spread'].sum() + df['Stake_total'].sum() if 'Stake_spread' in df.columns else 0
    
    # Count recommended plays
    rec_plays = 0
    if 'Rec_spread' in df.columns:
        rec_plays = len(df[df['Rec_spread'] != 'NO PLAY'])
    
    return render_template('index.html',
                         total_games=total_games,
                         avg_edge=avg_edge,
                         total_stake=total_stake,
                         rec_plays=rec_plays)

@app.route('/api/games')
def api_games():
    """API endpoint for game data"""
    df = load_latest_predictions()
    
    if df is None:
        return jsonify({'error': 'No data'}), 404
    
    # Convert to dict for JSON
    games = []
    for _, row in df.iterrows():
        game = {
            'away': row['away'],
            'home': row['home'],
            'exp_score': row.get('Exp score (away-home)', 'N/A'),
            'spread': row.get('Spread used (home-)', 0),
            'total': row.get('Total used', 0),
            'home_win_pct': row.get('Home win %', 0),
            'home_cover_pct': row.get('Home cover %', 0),
            'over_pct': row.get('Over %', 0),
            'ev_spread': row.get('EV_spread', 0) * 100,
            'ev_total': row.get('EV_total', 0) * 100,
            'stake_spread': row.get('Stake_spread', 0),
            'stake_total': row.get('Stake_total', 0),
            'rec_spread': row.get('Rec_spread', 'NO PLAY'),
            'rec_total': row.get('Rec_total', 'NO PLAY'),
            'best_bet': row.get('Best_bet', 'NO PLAY')
        }
        games.append(game)
    
    return jsonify(games)

@app.route('/api/best-bets')
def api_best_bets():
    """API endpoint for best betting opportunities"""
    df = load_latest_predictions()
    
    if df is None:
        return jsonify({'error': 'No data'}), 404
    
    # Filter to only recommended plays
    if 'EV_spread' in df.columns and 'EV_total' in df.columns:
        df['max_ev'] = df[['EV_spread', 'EV_total']].max(axis=1)
        best = df[df['max_ev'] > 0.02].sort_values('max_ev', ascending=False)
    else:
        best = df
    
    bets = []
    for _, row in best.iterrows():
        # Determine which bet is better
        ev_spread = row.get('EV_spread', 0)
        ev_total = row.get('EV_total', 0)
        
        if ev_spread > ev_total:
            bet = {
                'game': f"{row['away']} @ {row['home']}",
                'type': 'SPREAD',
                'recommendation': row.get('Rec_spread', 'NO PLAY'),
                'ev': ev_spread * 100,
                'stake': row.get('Stake_spread', 0),
                'probability': row.get('Home cover %', 0)
            }
        else:
            bet = {
                'game': f"{row['away']} @ {row['home']}",
                'type': 'TOTAL',
                'recommendation': row.get('Rec_total', 'NO PLAY'),
                'ev': ev_total * 100,
                'stake': row.get('Stake_total', 0),
                'probability': row.get('Over %', 0)
            }
        
        bets.append(bet)
    
    return jsonify(bets)

@app.route('/api/aii')
def api_aii():
    """API endpoint for Analytics Intensity Index"""
    df = load_latest_aii()
    
    if df is None:
        return jsonify({'error': 'No AII data. Run python3 run_analytics.py first.'}), 404
    
    teams = []
    for _, row in df.iterrows():
        teams.append({
            'team': row['team'],
            'aii_score': row['aii_normalized'],
            'projected_wins': row.get('projected_wins', 0),
            'analytics_tier': row.get('analytics_tier', 3)
        })
    
    return jsonify(teams)

@app.route('/analytics')
def analytics():
    """Analytics Intensity Index page"""
    df = load_latest_aii()
    
    if df is None:
        return render_template('error.html',
                             message="No AII data found. Run python3 run_analytics.py first.")
    
    return render_template('analytics.html',
                         total_teams=len(df))

@app.route('/game/<away>/<home>')
def game_detail(away, home):
    """Detailed game view with team stats"""
    df_pred = load_latest_predictions()
    
    if df_pred is None:
        return render_template('error.html',
                             message="No predictions found. Run python3 run_week.py first.")
    
    # Find the specific game
    game = df_pred[(df_pred['away'] == away) & (df_pred['home'] == home)]
    
    if game.empty:
        return render_template('error.html',
                             message=f"Game {away} @ {home} not found.")
    
    game_data = game.iloc[0].to_dict()
    
    # Fetch detailed team stats - HYBRID: ESPN scores + NFLverse stats
    try:
        print("Fetching hybrid data: ESPN (scores) + NFLverse (stats)...")
        
        # 1. Get accurate scores from ESPN
        espn_games = []
        for week in range(1, 18):
            try:
                espn_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
                params = {'seasontype': 2, 'week': week, 'year': 2025}
                response = requests.get(espn_url, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    events = data.get('events', [])
                    
                    for event in events:
                        for comp in event.get('competitions', []):
                            competitors = comp.get('competitors', [])
                            if len(competitors) == 2:
                                home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                                away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                                
                                if home_team and away_team:
                                    espn_games.append({
                                        'week': week,
                                        'home_team': home_team['team']['abbreviation'],
                                        'away_team': away_team['team']['abbreviation'],
                                        'home_score': int(home_team.get('score', 0)),
                                        'away_score': int(away_team.get('score', 0)),
                                        'completed': comp.get('status', {}).get('type', {}).get('completed', False)
                                    })
            except Exception as e:
                print(f"ESPN fetch error week {week}: {e}")
                continue
        
        print(f"✅ ESPN: Fetched {len(espn_games)} games (accurate scores)")
        df_espn = pd.DataFrame(espn_games)
        
        # 2. Get detailed stats from NFLverse
        nflverse_url = "https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2025.csv"
        response = requests.get(nflverse_url, timeout=30)
        df_nflverse = pd.read_csv(io.BytesIO(response.content))
        
        print(f"✅ NFLverse: Fetched {len(df_nflverse)} team-week records (detailed stats)")
        
        # Filter to 2025 season
        df_nflverse = df_nflverse[df_nflverse['season'] == 2025].copy()
        
        if df_espn.empty:
            raise Exception("No ESPN data available")
        
        # 3. Merge ESPN scores with NFLverse stats
        # Create a function to merge data for a specific team
        def get_team_games(team_code):
            games = []
            for _, espn_game in df_espn.iterrows():
                week = espn_game['week']
                
                # CRITICAL FIX: Only include COMPLETED games (skip future scheduled games)
                if not espn_game.get('completed', False):
                    continue
                
                # Check if team played in this game
                if espn_game['away_team'] == team_code:
                    is_home = False
                    opponent = espn_game['home_team']
                    pts_scored = espn_game['away_score']
                    pts_allowed = espn_game['home_score']
                elif espn_game['home_team'] == team_code:
                    is_home = True
                    opponent = espn_game['away_team']
                    pts_scored = espn_game['home_score']
                    pts_allowed = espn_game['away_score']
                else:
                    continue
                
                # Skip if scores are 0-0 (likely incomplete data)
                if pts_scored == 0 and pts_allowed == 0:
                    continue
                
                # Get detailed stats from NFLverse for this team/week
                nfl_stats = df_nflverse[(df_nflverse['team'] == team_code) & (df_nflverse['week'] == week)]
                
                if not nfl_stats.empty:
                    stats_row = nfl_stats.iloc[0]
                    games.append({
                        'week': week,
                        'opponent': opponent,
                        'points_scored': pts_scored,  # ESPN (accurate)
                        'points_allowed': pts_allowed,  # ESPN (accurate)
                        'result': 'W' if pts_scored > pts_allowed else ('L' if pts_scored < pts_allowed else 'T'),
                        # NFLverse detailed stats
                        'passing_epa': stats_row.get('passing_epa', 0),
                        'rushing_epa': stats_row.get('rushing_epa', 0),
                        'passing_yards': stats_row.get('passing_yards', 0),
                        'rushing_yards': stats_row.get('rushing_yards', 0),
                        'passing_tds': stats_row.get('passing_tds', 0),
                        'rushing_tds': stats_row.get('rushing_tds', 0),
                        'turnovers': stats_row.get('passing_interceptions', 0) + stats_row.get('rushing_fumbles_lost', 0),
                        'sacks_taken': stats_row.get('sacks_suffered', 0),
                    })
                else:
                    # ESPN data only (no NFLverse stats available)
                    games.append({
                        'week': week,
                        'opponent': opponent,
                        'points_scored': pts_scored,
                        'points_allowed': pts_allowed,
                        'result': 'W' if pts_scored > pts_allowed else ('L' if pts_scored < pts_allowed else 'T'),
                        'passing_epa': 0,
                        'rushing_epa': 0,
                        'passing_yards': 0,
                        'rushing_yards': 0,
                        'passing_tds': 0,
                        'rushing_tds': 0,
                        'turnovers': 0,
                        'sacks_taken': 0,
                    })
            
            return pd.DataFrame(games).sort_values('week', ascending=False) if games else pd.DataFrame()
        
        away_stats = get_team_games(away)
        home_stats = get_team_games(home)
        
        # Calculate season averages for away team (ESPN + NFLverse hybrid)
        away_season = {
            'team': away,
            'games': len(away_stats),
            # ESPN data (accurate scores)
            'ppg': away_stats['points_scored'].mean() if len(away_stats) > 0 else 0,
            'pa_pg': away_stats['points_allowed'].mean() if len(away_stats) > 0 else 0,
            # NFLverse data (advanced analytics)
            'off_epa': (away_stats['passing_epa'].mean() + away_stats['rushing_epa'].mean()) if len(away_stats) > 0 else 0,
            'pass_epa': away_stats['passing_epa'].mean() if len(away_stats) > 0 else 0,
            'rush_epa': away_stats['rushing_epa'].mean() if len(away_stats) > 0 else 0,
            'passing_yards': away_stats['passing_yards'].mean() if len(away_stats) > 0 else 0,
            'rushing_yards': away_stats['rushing_yards'].mean() if len(away_stats) > 0 else 0,
            'turnovers': away_stats['turnovers'].sum() if len(away_stats) > 0 else 0,
            'sacks_taken': away_stats['sacks_taken'].sum() if len(away_stats) > 0 else 0,
            # Defensive stats (would need opponent data for full picture)
            'def_epa': 0,
            'def_pass_epa': 0,
            'def_rush_epa': 0,
            'takeaways': 0,
            # Last 5 games
            'last_5_ppg': away_stats.head(5)['points_scored'].mean() if len(away_stats) >= 5 else (away_stats['points_scored'].mean() if len(away_stats) > 0 else 0),
            'last_5_pa': away_stats.head(5)['points_allowed'].mean() if len(away_stats) >= 5 else (away_stats['points_allowed'].mean() if len(away_stats) > 0 else 0),
        }
        
        # Calculate season averages for home team (ESPN + NFLverse hybrid)
        home_season = {
            'team': home,
            'games': len(home_stats),
            # ESPN data (accurate scores)
            'ppg': home_stats['points_scored'].mean() if len(home_stats) > 0 else 0,
            'pa_pg': home_stats['points_allowed'].mean() if len(home_stats) > 0 else 0,
            # NFLverse data (advanced analytics)
            'off_epa': (home_stats['passing_epa'].mean() + home_stats['rushing_epa'].mean()) if len(home_stats) > 0 else 0,
            'pass_epa': home_stats['passing_epa'].mean() if len(home_stats) > 0 else 0,
            'rush_epa': home_stats['rushing_epa'].mean() if len(home_stats) > 0 else 0,
            'passing_yards': home_stats['passing_yards'].mean() if len(home_stats) > 0 else 0,
            'rushing_yards': home_stats['rushing_yards'].mean() if len(home_stats) > 0 else 0,
            'turnovers': home_stats['turnovers'].sum() if len(home_stats) > 0 else 0,
            'sacks_taken': home_stats['sacks_taken'].sum() if len(home_stats) > 0 else 0,
            # Defensive stats
            'def_epa': 0,
            'def_pass_epa': 0,
            'def_rush_epa': 0,
            'takeaways': 0,
            # Last 5 games
            'last_5_ppg': home_stats.head(5)['points_scored'].mean() if len(home_stats) >= 5 else (home_stats['points_scored'].mean() if len(home_stats) > 0 else 0),
            'last_5_pa': home_stats.head(5)['points_allowed'].mean() if len(home_stats) >= 5 else (home_stats['points_allowed'].mean() if len(home_stats) > 0 else 0),
        }
        
        # Recent games are already formatted correctly from the DataFrame
        away_recent = away_stats.to_dict('records') if not away_stats.empty else []
        home_recent = home_stats.to_dict('records') if not home_stats.empty else []
        
    except Exception as e:
        print(f"Error fetching team stats: {e}")
        away_season = {'team': away, 'games': 0}
        home_season = {'team': home, 'games': 0}
        away_recent = []
        home_recent = []
    
    # Fetch predictions from multiple sources (ESPN, 538, Vegas)
    print(f"Fetching predictions for {away} @ {home}...")
    all_predictions = fetch_all_predictions(away, home)
    
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
    
    # Add 538 if available
    if all_predictions.get('fivethirtyeight'):
        pred = all_predictions['fivethirtyeight']
        external_predictions['fivethirtyeight'] = {
            'away_win': pred.get('away_win_prob', 50),
            'home_win': pred.get('home_win_prob', 50),
            'spread': 'N/A',
            'total': 'N/A',
            'source': pred.get('source', '538 ELO'),
            'confidence': pred.get('confidence', 'Medium')
        }
    
    # Add Vegas consensus if available
    if all_predictions.get('vegas'):
        pred = all_predictions['vegas']
        external_predictions['vegas'] = {
            'away_win': pred.get('away_win_prob', 50),
            'home_win': pred.get('home_win_prob', 50),
            'spread': 'N/A',
            'total': 'N/A',
            'source': pred.get('source', 'Vegas Consensus'),
            'moneyline': f"{pred.get('avg_away_ml', 0):+d} / {pred.get('avg_home_ml', 0):+d}",
            'confidence': 'High'
        }
    
    # Also get sportsbook lines for spread/total
    try:
        import os
        api_key = os.environ.get('ODDS_API_KEY', '')
        if api_key:
            odds_url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
            params = {
                'apiKey': api_key,
                'regions': 'us',
                'markets': 'spreads,totals',
                'oddsFormat': 'american'
            }
            response = requests.get(odds_url, params=params, timeout=10)
            if response.status_code == 200:
                odds_data = response.json()
                
                for game_odds in odds_data:
                    if away in game_odds.get('away_team', '') and home in game_odds.get('home_team', ''):
                        spreads = []
                        totals = []
                        
                        for bookmaker in game_odds.get('bookmakers', []):
                            for market in bookmaker.get('markets', []):
                                if market['key'] == 'spreads':
                                    for outcome in market['outcomes']:
                                        if home in outcome.get('name', ''):
                                            spreads.append(outcome.get('point', 0))
                                elif market['key'] == 'totals':
                                    if market.get('outcomes'):
                                        totals.append(market['outcomes'][0].get('point', 0))
                        
                        if spreads and totals and 'vegas' in external_predictions:
                            external_predictions['vegas']['spread'] = f"{home} {sum(spreads)/len(spreads):+.1f}"
                            external_predictions['vegas']['total'] = round(sum(totals)/len(totals), 1)
                        break
    except Exception as e:
        print(f"Error fetching spreads/totals: {e}")
    
    return render_template('game_detail.html',
                         away=away,
                         home=home,
                         game=game_data,
                         away_season=away_season,
                         home_season=home_season,
                         away_recent=away_recent,
                         home_recent=home_recent,
                         external_predictions=external_predictions)

@app.route('/accuracy')
def accuracy():
    """Model accuracy tracking page"""
    tracker = create_tracker()
    
    # Get accuracy report for 2025 season
    report = tracker.get_accuracy_report(season=2025, min_games=1)
    
    # Get game-by-game breakdown
    game_breakdown = tracker.get_game_breakdown(season=2025, min_games=1)
    report['game_breakdown'] = game_breakdown
    
    return render_template('accuracy.html', report=report, season=2025)

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

@app.route('/api/bets/paste', methods=['POST'])
def api_paste_bets():
    """API endpoint to parse pasted bet data"""
    try:
        data = request.json or {}
        bet_data = data.get('data', '').strip()
        
        if not bet_data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            })
        
        # Parse the pasted data
        bets = []
        lines = [line.strip() for line in bet_data.split('\n') if line.strip()]
        
        for line in lines:
            parts = line.split('|')
            if len(parts) >= 6:
                try:
                    ticket = parts[0].strip()
                    date = parts[1].strip()
                    
                    # For parlays with multiple legs, everything between date and the last 4 fields is description
                    # Last 4 fields are: Type, Status, Amount, ToWin
                    # So we need to join all middle parts as description
                    bet_type = parts[-4].strip()
                    status = parts[-3].strip()
                    amount = float(parts[-2].strip())
                    to_win = float(parts[-1].strip()) if len(parts) > 6 else 0.0
                    
                    # Description is everything between date and type
                    description_parts = parts[2:-4]
                    description = ' | '.join(description_parts).strip()
                    
                    # Calculate profit based on status
                    if status == 'Won':
                        profit = to_win
                    elif status == 'Lost':
                        profit = -amount
                    else:  # Pending
                        profit = 0.0
                    
                    bets.append({
                        'ticket_id': ticket,
                        'date': date,
                        'description': description,
                        'type': bet_type,
                        'status': status,
                        'amount': amount,
                        'to_win': to_win,
                        'profit': profit
                    })
                except Exception as e:
                    print(f"Error parsing line: {line} - {e}")
                    continue
        
        if not bets:
            return jsonify({
                'success': False,
                'message': 'Could not parse any bets from the data'
            })
        
        # Calculate summary
        total_amount = sum(b['amount'] for b in bets)
        total_profit = sum(b['profit'] for b in bets)
        pending_amount = sum(b['amount'] for b in bets if b['status'] == 'Pending')
        potential_win = sum(b['to_win'] for b in bets if b['status'] == 'Pending')
        
        won_bets = [b for b in bets if b['status'] == 'Won']
        lost_bets = [b for b in bets if b['status'] == 'Lost']
        pending_bets = [b for b in bets if b['status'] == 'Pending']
        
        summary = {
            'total_bets': len(bets),
            'total_amount': total_amount,
            'total_profit': total_profit,
            'pending_amount': pending_amount,
            'potential_win': potential_win,
            'won_count': len(won_bets),
            'lost_count': len(lost_bets),
            'pending_count': len(pending_bets),
            'win_rate': (len(won_bets) / (len(won_bets) + len(lost_bets)) * 100) if (len(won_bets) + len(lost_bets)) > 0 else 0
        }
        
        # Save to JSON
        import json
        from datetime import datetime
        output = {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'bets': bets
        }
        
        Path('artifacts').mkdir(exist_ok=True)
        with open('artifacts/betonline_bets.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Loaded {len(bets)} bets',
            'count': len(bets),
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Parse failed: {str(e)}'
        })

@app.route('/api/bets/fetch-from-curl', methods=['POST'])
def api_fetch_from_curl():
    """API endpoint to fetch all bets using a cURL command"""
    try:
        from nfl_edge.bets.betonline_client import parse_curl_to_headers, fetch_all_bets, normalize_to_ledger
        
        data = request.json or {}
        curl_cmd = data.get('curl', '').strip()
        
        if not curl_cmd:
            return jsonify({
                'success': False,
                'message': 'No cURL command provided'
            })
        
        # Parse cURL to get headers
        parsed = parse_curl_to_headers(curl_cmd)
        headers = {k: v for k, v in parsed.items() if not k.startswith("__")}
        
        # Debug: Log what headers we extracted
        print(f"🔑 Extracted headers: {list(headers.keys())}")
        print(f"🔐 Has Authorization: {'authorization' in [k.lower() for k in headers.keys()]}")
        
        # Fetch all bets from BetOnline
        raw_data = fetch_all_bets(headers)
        
        # Debug: Show what we got back
        debug_info = raw_data.get('debug', [])
        debug_msg = '\n'.join(debug_info)
        
        ledger_df = normalize_to_ledger(raw_data)
        
        if ledger_df.empty:
            return jsonify({
                'success': False,
                'message': f'No bets found from BetOnline API.\n\nDebug Info:\n{debug_msg}\n\nRaw keys: {list(raw_data.keys())}'
            })
        
        # Convert to web format
        bets = []
        for _, row in ledger_df.iterrows():
            desc_parts = []
            if row['market']:
                desc_parts.append(row['market'])
            if row['submarket']:
                desc_parts.append(row['submarket'])
            if row['line']:
                desc_parts.append(f"Line: {row['line']}")
            if row['odds_american']:
                desc_parts.append(f"Odds: {row['odds_american']}")
            
            description = ' | '.join(desc_parts) if desc_parts else 'No description'
            
            if row['settlement'] == 'Pending':
                status = 'Pending'
            elif row['result'] == 'Win':
                status = 'Won'
            elif row['result'] == 'Loss':
                status = 'Lost'
            else:
                status = row['settlement']
            
            if status == 'Won':
                profit = row['profit']
            elif status == 'Lost':
                profit = -row['stake']
            else:
                profit = 0.0
            
            bets.append({
                'ticket_id': str(row['ticket_id']),
                'date': row['placed_utc'][:10] if row['placed_utc'] else '',
                'description': description,
                'type': row['market'] or 'Unknown',
                'status': status,
                'amount': float(row['stake']),
                'to_win': float(row['profit']) if row['profit'] else 0.0,
                'profit': float(profit)
            })
        
        # Calculate summary
        total_amount = sum(b['amount'] for b in bets)
        total_profit = sum(b['profit'] for b in bets)
        pending_amount = sum(b['amount'] for b in bets if b['status'] == 'Pending')
        potential_win = sum(b['to_win'] for b in bets if b['status'] == 'Pending')
        
        won_bets = [b for b in bets if b['status'] == 'Won']
        lost_bets = [b for b in bets if b['status'] == 'Lost']
        pending_bets = [b for b in bets if b['status'] == 'Pending']
        
        summary = {
            'total_bets': len(bets),
            'total_amount': total_amount,
            'total_profit': total_profit,
            'pending_amount': pending_amount,
            'potential_win': potential_win,
            'won_count': len(won_bets),
            'lost_count': len(lost_bets),
            'pending_count': len(pending_bets),
            'win_rate': (len(won_bets) / (len(won_bets) + len(lost_bets)) * 100) if (len(won_bets) + len(lost_bets)) > 0 else 0
        }
        
        # Save to JSON
        import json
        from datetime import datetime
        output = {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'bets': bets
        }
        
        Path('artifacts').mkdir(exist_ok=True)
        with open('artifacts/betonline_bets.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Fetched {len(bets)} bets from BetOnline!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to fetch bets: {str(e)}'
        })

@app.route('/api/bets/auto-fetch', methods=['POST'])
def api_auto_fetch_bets():
    """API endpoint to auto-fetch bets from BetOnline using saved session"""
    try:
        import subprocess
        
        # Check if session exists
        session_file = Path('artifacts/betonline_session.json')
        if not session_file.exists():
            return jsonify({
                'success': False,
                'message': 'No saved session found. Run setup first.',
                'need_setup': True
            })
        
        # Run the auto-fetch script
        result = subprocess.run(
            ['python3', 'auto_fetch_bets.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Load the fetched data to get count
            bet_file = Path('artifacts/betonline_bets.json')
            if bet_file.exists():
                with open(bet_file, 'r') as f:
                    data = json.load(f)
                    bet_count = len(data.get('bets', []))
                    
                return jsonify({
                    'success': True,
                    'message': f'Fetched {bet_count} bets from BetOnline!'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Fetch completed but no bets file created'
                })
        else:
            error_msg = result.stderr or result.stdout or 'Unknown error'
            return jsonify({
                'success': False,
                'message': f'Fetch failed: {error_msg[:200]}',
                'need_setup': 'session' in error_msg.lower() or 'expired' in error_msg.lower()
            })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'Fetch timed out. Try again.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fetch failed: {str(e)}'
        })

@app.route('/api/bets/clear', methods=['POST'])
def api_clear_bets():
    """API endpoint to clear all bets"""
    try:
        # Remove the JSON file
        bet_file = Path('artifacts/betonline_bets.json')
        if bet_file.exists():
            bet_file.unlink()
        
        return jsonify({
            'success': True,
            'message': 'All bets cleared'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Clear failed: {str(e)}'
        })


@app.route('/api/bets/upload-csv', methods=['POST'])
def api_upload_csv():
    """Upload CSV file with bet data"""
    try:
        data = request.json
        csv_data = data.get('csv', '')
        
        if not csv_data:
            return jsonify({
                'success': False,
                'message': 'No CSV data provided'
            })
        
        # Parse CSV
        import io
        df = pd.read_csv(io.StringIO(csv_data))
        
        # Convert to our format
        bets = []
        for _, row in df.iterrows():
            bet = {
                'date': str(row.get('Date', '')),
                'game': str(row.get('Game', '')),
                'type': str(row.get('Type', '')),
                'amount': float(row.get('Amount', 0)),
                'result': str(row.get('Result', '')),
                'profit': float(row.get('Profit', 0))
            }
            bets.append(bet)
        
        # Save to file
        bet_data = {
            'timestamp': datetime.now().isoformat(),
            'total_bets': len(bets),
            'bets': bets
        }
        
        with open('artifacts/bets.json', 'w') as f:
            json.dump(bet_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Uploaded {len(bets)} bets successfully!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'CSV upload failed: {str(e)}'
        })

@app.route('/api/bets/add-manual', methods=['POST'])
def api_add_manual():
    """Add a bet manually"""
    try:
        data = request.json
        
        # Load existing bets
        bets = []
        if Path('artifacts/bets.json').exists():
            with open('artifacts/bets.json', 'r') as f:
                bet_data = json.load(f)
                bets = bet_data.get('bets', [])
        
        # Add new bet
        new_bet = {
            'date': data.get('date', ''),
            'game': data.get('game', ''),
            'type': data.get('type', ''),
            'amount': float(data.get('amount', 0)),
            'result': data.get('result', ''),
            'profit': float(data.get('amount', 0)) if data.get('result') == 'Win' else -float(data.get('amount', 0)) if data.get('result') == 'Loss' else 0
        }
        
        bets.append(new_bet)
        
        # Save updated bets
        bet_data = {
            'timestamp': datetime.now().isoformat(),
            'total_bets': len(bets),
            'bets': bets
        }
        
        Path('artifacts').mkdir(exist_ok=True)
        with open('artifacts/bets.json', 'w') as f:
            json.dump(bet_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Bet added successfully!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to add bet: {str(e)}'
        })
def api_bets_summary():
    """API endpoint for bet summary data"""
    ledger_df = load_ledger("artifacts/bets.parquet")
    
    if ledger_df is None:
        return jsonify({
            'success': False,
            'message': 'No bet data found'
        })
    
    summary = get_weekly_summary(ledger_df)
    return jsonify({
        'success': True,
        'summary': summary
    })

@app.route('/api/record-prediction', methods=['POST'])
def record_prediction():
    """API endpoint to record predictions (for future use)"""
    try:
        tracker = create_tracker()
        data = request.json
        
        tracker.record_prediction(
            week=data['week'],
            season=data['season'],
            away=data['away'],
            home=data['home'],
            your_model=data.get('your_model'),
            fivethirtyeight=data.get('fivethirtyeight'),
            vegas=data.get('vegas')
        )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/live-bet-status')
def live_bet_status():
    """Get live status for all pending bets"""
    try:
        tracker = LiveBetTracker()
        statuses = tracker.update_all_bets()
        
        # Format for frontend
        result = {}
        for bet_status in statuses:
            if bet_status['live_status']:
                result[bet_status['ticket_number']] = {
                    'status': bet_status['live_status'],
                    'color': tracker.get_status_color(bet_status['live_status']),
                    'game': bet_status['game_info']
                }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/live-games')
def live_games():
    """Get all live games with scores and recommended bet status"""
    try:
        # Team name to abbreviation mapping
        TEAM_MAP = {
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
            'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'
        }
        
        tracker = LiveBetTracker()
        
        # Get all live games from ESPN
        all_live_games = []
        for sport in ['NFL']:  # Can add more sports later
            games = tracker.get_live_games(sport)
            all_live_games.extend(games)
        
        # Load predictions to match recommendations
        df = load_latest_predictions()
        
        result = []
        for game in all_live_games:
            # Convert full names to abbreviations
            away_abbr = TEAM_MAP.get(game['away_team'], game['away_team'])
            home_abbr = TEAM_MAP.get(game['home_team'], game['home_team'])
            
            # Try to find this game in predictions
            game_row = None
            if df is not None:
                # Match by team abbreviations
                for _, row in df.iterrows():
                    if (away_abbr == row.get('away', '') and 
                        home_abbr == row.get('home', '')):
                        game_row = row
                        break
            
            # Determine if recommended bets are winning
            spread_status = None
            total_status = None
            
            if game_row is not None:
                # Check spread recommendation
                rec_spread = game_row.get('Rec_spread', game_row.get('rec_spread', ''))
                if 'BET' in str(rec_spread):
                    # Parse which team and line
                    if away_abbr in str(rec_spread) or 'away' in str(rec_spread).lower():
                        # Recommended away team
                        score_diff = game['away_score'] - game['home_score']
                        # Extract line from recommendation (e.g., "+3.5")
                        import re
                        line_match = re.search(r'([+-]?\d+\.?\d*)', rec_spread)
                        if line_match:
                            line = float(line_match.group(1))
                            if score_diff + line > 0:
                                spread_status = 'winning'
                            elif score_diff + line < 0:
                                spread_status = 'losing'
                            else:
                                spread_status = 'neutral'
                    elif home_abbr in str(rec_spread) or 'home' in str(rec_spread).lower():
                        # Recommended home team
                        score_diff = game['home_score'] - game['away_score']
                        import re
                        line_match = re.search(r'([+-]?\d+\.?\d*)', rec_spread)
                        if line_match:
                            line = float(line_match.group(1))
                            if score_diff + line > 0:
                                spread_status = 'winning'
                            elif score_diff + line < 0:
                                spread_status = 'losing'
                            else:
                                spread_status = 'neutral'
                
                # Check total recommendation
                rec_total = game_row.get('Rec_total', game_row.get('rec_total', ''))
                if 'OVER' in str(rec_total):
                    total_score = game['away_score'] + game['home_score']
                    import re
                    line_match = re.search(r'(\d+\.?\d*)', rec_total)
                    if line_match:
                        total_line = float(line_match.group(1))
                        if total_score > total_line:
                            total_status = 'winning'
                        elif total_score < total_line:
                            total_status = 'losing'
                        else:
                            total_status = 'neutral'
                elif 'UNDER' in str(rec_total):
                    total_score = game['away_score'] + game['home_score']
                    import re
                    line_match = re.search(r'(\d+\.?\d*)', rec_total)
                    if line_match:
                        total_line = float(line_match.group(1))
                        if total_score < total_line:
                            total_status = 'winning'
                        elif total_score > total_line:
                            total_status = 'losing'
                        else:
                            total_status = 'neutral'
            
            result.append({
                'away_team': game['away_team'],
                'home_team': game['home_team'],
                'away_abbr': away_abbr,  # Add abbreviations for easy matching
                'home_abbr': home_abbr,
                'away_score': game['away_score'],
                'home_score': game['home_score'],
                'period': game['period'],
                'clock': game.get('clock', ''),
                'status': game['status'],
                'spread_status': spread_status,
                'total_status': total_status,
                'best_status': spread_status or total_status  # Use whichever has a status
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=9876)

