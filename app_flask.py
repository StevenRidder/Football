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
    
    # Fetch detailed team stats - use ESPN API (more accurate than NFLverse)
    try:
        # Fetch from ESPN's official API
        print("Fetching game data from ESPN API...")
        
        # Get all 2025 season games from ESPN
        espn_games = []
        for week in range(1, 18):  # Fetch all weeks
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
                                # Parse teams and scores
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
        
        print(f"Fetched {len(espn_games)} games from ESPN")
        
        # Convert to DataFrame for easier processing
        df_season = pd.DataFrame(espn_games)
        
        if df_season.empty:
            raise Exception("No ESPN data available")
        
        # Get stats for both teams (filter where team played as either home or away)
        away_games = []
        for _, game in df_season.iterrows():
            if game['away_team'] == away:
                away_games.append({
                    'week': game['week'],
                    'opponent': game['home_team'],
                    'points_scored': game['away_score'],
                    'points_allowed': game['home_score'],
                    'result': 'W' if game['away_score'] > game['home_score'] else ('L' if game['away_score'] < game['home_score'] else 'T')
                })
            elif game['home_team'] == away:
                away_games.append({
                    'week': game['week'],
                    'opponent': game['away_team'],
                    'points_scored': game['home_score'],
                    'points_allowed': game['away_score'],
                    'result': 'W' if game['home_score'] > game['away_score'] else ('L' if game['home_score'] < game['away_score'] else 'T')
                })
        
        home_games = []
        for _, game in df_season.iterrows():
            if game['away_team'] == home:
                home_games.append({
                    'week': game['week'],
                    'opponent': game['home_team'],
                    'points_scored': game['away_score'],
                    'points_allowed': game['home_score'],
                    'result': 'W' if game['away_score'] > game['home_score'] else ('L' if game['away_score'] < game['home_score'] else 'T')
                })
            elif game['home_team'] == home:
                home_games.append({
                    'week': game['week'],
                    'opponent': game['away_team'],
                    'points_scored': game['home_score'],
                    'points_allowed': game['away_score'],
                    'result': 'W' if game['home_score'] > game['away_score'] else ('L' if game['home_score'] < game['away_score'] else 'T')
                })
        
        away_stats = pd.DataFrame(away_games).sort_values('week', ascending=False) if away_games else pd.DataFrame()
        home_stats = pd.DataFrame(home_games).sort_values('week', ascending=False) if home_games else pd.DataFrame()
        
        # Calculate season averages for away team
        away_season = {
            'team': away,
            'games': len(away_stats),
            'ppg': away_stats['points_scored'].mean() if len(away_stats) > 0 else 0,
            'pa_pg': away_stats['points_allowed'].mean() if len(away_stats) > 0 else 0,
            'off_epa': 0,  # ESPN doesn't provide EPA in basic scoreboard
            'def_epa': 0,
            'pass_epa': 0,
            'rush_epa': 0,
            'def_pass_epa': 0,
            'def_rush_epa': 0,
            'turnovers': 0,  # Would need detailed stats
            'takeaways': 0,
            'last_5_ppg': away_stats.head(5)['points_scored'].mean() if len(away_stats) >= 5 else (away_stats['points_scored'].mean() if len(away_stats) > 0 else 0),
            'last_5_pa': away_stats.head(5)['points_allowed'].mean() if len(away_stats) >= 5 else (away_stats['points_allowed'].mean() if len(away_stats) > 0 else 0),
        }
        
        # Calculate season averages for home team
        home_season = {
            'team': home,
            'games': len(home_stats),
            'ppg': home_stats['points_scored'].mean() if len(home_stats) > 0 else 0,
            'pa_pg': home_stats['points_allowed'].mean() if len(home_stats) > 0 else 0,
            'off_epa': 0,
            'def_epa': 0,
            'pass_epa': 0,
            'rush_epa': 0,
            'def_pass_epa': 0,
            'def_rush_epa': 0,
            'turnovers': 0,
            'takeaways': 0,
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
    
    # Fetch sportsbook consensus from TheOddsAPI
    external_predictions = {}
    
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
                print(f"Fetched odds for {len(odds_data)} games")
                
                # Find this specific game
                for game_odds in odds_data:
                    away_team = game_odds.get('away_team', '')
                    home_team = game_odds.get('home_team', '')
                    
                    # Match team names (allow partial matches)
                    if away in away_team or home in home_team:
                        print(f"Found match: {away_team} @ {home_team}")
                        
                        # Calculate consensus from multiple bookmakers
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
                        
                        if spreads and totals:
                            avg_spread = sum(spreads) / len(spreads)
                            avg_total = sum(totals) / len(totals)
                            
                            # Estimate win probability from spread (spread * 3 ≈ win prob offset)
                            home_win_prob = 50 + (avg_spread * 3)
                            home_win_prob = max(10, min(90, home_win_prob))
                            
                            external_predictions['consensus'] = {
                                'away_win': round(100 - home_win_prob, 1),
                                'home_win': round(home_win_prob, 1),
                                'spread': f"{home} {avg_spread:+.1f}",
                                'total': round(avg_total, 1),
                                'source': f'{len(spreads)} sportsbooks'
                            }
                            print(f"Consensus: {external_predictions['consensus']}")
                        break
        else:
            print("No ODDS_API_KEY found")
    except Exception as e:
        print(f"Odds API error: {e}")
        import traceback
        traceback.print_exc()
        external_predictions['consensus'] = None
    
    return render_template('game_detail.html',
                         away=away,
                         home=home,
                         game=game_data,
                         away_season=away_season,
                         home_season=home_season,
                         away_recent=away_recent,
                         home_recent=home_recent,
                         external_predictions=external_predictions)

if __name__ == '__main__':
    app.run(debug=True, port=9876)

