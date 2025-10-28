"""
NFL Edge - Tabler Dashboard
Flask application serving NFL predictions with official Tabler UI
"""
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import pandas as pd
from datetime import datetime
import requests
import io
import json
from nfl_edge.predictions_api import fetch_all_predictions
from nfl_edge.accuracy_tracker import create_tracker
from nfl_edge.bets.betonline_client import (
    load_ledger, get_weekly_summary
)
from live_bet_tracker import LiveBetTracker

app = Flask(__name__)

# Load latest predictions
def load_latest_predictions():
    """Load most recent week's predictions"""
    artifacts = Path("artifacts")
    # First try new format (predictions_2025_*.csv), then fall back to old format
    csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
    if not csvs:
        csvs = sorted(artifacts.glob("week_*_projections.csv"))
    if not csvs:
        return None
    
    # Get the most recent file that doesn't have "week" in the name (current week)
    # Files with "week1", "week2" etc are historical backfills
    current_week_files = [f for f in csvs if '_week' not in f.name]
    if current_week_files:
        df = pd.read_csv(current_week_files[-1])
    else:
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
    
    # Get current week from schedules.py
    try:
        from schedules import CURRENT_WEEK, CURRENT_SEASON
        current_week = CURRENT_WEEK
        current_season = CURRENT_SEASON
    except ImportError:
        current_week = 8
        current_season = 2025
    
    # Calculate summary stats
    total_games = len(df)
    avg_edge = df['EV_spread'].mean() * 100 if 'EV_spread' in df.columns else 0
    total_stake = df['Stake_spread'].sum() + df['Stake_total'].sum() if 'Stake_spread' in df.columns else 0
    
    # Count recommended plays
    rec_plays = 0
    if 'Rec_spread' in df.columns:
        rec_plays = len(df[df['Rec_spread'] != 'NO PLAY'])
    
    return render_template('index.html',
                         current_week=current_week,
                         current_season=current_season,
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
            'market_spread': row.get('Spread used (home-)', 0),
            'model_spread': row.get('Model spread home-', 0),
            'market_total': row.get('Total used', 0),
            'model_total': row.get('Model total', 0),
            'spread': row.get('Spread used (home-)', 0),  # Keep for backward compatibility
            'total': row.get('Total used', 0),  # Keep for backward compatibility
            'home_win_pct': row.get('Home win %', 0),
            'home_cover_pct': row.get('Home cover %', 0),
            'over_pct': row.get('Over %', 0),
            'ev_spread': row.get('EV_spread', 0) * 100,
            'ev_total': row.get('EV_total', 0) * 100,
            'stake_spread': row.get('Stake_spread', 0),
            'stake_total': row.get('Stake_total', 0),
            'rec_spread': row.get('Rec_spread', 'NO PLAY'),
            'rec_total': row.get('Rec_total', 'NO PLAY'),
            'best_bet': row.get('Best_bet', 'NO PLAY'),
            'confidence_level': row.get('confidence_level', 'MEDIUM'),
            'confidence_pct': row.get('confidence_pct', 50)
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
    
    """
    # DISABLED CODE - was making 17 ESPN API calls on every page load
    if False:  # Disabled for performance
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
    """
    
    # Fetch predictions from multiple sources (ESPN, 538, Vegas)
    # Temporarily disabled - was causing timeouts
    # print(f"Fetching predictions for {away} @ {home}...")
    # all_predictions = fetch_all_predictions(away, home)
    all_predictions = {}
    
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
                         away_season=game_data['team_stats']['away'],
                         home_season=game_data['team_stats']['home'],
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

@app.route('/line-movements')
def line_movements():
    """Line movement tracking page"""
    from line_tracker import LineTracker
    from schedules import CURRENT_WEEK, CURRENT_SEASON
    
    tracker = LineTracker()
    movements = tracker.get_week_movements(CURRENT_SEASON, CURRENT_WEEK)
    
    return render_template('line_movements.html', 
                         movements=movements,
                         week=CURRENT_WEEK,
                         season=CURRENT_SEASON)

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

@app.route('/api/bets/load', methods=['POST'])
def api_load_bets():
    """API endpoint to load bets from pasted data (upsert: update if exists, insert if new)"""
    try:
        data = request.get_json()
        bets = data.get('bets', [])
        
        print("=== API LOAD BETS CALLED ===")
        print(f"Received {len(bets)} bets")
        for bet in bets:
            print(f"  Bet: {bet.get('ticket_id')} - desc length: {len(bet.get('description', ''))}")
        
        if not bets:
            print("No bets in request!")
            return jsonify({
                'success': False,
                'message': 'No bets provided'
            })
        
        # Add/update bets in database
        from nfl_edge.bets.db import BettingDB
        db = BettingDB()
        conn = db.connect()
        
        inserted = 0
        updated = 0
        
        for bet in bets:
            try:
                ticket_id = bet.get('ticket_id')
                
                # Check if bet already exists
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM bets WHERE ticket_id = %s', (ticket_id,))
                    existing = cur.fetchone()
                    
                    if existing:
                        # Update existing bet (only if new description is more detailed)
                        existing_desc = existing.get('description', '')
                        new_desc = bet.get('description', '')
                        
                        print(f"Bet {ticket_id} exists. Existing desc length: {len(existing_desc)}, New desc length: {len(new_desc)}")
                        
                        # Update if new description is longer (more detailed)
                        if len(new_desc) > len(existing_desc):
                            print(f"Updating bet {ticket_id} with longer description")
                            cur.execute('''
                                UPDATE bets 
                                SET description = %s, 
                                    date = %s,
                                    bet_type = %s,
                                    amount = %s,
                                    to_win = %s,
                                    status = %s
                                WHERE ticket_id = %s
                            ''', (
                                new_desc,
                                bet.get('date'),
                                bet.get('bet_type'),
                                bet.get('amount'),
                                bet.get('to_win'),
                                bet.get('status', 'Pending'),
                                ticket_id
                            ))
                            updated += 1
                        else:
                            print(f"Skipping bet {ticket_id} - new description not longer")
                    else:
                        # Insert new bet
                        print(f"Inserting new bet {ticket_id}")
                        db.insert_bet(bet)
                        inserted += 1
                        
            except Exception as e:
                print(f"Error upserting bet {bet.get('ticket_id')}: {e}")
                import traceback
                traceback.print_exc()
        
        conn.commit()
        db.close()
        
        message = f'Loaded {inserted} new bet(s)'
        if updated > 0:
            message += f', updated {updated} existing bet(s) with more details'
        
        return jsonify({
            'success': True,
            'inserted': inserted,
            'updated': updated,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Load failed: {str(e)}'
        })

@app.route('/api/bets/update-status', methods=['POST'])
def api_update_bet_status():
    """API endpoint to update bet status (Won/Lost/Pending)"""
    try:
        data = request.get_json()
        ticket_id = data.get('ticket_id')
        new_status = data.get('status')
        
        if not ticket_id or not new_status:
            return jsonify({
                'success': False,
                'message': 'Missing ticket_id or status'
            })
        
        if new_status not in ['Won', 'Lost', 'Pending']:
            return jsonify({
                'success': False,
                'message': 'Invalid status. Must be Won, Lost, or Pending'
            })
        
        from nfl_edge.bets.db import BettingDB
        db = BettingDB()
        conn = db.connect()
        
        with conn.cursor() as cur:
            # Update bet status
            cur.execute(
                'UPDATE bets SET status = %s WHERE ticket_id = %s',
                (new_status, ticket_id)
            )
            
            # If marking as Won or Lost, calculate profit
            if new_status in ['Won', 'Lost']:
                cur.execute(
                    'SELECT amount, to_win FROM bets WHERE ticket_id = %s',
                    (ticket_id,)
                )
                bet = cur.fetchone()
                
                if bet:
                    amount = float(bet['amount']) if bet['amount'] else 0
                    to_win = float(bet['to_win']) if bet['to_win'] else 0
                    
                    if new_status == 'Won':
                        profit = to_win
                    else:  # Lost
                        profit = -amount
                    
                    cur.execute(
                        'UPDATE bets SET profit = %s WHERE ticket_id = %s',
                        (profit, ticket_id)
                    )
        
        conn.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'message': f'Bet {ticket_id} marked as {new_status}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Update failed: {str(e)}'
        })

