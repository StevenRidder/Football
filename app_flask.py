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
        df_season = df_teamweeks[
            (df_teamweeks['season'] == 2025) & 
            (df_teamweeks['season_type'] == 'REG')
        ].copy()
        
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
        away_recent = away_stats.head(3)[['week', 'points_scored', 'points_allowed', 'opponent']].to_dict('records') if len(away_stats) >= 3 else []
        home_recent = home_stats.head(3)[['week', 'points_scored', 'points_allowed', 'opponent']].to_dict('records') if len(home_stats) >= 3 else []
        
    except Exception as e:
        print(f"Error fetching team stats: {e}")
        away_season = {'team': away, 'games': 0}
        home_season = {'team': home, 'games': 0}
        away_recent = []
        home_recent = []
    
    # Third-party predictions (placeholder - you can integrate real APIs)
    external_predictions = {
        'opta': {
            'away_win': 54.5,  # Placeholder
            'home_win': 45.5,
            'spread': away + ' -3.0',
            'total': 44.5
        },
        'espn': {
            'away_win': 52.0,
            'home_win': 48.0,
            'spread': away + ' -2.5',
            'total': 45.0
        },
        'fpi': {
            'away_win': 56.0,
            'home_win': 44.0,
            'spread': away + ' -3.5',
            'total': 44.0
        }
    }
    
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

