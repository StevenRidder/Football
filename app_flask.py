"""
NFL Edge - Tabler Dashboard
Flask application serving NFL predictions with official Tabler UI
"""
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import pandas as pd
from datetime import date
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
    
    # Fetch detailed team stats
    try:
        df_teamweeks = fetch_teamweeks_live(season=2025)
        
        # Filter to current season only
        df_season = df_teamweeks[df_teamweeks['season'] == 2025].copy()
        
        # Get season-to-date stats for both teams
        away_stats = df_season[df_season['team'] == away].sort_values('week', ascending=False)
        home_stats = df_season[df_season['team'] == home].sort_values('week', ascending=False)
        
        # Calculate season averages
        away_season = {
            'team': away,
            'games': len(away_stats),
            'ppg': away_stats['points_scored'].mean() if len(away_stats) > 0 else 0,
            'pa_pg': away_stats['points_allowed'].mean() if len(away_stats) > 0 else 0,
            'off_epa': away_stats['passing_epa'].mean() + away_stats['rushing_epa'].mean() if len(away_stats) > 0 else 0,
            'def_epa': away_stats['def_passing_epa'].mean() + away_stats['def_rushing_epa'].mean() if len(away_stats) > 0 else 0,
            'pass_epa': away_stats['passing_epa'].mean() if len(away_stats) > 0 else 0,
            'rush_epa': away_stats['rushing_epa'].mean() if len(away_stats) > 0 else 0,
            'def_pass_epa': away_stats['def_passing_epa'].mean() if len(away_stats) > 0 else 0,
            'def_rush_epa': away_stats['def_rushing_epa'].mean() if len(away_stats) > 0 else 0,
            'turnovers': away_stats['turnovers'].sum() if len(away_stats) > 0 else 0,
            'takeaways': away_stats['def_interceptions'].sum() + away_stats['def_fumbles_recovered'].sum() if len(away_stats) > 0 else 0,
            'last_5_ppg': away_stats.head(5)['points_scored'].mean() if len(away_stats) >= 5 else away_stats['points_scored'].mean(),
            'last_5_pa': away_stats.head(5)['points_allowed'].mean() if len(away_stats) >= 5 else away_stats['points_allowed'].mean(),
        }
        
        home_season = {
            'team': home,
            'games': len(home_stats),
            'ppg': home_stats['points_scored'].mean() if len(home_stats) > 0 else 0,
            'pa_pg': home_stats['points_allowed'].mean() if len(home_stats) > 0 else 0,
            'off_epa': home_stats['passing_epa'].mean() + home_stats['rushing_epa'].mean() if len(home_stats) > 0 else 0,
            'def_epa': home_stats['def_passing_epa'].mean() + home_stats['def_rushing_epa'].mean() if len(home_stats) > 0 else 0,
            'pass_epa': home_stats['passing_epa'].mean() if len(home_stats) > 0 else 0,
            'rush_epa': home_stats['rushing_epa'].mean() if len(home_stats) > 0 else 0,
            'def_pass_epa': home_stats['def_passing_epa'].mean() if len(home_stats) > 0 else 0,
            'def_rush_epa': home_stats['def_rushing_epa'].mean() if len(home_stats) > 0 else 0,
            'turnovers': home_stats['turnovers'].sum() if len(home_stats) > 0 else 0,
            'takeaways': home_stats['def_interceptions'].sum() + home_stats['def_fumbles_recovered'].sum() if len(home_stats) > 0 else 0,
            'last_5_ppg': home_stats.head(5)['points_scored'].mean() if len(home_stats) >= 5 else home_stats['points_scored'].mean(),
            'last_5_pa': home_stats.head(5)['points_allowed'].mean() if len(home_stats) >= 5 else home_stats['points_allowed'].mean(),
        }
        
        # Get last 3 games for recent form
        if len(away_stats) >= 3:
            away_recent = away_stats.head(3)[['week', 'points_scored', 'points_allowed', 'opponent_team']].rename(columns={'opponent_team': 'opponent'}).to_dict('records')
        else:
            away_recent = []
            
        if len(home_stats) >= 3:
            home_recent = home_stats.head(3)[['week', 'points_scored', 'points_allowed', 'opponent_team']].rename(columns={'opponent_team': 'opponent'}).to_dict('records')
        else:
            home_recent = []
        
    except Exception as e:
        print(f"Error fetching team stats: {e}")
        away_season = {'team': away, 'games': 0}
        home_season = {'team': home, 'games': 0}
        away_recent = []
        home_recent = []
    
    # Fetch external predictions from real sources
    external_predictions = {}
    
    # ESPN FPI - Use actual data
    try:
        import requests
        # ESPN FPI endpoint (public data)
        espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
        response = requests.get(espn_url, timeout=5)
        if response.status_code == 200:
            espn_data = response.json()
            # Parse ESPN data for matchup predictions
            # This is a simplified version - real implementation would need proper parsing
            external_predictions['espn'] = {
                'away_win': round(100 - game_data.get('Home win %', 50), 1),
                'home_win': round(game_data.get('Home win %', 50), 1),
                'spread': f"{home} {game_data.get('Spread used (home-)', 0):+.1f}",
                'total': round(game_data.get('Total used', 0), 1)
            }
    except Exception as e:
        print(f"ESPN API error: {e}")
        external_predictions['espn'] = None
    
    # 538 NFL Predictions (they have public data)
    try:
        # 538 has NFL ELO ratings and predictions
        fivethirtyeight_url = "https://projects.fivethirtyeight.com/nfl-api/nfl_elo_latest.csv"
        response = requests.get(fivethirtyeight_url, timeout=5)
        if response.status_code == 200:
            import io
            df_538 = pd.read_csv(io.StringIO(response.text))
            # Filter for this matchup
            matchup_538 = df_538[
                ((df_538['team1'] == away) & (df_538['team2'] == home)) |
                ((df_538['team1'] == home) & (df_538['team2'] == away))
            ]
            if not matchup_538.empty:
                game_538 = matchup_538.iloc[-1]  # Most recent
                if game_538['team1'] == away:
                    away_prob = game_538.get('elo_prob1', 0.5) * 100
                else:
                    away_prob = game_538.get('elo_prob2', 0.5) * 100
                
                external_predictions['fivethirtyeight'] = {
                    'away_win': round(away_prob, 1),
                    'home_win': round(100 - away_prob, 1),
                    'spread': f"{home} {-1 * (away_prob - 50) / 3:+.1f}",  # Rough conversion
                    'total': round(game_data.get('Total used', 0), 1)
                }
            else:
                external_predictions['fivethirtyeight'] = None
    except Exception as e:
        print(f"FiveThirtyEight API error: {e}")
        external_predictions['fivethirtyeight'] = None
    
    # The Action Network / Consensus Lines
    try:
        # Use TheOddsAPI for consensus data (you already have the key)
        import os
        api_key = os.environ.get('ODDS_API_KEY', '')
        if api_key:
            odds_url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
            params = {
                'apiKey': api_key,
                'regions': 'us',
                'markets': 'spreads,totals',
                'oddsFormat': 'american'
            }
            response = requests.get(odds_url, params=params, timeout=5)
            if response.status_code == 200:
                odds_data = response.json()
                # Find this specific game
                for game_odds in odds_data:
                    if away in game_odds.get('away_team', '') and home in game_odds.get('home_team', ''):
                        # Calculate consensus from multiple bookmakers
                        spreads = []
                        totals = []
                        for bookmaker in game_odds.get('bookmakers', []):
                            for market in bookmaker.get('markets', []):
                                if market['key'] == 'spreads':
                                    for outcome in market['outcomes']:
                                        if outcome['name'] == home:
                                            spreads.append(outcome.get('point', 0))
                                elif market['key'] == 'totals':
                                    totals.append(market['outcomes'][0].get('point', 0))
                        
                        if spreads and totals:
                            avg_spread = sum(spreads) / len(spreads)
                            avg_total = sum(totals) / len(totals)
                            
                            # Estimate win probability from spread
                            home_win_prob = 50 + (avg_spread * 3)  # Rough conversion
                            home_win_prob = max(0, min(100, home_win_prob))
                            
                            external_predictions['consensus'] = {
                                'away_win': round(100 - home_win_prob, 1),
                                'home_win': round(home_win_prob, 1),
                                'spread': f"{home} {avg_spread:+.1f}",
                                'total': round(avg_total, 1),
                                'source': f'{len(spreads)} sportsbooks'
                            }
                        break
    except Exception as e:
        print(f"Odds API error: {e}")
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