@app.route('/api/bets/auto-grade', methods=['POST'])
def api_auto_grade_bets():
    """Auto-grade all pending bets based on completed games"""
    try:
        from nfl_edge.bets.db import BettingDB
        from live_bet_tracker import LiveBetTracker
        import re
        
        db = BettingDB()
        tracker = LiveBetTracker()
        conn = db.connect()
        
        # Get all pending bets
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM bets WHERE status = %s', ('Pending',))
            pending_bets = cur.fetchall()
        
        with open('/tmp/autograde_start.log', 'a') as f:
            f.write(f"Found {len(pending_bets)} pending bets\n")
        
        graded = 0
        won_count = 0
        lost_count = 0
        still_pending = 0
        
        # Get all games (live and final)
        all_games = []
        for sport in ['NFL']:
            games = tracker.get_live_games(sport)
            all_games.extend(games)
        
        # Get final games only
        final_games = [g for g in all_games if 'final' in g.get('status', '').lower()]
        
        for bet in pending_bets:
            bet_dict = dict(bet)
            description = bet_dict.get('description', '')
            bet_type = bet_dict.get('bet_type', '').lower()
            
            # DEBUG
            with open('/tmp/all_bets_debug.log', 'a') as f:
                f.write(f"\nProcessing bet: {bet_dict['ticket_id']}\n")
                f.write(f"  Type: {bet_type}\n")
            
            # Handle parlays and single bets differently
            is_parlay = 'parlay' in bet_type or 'teaser' in bet_type
            
            with open('/tmp/all_bets_debug.log', 'a') as f:
                f.write(f"  is_parlay: {is_parlay}\n")
            
            new_status = None
            
            # === PARLAY GRADING ===
            if is_parlay:
                # DEBUG
                with open('/tmp/parlay_debug.log', 'a') as f:
                    f.write(f"\nProcessing parlay: {bet_dict['ticket_id']}\n")
                    f.write(f"  Type: {bet_type}\n")
                    f.write(f"  Description: {description[:100]}...\n")
                
                # Check if description has detailed leg format with status (Won/Lost/Pending)
                # Format: "Team +X | Status" or just "Team +X"
                has_leg_status = '| Won' in description or '| Lost' in description or '| Pending' in description
                
                with open('/tmp/parlay_debug.log', 'a') as f:
                    f.write(f"  has_leg_status: {has_leg_status}\n")
                
                if has_leg_status:
                    # Parse detailed format - but RE-EVALUATE legs against current games
                    # Don't trust stale statuses in description!
                    # Example: "Minnesota Vikings +9 +100 For Game | 10/23/2025 | 08:15:00 PM (EST) | Lost"
                    legs = description.split('Football - NFL -')[1:]  # Split by game separator
                    
                    any_leg_lost = False
                    all_legs_final = True
                    
                    for leg in legs:
                        # Extract bet details from leg (ignore old status)
                        # Parse spread/total from leg description
                        spread_match = re.search(r'([+-]\d+(?:½|\.5)?)', leg)
                        total_match = re.search(r'(over|under)\s+(\d+(?:\.5)?)', leg, re.IGNORECASE)
                        
                        # Try to find the game this leg is for
                        leg_game = None
                        for game in all_games:
                            game_teams = [game.get('home_team', ''), game.get('away_team', '')]
                            if any(team in leg for team in game_teams):
                                leg_game = game
                                break
                        
                        if not leg_game:
                            # Can't find game - keep pending
                            all_legs_final = False
                            continue
                        
                        # Check if this game is final
                        if 'final' not in leg_game.get('status', '').lower():
                            all_legs_final = False
                            continue
                        
                        # Determine if leg won or lost based on actual game result
                        if spread_match:
                            # Spread bet
                            spread = float(spread_match.group(1).replace('½', '.5'))
                            # Determine which team
                            is_home = leg_game['home_team'] in leg
                            if is_home:
                                effective_diff = (leg_game['home_score'] - leg_game['away_score']) + spread
                            else:
                                effective_diff = (leg_game['away_score'] - leg_game['home_score']) + spread
                            
                            if effective_diff <= 0:
                                any_leg_lost = True
                                break
                        elif total_match:
                            # Total bet
                            total_line = float(total_match.group(2))
                            actual_total = leg_game['home_score'] + leg_game['away_score']
                            is_over = 'over' in total_match.group(1).lower()
                            
                            if is_over and actual_total <= total_line:
                                any_leg_lost = True
                                break
                            elif not is_over and actual_total >= total_line:
                                any_leg_lost = True
                                break
                    
                    # Grade the bet
                    if any_leg_lost:
                        new_status = 'Lost'
                    elif all_legs_final:
                        new_status = 'Won'
                    else:
                        # Still has pending legs
                        still_pending += 1
                        continue
                    
                else:
                    # Check if it's a Same Game Parlay with pipe-separated legs
                    if '|' in description and ('same game parlay' in bet_type or 'same game' in description.lower()):
                        # DEBUG
                        with open('/tmp/sgp_debug.log', 'a') as f:
                            f.write(f"Processing SGP: {bet_dict['ticket_id']}\n")
                        
                        # Parse SGP format: "Team1 v Team2 | Leg1 | Leg2 | Leg3"
                        parts = description.split('|')
                        if len(parts) < 2:
                            with open('/tmp/sgp_debug.log', 'a') as f:
                                f.write(f"  Not enough parts: {len(parts)}\n")
                            still_pending += 1
                            continue
                        
                        # Extract game info from first part
                        game_part = parts[0]
                        leg_parts = parts[1:]
                        
                        # Find the game
                        sgp_game = None
                        for game in all_games:
                            game_teams = [game.get('home_team', ''), game.get('away_team', '')]
                            if any(team in game_part for team in game_teams):
                                sgp_game = game
                                break
                        
                        if not sgp_game:
                            with open('/tmp/sgp_debug.log', 'a') as f:
                                f.write("  Game not found\n")
                            still_pending += 1
                            continue
                        
                        with open('/tmp/sgp_debug.log', 'a') as f:
                            f.write(f"  Found game: {sgp_game['away_team']} @ {sgp_game['home_team']}\n")
                            f.write(f"  Status: {sgp_game.get('status')}\n")
                        
                        # Check if game is final
                        if 'final' not in sgp_game.get('status', '').lower():
                            with open('/tmp/sgp_debug.log', 'a') as f:
                                f.write("  Game not final yet\n")
                            still_pending += 1
                            continue
                        
                        # Grade all legs including player props
                        any_leg_lost = False
                        all_legs_graded = True
                        
                        for leg in leg_parts:
                            leg_lower = leg.lower()
                            
                            # Check for player props FIRST (before checking for over/under)
                            if 'player' in leg_lower:
                                game_id = sgp_game.get('id')
                                if game_id:
                                    prop_status = tracker.player_tracker.check_prop_bet(game_id, leg)
                                    if prop_status == 'losing':
                                        any_leg_lost = True
                                        break
                                    elif prop_status is None or prop_status == 'neutral':
                                        # Can't determine yet
                                        all_legs_graded = False
                                        break
                                    # If 'winning', continue to next leg
                                else:
                                    all_legs_graded = False
                                    break
                            
                            # Check for moneyline
                            elif 'money line' in leg_lower or 'moneyline' in leg_lower:
                                is_home = sgp_game['home_team'] in leg
                                is_away = sgp_game['away_team'] in leg
                                if is_home and sgp_game['home_score'] <= sgp_game['away_score']:
                                    any_leg_lost = True
                                    break
                                elif is_away and sgp_game['away_score'] <= sgp_game['home_score']:
                                    any_leg_lost = True
                                    break
                            
                            # Check for total
                            elif 'total points' in leg_lower or ('over' in leg_lower or 'under' in leg_lower):
                                total_match = re.search(r'(over|under)\s+(\d+(?:\.5)?)', leg, re.IGNORECASE)
                                if total_match:
                                    total_line = float(total_match.group(2))
                                    actual_total = sgp_game['home_score'] + sgp_game['away_score']
                                    is_over = 'over' in total_match.group(1).lower()
                                    
                                    if is_over and actual_total <= total_line:
                                        any_leg_lost = True
                                        break
                                    elif not is_over and actual_total >= total_line:
                                        any_leg_lost = True
                                        break
                        
                        # Grade the SGP
                        with open('/tmp/sgp_debug.log', 'a') as f:
                            f.write(f"  any_leg_lost: {any_leg_lost}\n")
                            f.write(f"  all_legs_graded: {all_legs_graded}\n")
                        
                        if any_leg_lost:
                            new_status = 'Lost'
                            with open('/tmp/sgp_debug.log', 'a') as f:
                                f.write("  Result: Lost\n")
                        elif all_legs_graded:
                            new_status = 'Won'
                            with open('/tmp/sgp_debug.log', 'a') as f:
                                f.write("  Result: Won\n")
                        else:
                            # Some legs can't be graded yet
                            with open('/tmp/sgp_debug.log', 'a') as f:
                                f.write("  Result: Still Pending\n")
                            still_pending += 1
                            continue
                    
                    # Parse simple format: "12-team parlay: CAR +7, NYG +7.5, ..."
                    else:
                        match = re.search(r'parlay:\s*(.+)', description, re.IGNORECASE)
                        if not match:
                            still_pending += 1
                            continue
                        
                        legs_str = match.group(1)
                        legs = [leg.strip() for leg in legs_str.split(',')]
                        
                        all_legs_completed = True
                        any_leg_lost = False
                        
                        for leg in legs:
                            # Parse leg like "CAR +7" or "MIA +7.5"
                            leg_match = re.match(r'([A-Z]+)\s+([-+]?\d+(?:\.\d+)?)', leg)
                            if not leg_match:
                                all_legs_completed = False
                                continue
                            
                            team_abbr = leg_match.group(1)
                            spread = float(leg_match.group(2))
                            
                            # Find matching game
                            game_found = False
                            for game in all_games:
                                if game.get('away_abbr') == team_abbr or game.get('home_abbr') == team_abbr:
                                    game_found = True
                                    
                                    # Check if game is completed (status contains "Final")
                                    if 'final' not in game.get('status', '').lower():
                                        all_legs_completed = False
                                        # Don't break - keep checking other legs for losses
                                        continue
                                    
                                    # Determine if leg won or lost
                                    if game.get('away_abbr') == team_abbr:
                                        score_diff = game['away_score'] - game['home_score']
                                    else:
                                        score_diff = game['home_score'] - game['away_score']
                                    
                                    effective_diff = score_diff + spread
                                    
                                    if effective_diff < 0:
                                        any_leg_lost = True
                                        # IMMEDIATELY mark parlay as lost - don't wait for other games
                                        break
                                    elif effective_diff == 0:
                                        # Push - treat as loss for parlays
                                        any_leg_lost = True
                                        break
                                    break
                            
                            if not game_found:
                                all_legs_completed = False
                                # Don't break - keep checking other legs for losses
                            
                            # If we found a lost leg, immediately grade as lost
                            if any_leg_lost:
                                break
                        
                        # Grade the bet if ANY leg is lost OR all legs are completed
                        if any_leg_lost:
                            new_status = 'Lost'
                        elif all_legs_completed:
                            new_status = 'Won'
                        else:
                            # Still has pending legs and no losses yet
                            still_pending += 1
                            continue
            
            # === SINGLE BET GRADING ===
            else:
                # Grade single bets (spread, total, moneyline)
                
                # Use LiveBetTracker to get bet status
                bet_data = {
                    'ticket_number': bet_dict['ticket_id'],
                    'description': description,
                    'bet_type': bet_type,
                    'team': tracker._extract_team(description),
                    'line': tracker._extract_line(description)
                }
                
                # Find matching game
                matched_game = None
                for game in final_games:
                    teams = [game.get('home_team', ''), game.get('away_team', '')]
                    if any(bet_data['team'] in team for team in teams):
                        matched_game = game
                        break
                
                if not matched_game:
                    still_pending += 1
                    continue
                
                # Check bet result
                status = tracker.get_bet_status(bet_data, matched_game)
                
                if status == 'winning':
                    new_status = 'Won'
                elif status == 'losing':
                    new_status = 'Lost'
                else:
                    still_pending += 1
                    continue
            
            # Update bet status if we have a decision
            if not new_status:
                still_pending += 1
                continue
            
            # Update bet status
            amount = float(bet_dict['amount']) if bet_dict['amount'] else 0
            to_win = float(bet_dict['to_win']) if bet_dict['to_win'] else 0
            profit = to_win if new_status == 'Won' else -amount
            
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE bets SET status = %s, profit = %s WHERE ticket_id = %s',
                    (new_status, profit, bet_dict['ticket_id'])
                )
            
            graded += 1
            if new_status == 'Won':
                won_count += 1
            else:
                lost_count += 1
        
        conn.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'graded': graded,
            'won': won_count,
            'lost': lost_count,
            'still_pending': still_pending
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Auto-grade failed: {str(e)}'
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

