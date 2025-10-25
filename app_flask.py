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
    
    # Ensure ODDS_API_KEY is set for Vegas predictions
    import os
    if not os.environ.get('ODDS_API_KEY'):
        print("⚠️ ODDS_API_KEY not set - Vegas predictions will be unavailable")
    
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
    
    return render_template('accuracy.html', report=report, season=2025)

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

if __name__ == '__main__':
    app.run(debug=True, port=9876)