@app.route('/api/bet-legs/<ticket_id>')
def api_bet_legs(ticket_id):
    """Get parlay legs with live status for a bet (backend calculates status)"""
    try:
        from nfl_edge.bets.db import BettingDB
        
        db = BettingDB()
        bet = db.get_bet_with_legs(ticket_id)
        db.close()
        
        if not bet:
            return jsonify({'success': False, 'message': 'Bet not found'}), 404
        
        if not bet.get('legs'):
            return jsonify({'success': True, 'legs': []})
        
        # Get live games for status calculation
        tracker = LiveBetTracker()
        live_games = tracker.get_live_games()
        
        # Calculate live status for each leg
        legs_with_status = []
        for leg in bet['legs']:
            leg_dict = dict(leg)
            
            # Calculate live status on backend
            status = tracker.get_leg_live_status(
                leg['description'],
                leg.get('team'),
                leg.get('line'),
                live_games,
                bet['description']  # Full bet description for context
            )
            
            leg_dict['live_status'] = status
            leg_dict['color'] = tracker.get_status_color(status) if status else 'white'
            legs_with_status.append(leg_dict)
        
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'bet_type': bet['bet_type'],
            'legs': legs_with_status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/check-player-prop')
def check_player_prop():
    """Check status of a player prop bet"""
    try:
        game_id = request.args.get('game_id')
        prop_description = request.args.get('prop')
        
        if not game_id or not prop_description:
            return jsonify({'error': 'Missing game_id or prop parameter'}), 400
        
        from player_stats_tracker import PlayerStatsTracker
        tracker = PlayerStatsTracker()
        
        status = tracker.check_prop_bet(game_id, prop_description)
        
        return jsonify({
            'status': status,
            'color': 'success' if status == 'winning' else 'danger' if status == 'losing' else 'warning' if status == 'neutral' else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-model-performance', methods=['POST'])
def api_update_model_performance():
    """Trigger model performance update"""
    try:
        import subprocess
        
        # Run the update script
        result = subprocess.run(
            ['python3', 'update_model_performance.py'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Model performance updated successfully!',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error updating model performance',
                'error': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'Update timed out'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/config/calibration', methods=['GET'])
def api_get_calibration():
    """Get current calibration factor from config.yaml"""
    try:
        import yaml
        from pathlib import Path
        
        config_path = Path('/Users/steveridder/Git/Football/config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        calibration = config.get('score_calibration_factor', 0.54)
        recent_weight = config.get('recent_weight', 0.85)
        
        return jsonify({
            'success': True,
            'calibration': calibration,
            'recent_weight': recent_weight
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/config/calibration', methods=['POST'])
def api_set_calibration():
    """Update calibration factor in config.yaml and optionally regenerate predictions"""
    try:
        import yaml
        from pathlib import Path
        
        data = request.json
        new_calibration = float(data.get('calibration'))
        regenerate = data.get('regenerate', True)
        
        if not (0.1 <= new_calibration <= 1.5):
            return jsonify({
                'success': False,
                'message': 'Calibration must be between 0.1 and 1.5'
            }), 400
        
        # Update config.yaml
        config_path = Path('/Users/steveridder/Git/Football/config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        old_calibration = config.get('score_calibration_factor', 0.54)
        config['score_calibration_factor'] = new_calibration
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        message = f'Calibration updated from {old_calibration} to {new_calibration}'
        
        # Optionally regenerate predictions
        if regenerate:
            import subprocess
            result = subprocess.run(
                ['python3', '-c', 'from nfl_edge.main import run_week; run_week()'],
                cwd='/Users/steveridder/Git/Football',
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                message += '. Predictions regenerated!'
            else:
                message += f'. Warning: Regeneration had issues: {result.stderr[:200]}'
        
        return jsonify({
            'success': True,
            'message': message,
            'old_calibration': old_calibration,
            'new_calibration': new_calibration
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to update calibration: {str(e)}'
        }), 500

@app.route('/api/generate-predictions', methods=['POST'])
def api_generate_predictions():
    """Generate predictions for next week"""
    try:
        import subprocess
        from pathlib import Path
        
        # Run the prediction script
        result = subprocess.run(
            ['python3', '-c', 'from nfl_edge.main import run_week; run_week()'],
            cwd='/Users/steveridder/Git/Football',
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            # Find the latest prediction file
            artifacts_dir = Path('/Users/steveridder/Git/Football/artifacts')
            csv_files = sorted(artifacts_dir.glob('predictions_*.csv'), reverse=True)
            
            if csv_files:
                latest_file = csv_files[0]
                return jsonify({
                    'success': True,
                    'message': 'Predictions generated successfully',
                    'file': latest_file.name,
                    'output': result.stdout
                })
        
        return jsonify({
            'success': False,
            'message': 'Prediction generation failed',
            'error': result.stderr
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Generation failed: {str(e)}'
        })

@app.route('/api/predictions/history', methods=['GET'])
def api_predictions_history():
    """Get list of historical prediction files"""
    try:
        from pathlib import Path
        import re
        
        artifacts_dir = Path('/Users/steveridder/Git/Football/artifacts')
        
        # Get only weekly prediction files (predictions_2025_weekN_*.csv)
        csv_files = sorted(artifacts_dir.glob('predictions_2025_week*.csv'), reverse=True)
        
        history = []
        for csv_file in csv_files:
            # Extract week number from filename
            match = re.search(r'week(\d+)', csv_file.name)
            if match:
                week_num = match.group(1)
                history.append({
                    'date': f'Week {week_num}',
                    'filename': csv_file.name,
                    'week': int(week_num)
                })
        
        # Sort by week number descending
        history.sort(key=lambda x: x['week'], reverse=True)
        
        return jsonify({
            'success': True,
            'predictions': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to load history: {str(e)}'
        })

@app.route('/api/predictions/<filename>', methods=['GET'])
def api_get_prediction_file(filename):
    """Get a specific prediction file"""
    try:
        from pathlib import Path
        import pandas as pd
        
        # Security: only allow predictions_*.csv files
        if not filename.startswith('predictions_') or not filename.endswith('.csv'):
            return jsonify({'success': False, 'message': 'Invalid filename'}), 400
        
        file_path = Path('/Users/steveridder/Git/Football/artifacts') / filename
        
        if not file_path.exists():
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        df = pd.read_csv(file_path)
        
        # Convert to JSON format similar to main page
        predictions = []
        for _, row in df.iterrows():
            predictions.append({
                'away': row['away'],
                'home': row['home'],
                'exp_score': row.get('Exp score (away-home)', ''),
                'model_spread': row.get('Model spread home-', 0),
                'spread_used': row.get('Spread used (home-)', 0),
                'home_cover_pct': row.get('Home cover %', 0),
                'over_pct': row.get('Over %', 0),
                'best_bet': row.get('best_bet', ''),
                'kelly_pct': row.get('kelly_pct', 0),
                'ev': row.get('ev', 0)
            })
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'date': filename.replace('predictions_', '').replace('.csv', '')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to load predictions: {str(e)}'
        })

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
            best_bet_type = None  # Track which type of bet is the "best"
            
            if game_row is not None:
                # Determine the best bet type from the best_bet column
                best_bet = game_row.get('best_bet', game_row.get('Best_bet', ''))
                if 'SPREAD' in str(best_bet).upper():
                    best_bet_type = 'spread'
                elif 'TOTAL' in str(best_bet).upper() or 'OVER' in str(best_bet).upper() or 'UNDER' in str(best_bet).upper():
                    best_bet_type = 'total'
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
            
            # Determine best_status based on which bet type is recommended
            if best_bet_type == 'total':
                best_status = total_status or spread_status
            elif best_bet_type == 'spread':
                best_status = spread_status or total_status
            else:
                # If we can't determine, use whichever has a status
                best_status = spread_status or total_status
            
            result.append({
                'id': game.get('id'),  # Add game ID for player prop lookups
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
                'best_status': best_status
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=9876)

