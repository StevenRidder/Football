"""
NFL Edge - Tabler Dashboard
Flask application serving NFL predictions with official Tabler UI
"""
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import pandas as pd
from datetime import datetime
import json
import ast
from nfl_edge.accuracy_tracker import create_tracker
from nfl_edge.bets.betonline_client import (
    load_ledger, get_weekly_summary
)
from live_bet_tracker import LiveBetTracker
from edge_hunt.integrate_signals import enrich_predictions_with_signals

app = Flask(__name__)

def _parse_signals(signals_data):
    """Safely parse edge_hunt_signals from CSV."""
    # Check for None first
    if signals_data is None or signals_data == '':
        return []
    # Check for NaN (scalar check only)
    try:
        if pd.isna(signals_data):
            return []
    except (ValueError, TypeError):
        pass  # Not a scalar, continue
    # Check if already a list
    if isinstance(signals_data, list):
        return signals_data
    # Try to parse string
    if isinstance(signals_data, str):
        try:
            return ast.literal_eval(signals_data)
        except (ValueError, SyntaxError):
            return []
    return []

def generate_betting_recommendations(df_pred, current_week=None):
    """Generate betting recommendations tables from predictions DataFrame."""

    # Determine current week if not provided
    if current_week is None:
        if 'week' in df_pred.columns:
            current_week = df_pred.loc[~df_pred['is_completed'], 'week'].max()
        else:
            current_week = None

    current_week_games = df_pred[~df_pred['is_completed']].copy()
    if current_week is not None:
        current_week_games = current_week_games[
            current_week_games['week'] == current_week
        ]

    if current_week_games.empty:
        return None

    # 1. ATS (Against-the-Spread) Bets
    def format_team_from_pick(row, pick):
        if not pick:
            return None
        pick_upper = pick.upper()
        if pick_upper.startswith('HOME'):
            return row['home_team']
        if pick_upper.startswith('AWAY'):
            return row['away_team']
        return pick.replace(' ATS', '').strip()

    def format_line_for_team(row, line_value, team, is_closing_spread=False):
        """
        Convert spread line to betting team's perspective.
        
        closing_spread convention (special):
        - Positive (4.5) = home favored → home -4.5, away +4.5
        - Negative (-8.5) = away favored → home +8.5, away -8.5
        For away: if positive, use as-is; if negative, use as-is (already correct)
        
        our_spread convention (home_score - away_score):
        - Positive (4.5) = home wins by 4.5 → home -4.5, away +4.5
        - Negative (-6.5) = away wins by 6.5 → home +6.5, away -6.5
        For away: always negate
        """
        if team is None or pd.isna(line_value):
            return None

        # Determine if betting home or away
        is_home = (team.upper() == row['home_team'].upper())
        is_away = (team.upper() == row['away_team'].upper())

        if is_home:
            # Home team: convert to home betting line
            if is_closing_spread:
                # closing_spread: positive = home favored, so home line is negative
                value = -line_value if line_value > 0 else abs(line_value)
            else:
                # our_spread: positive = home wins, so home line is negative
                value = -line_value if line_value > 0 else abs(line_value)
        elif is_away:
            # Away team: convert to away betting line
            if is_closing_spread:
                # closing_spread: positive = away gets points (+), negative = away gives points (-)
                value = line_value  # Already in correct format!
            else:
                # our_spread = home_score - away_score
                # If negative: away wins → away gives points → away line negative (use as-is: -17.29 → BAL -17.3)
                # If positive: home wins → away gets points → away line positive (use positive: +7.3 → NE +7.3)
                # Key insight: our_spread sign already matches betting line sign from away perspective!
                value = line_value
        else:
            return None

        return f"{team} {value:+.1f}"

    ats_bets = []
    for _, row in current_week_games.iterrows():
        pick = row.get('spread_recommendation')
        if not pick or pick == 'Pass':
            continue

        conviction = row.get('spread_conviction') or 'LOW'
        edge_pct = row.get('spread_edge_pct', 0)
        pick_team = format_team_from_pick(row, pick)

        market_line_home = row.get('closing_spread')
        sim_line_home = row.get('our_spread')

        market_line_str = format_line_for_team(row, market_line_home, pick_team, is_closing_spread=True)
        sim_line_str = format_line_for_team(row, sim_line_home, pick_team, is_closing_spread=False)

        if market_line_str is None or sim_line_str is None:
            continue

        # Calculate edge using same perspective as display
        # Market line: closing_spread has special format
        if pick_team == row['home_team']:
            # Home betting: convert closing_spread to home line
            market_line_value = -market_line_home if market_line_home > 0 else abs(market_line_home)
            # Sim line: positive = home wins, so home line is negative
            sim_line_value = -sim_line_home if sim_line_home > 0 else abs(sim_line_home)
        else:
            # Away betting: closing_spread is already in away format
            market_line_value = market_line_home
            # Sim line: our_spread already has correct sign from away perspective
            sim_line_value = sim_line_home if pd.notna(sim_line_home) else None

        if market_line_value is None or sim_line_value is None:
            continue

        edge_value = abs(market_line_value - sim_line_value)

        if conviction == 'HIGH':
            confidence = min(100, 70 + edge_pct * 3)
        elif conviction == 'MEDIUM':
            confidence = min(70, 53 + edge_pct * 2)
        else:
            confidence = min(60, 50 + edge_pct)

        ats_bets.append({
            'game': f"{row['away_team']} @ {row['home_team']}",
            'market_line': market_line_str,
            'sim_line': sim_line_str,
            'edge': f"{edge_value:.1f}-pt edge",
            'pick': market_line_str,  # Use actual bet line instead of recommendation type
            'confidence': f"{confidence:.0f}%",
            'conviction': conviction,
            'edge_value': edge_value
        })

    # Sort by edge (descending)
    ats_bets = sorted(ats_bets, key=lambda x: x['edge_value'], reverse=True)[:11]

    # 2. Totals (Over/Under)
    total_bets = []
    for _, row in current_week_games.iterrows():
        market_total = row.get('closing_total', 0)
        sim_total = row.get('our_total', 0)
        edge = abs(market_total - sim_total)
        pick = row.get('total_recommendation', 'Pass')
        conviction = row.get('total_conviction', 'LOW')
        edge_pct = row.get('total_edge_pct', 0)

        if pick != 'Pass':
            # Calculate confidence
            if edge >= 10:
                confidence = 87
            elif edge >= 5:
                confidence = 70
            else:
                confidence = 60

            total_bets.append({
                'game': f"{row['away_team']} @ {row['home_team']}",
                'market_total': f"{market_total:.1f}",
                'sim_total': f"{sim_total:.1f}",
                'edge': f"{market_total - sim_total:+.1f} pts",
                'pick': f"{pick} {market_total:.1f}",  # Include total number, e.g., "Over 45.5"
                'confidence': f"{confidence}%",
                'edge_value': edge
            })

    # Sort by edge (descending)
    total_bets = sorted(total_bets, key=lambda x: x['edge_value'], reverse=True)[:7]

    # 3. Moneyline Value
    ml_picks = []
    for _, row in current_week_games.iterrows():
        home_score = row.get('our_home_score', 0)
        away_score = row.get('our_away_score', 0)
        edge = abs(home_score - away_score)

        if edge >= 10:  # Significant edge
            winner = row['home_team'] if home_score > away_score else row['away_team']
            ml_picks.append({
                'game': f"{row['away_team']} @ {row['home_team']}",
                'market_proj': 'N/A',
                'sim_proj': f"{int(away_score)}-{int(home_score)}",
                'edge': 'Huge' if edge >= 15 else 'Strong' if edge >= 12 else 'Solid',
                'pick': f"{winner} ML",
                'edge_value': edge
            })

    # Sort by edge (descending)
    ml_picks = sorted(ml_picks, key=lambda x: x['edge_value'], reverse=True)[:5]

    # 4. Final Recommendations - Top 3 from each category
    recommendations = {
        'ats': ats_bets[:4] if len(ats_bets) >= 4 else ats_bets,
        'totals': total_bets[:4] if len(total_bets) >= 4 else total_bets,
        'moneyline': ml_picks[:4] if len(ml_picks) >= 4 else ml_picks
    }

    return {
        'ats_bets': ats_bets,
        'total_bets': total_bets,
        'ml_picks': ml_picks,
        'recommendations': recommendations
    }

# Load predictions functions
def load_simulator_predictions(force_reload=False):
    """Load simulator predictions from backtest_all_games_conviction.py (formatted for frontend)."""
    simulator_file = Path("artifacts") / "simulator_predictions.csv"

    if simulator_file.exists():
        # Get file modification time for cache busting
        mtime = simulator_file.stat().st_mtime
        print(f"✅ Loading simulator predictions from {simulator_file} (modified: {mtime})")
        df = pd.read_csv(simulator_file)
        
        # Ensure spread_result is in the correct format (WIN/LOSS/None)
        if 'spread_result' in df.columns:
            # Convert numeric to string if needed
            if df['spread_result'].dtype in ['float64', 'int64']:
                df['spread_result'] = df['spread_result'].apply(
                    lambda x: 'WIN' if x == 1.0 else ('LOSS' if x == 0.0 else None) if pd.notna(x) else None
                )
        
        return df
    
    # If formatted file doesn't exist, try to load and format backtest files directly
    print("⚠️  simulator_predictions.csv not found, trying to load backtest files directly...")
    backtest_file = Path("simulation_engine/nflfastR_simulator/artifacts/backtest_all_games_conviction.csv")
    week9_file = Path("simulation_engine/nflfastR_simulator/artifacts/backtest_week9_predictions.csv")
    
    dfs = []
    if backtest_file.exists():
        print(f"   Loading weeks 1-8 from: {backtest_file}")
        df_backtest = pd.read_csv(backtest_file)
        dfs.append(df_backtest)
    
    if week9_file.exists():
        print(f"   Loading week 9 from: {week9_file}")
        df_week9 = pd.read_csv(week9_file)
        dfs.append(df_week9)
    
    if dfs:
        df_combined = pd.concat(dfs, ignore_index=True)
        # Convert spread_result to WIN/LOSS format
        if 'spread_result' in df_combined.columns:
            df_combined['spread_result'] = df_combined['spread_result'].apply(
                lambda x: 'WIN' if x == 1.0 else ('LOSS' if x == 0.0 else None) if pd.notna(x) else None
            )
        # Ensure is_completed exists
        if 'is_completed' not in df_combined.columns:
            df_combined['is_completed'] = df_combined.get('home_score', pd.Series()).notna() & df_combined.get('away_score', pd.Series()).notna()
        # Ensure spread_recommendation exists (convert from spread_bet if needed)
        if 'spread_recommendation' not in df_combined.columns and 'spread_bet' in df_combined.columns:
            def format_spread_bet(bet):
                if pd.isna(bet) or bet == 'Pass' or bet == '':
                    return 'Pass'
                if bet == 'HOME':
                    return 'Home ATS'
                if bet == 'AWAY':
                    return 'Away ATS'
                return str(bet)
            df_combined['spread_recommendation'] = df_combined['spread_bet'].apply(format_spread_bet)
        
        print(f"✅ Loaded {len(df_combined)} games from backtest files (weeks: {sorted(df_combined['week'].unique()) if 'week' in df_combined.columns else 'N/A'})")
        return df_combined
    
    return None

def load_latest_predictions():
    """Load pre-computed graded results from backend - combines all weeks for historical data"""
    import glob

    # Priority 1: Simulator predictions (from backtest_all_games_conviction.py)
    simulator_df = load_simulator_predictions()
    if simulator_df is not None:
        # Check if simulator file has all weeks, otherwise combine with individual week files
        if 'week' in simulator_df.columns:
            weeks_in_sim = set(simulator_df['week'].unique())
            # If simulator only has current week, combine with historical week files
            if len(weeks_in_sim) == 1:
                print(f"⚠️  Simulator file only has week {list(weeks_in_sim)[0]}, combining with historical weeks...")
                historical_df = load_all_historical_weeks()
                if historical_df is not None and len(historical_df) > 0:
                    # Combine, keeping simulator data for overlapping weeks
                    combined = pd.concat([historical_df, simulator_df], ignore_index=True)
                    # Remove duplicates (keep simulator version for overlapping weeks)
                    combined = combined.drop_duplicates(subset=['away_team', 'home_team', 'week', 'season'], keep='last')
                    print(f"✅ Combined {len(historical_df)} historical games with {len(simulator_df)} simulator games")
                    return combined
        return simulator_df

    # Priority 2: Pre-computed graded results (from grade_predictions_simple.py)
    graded_files = glob.glob('artifacts/graded_results/graded_bets_*.csv')
    if graded_files:
        latest_file = sorted(graded_files)[-1]
        print(f"✅ Loading pre-computed results from {latest_file}")
        df = pd.read_csv(latest_file)
        # Check if this has all weeks, otherwise combine
        if 'week' in df.columns and len(df['week'].unique()) == 1:
            historical_df = load_all_historical_weeks()
            if historical_df is not None and len(historical_df) > 0:
                combined = pd.concat([historical_df, df], ignore_index=True)
                combined = combined.drop_duplicates(subset=['away_team', 'home_team', 'week', 'season'], keep='last')
                print(f"✅ Combined {len(historical_df)} historical games with graded results")
                return combined
        return df

    # Priority 3: Load all historical week files and combine
    return load_all_historical_weeks()

def load_all_historical_weeks():
    """Load and combine all individual week prediction files"""
    import re
    
    artifacts = Path("artifacts")
    
    # Find all week-specific files (predictions_2025_weekN_*.csv)
    week_files = sorted(artifacts.glob("predictions_2025_week*.csv"))
    
    if not week_files:
        # Fall back to generic predictions files
        csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
        if not csvs:
            csvs = sorted(artifacts.glob("week_*_projections.csv"))
        if not csvs:
            return None
        # If only one file, return it
        if len(csvs) == 1:
            return pd.read_csv(csvs[0])
    
    # Combine all week files
    dfs = []
    for week_file in week_files:
        try:
            # Extract week number from filename (e.g., "predictions_2025_week1_*.csv" -> 1)
            week_match = re.search(r'week(\d+)', week_file.name)
            if not week_match:
                continue
            
            week_num = int(week_match.group(1))
            df = pd.read_csv(week_file)
            
            # Add week column if it doesn't exist
            if 'week' not in df.columns:
                df['week'] = week_num
            
            # Add season column if it doesn't exist
            if 'season' not in df.columns:
                df['season'] = 2025
            
            # Normalize team column names (some files use 'away'/'home', others use 'away_team'/'home_team')
            if 'away' in df.columns and 'away_team' not in df.columns:
                df['away_team'] = df['away']
            if 'home' in df.columns and 'home_team' not in df.columns:
                df['home_team'] = df['home']
            
            # Add is_completed column if missing (default to False for historical weeks)
            if 'is_completed' not in df.columns:
                # Check if game is completed by looking for actual scores
                if 'away_score' in df.columns and 'home_score' in df.columns:
                    df['is_completed'] = df['away_score'].notna() & df['home_score'].notna()
                else:
                    df['is_completed'] = False  # Historical weeks without scores are treated as incomplete
            
            # Ensure is_completed is boolean
            df['is_completed'] = df['is_completed'].astype(bool)
            
            dfs.append(df)
        except Exception as e:
            print(f"⚠️  Error loading {week_file}: {e}")
            continue
    
    if not dfs:
        return None
    
    # Combine all dataframes
    combined = pd.concat(dfs, ignore_index=True)
    
    # Remove duplicates (keep latest if same game appears in multiple files)
    if 'away_team' in combined.columns and 'home_team' in combined.columns and 'week' in combined.columns:
        combined = combined.drop_duplicates(subset=['away_team', 'home_team', 'week', 'season'], keep='last')
    elif 'away' in combined.columns and 'home' in combined.columns and 'week' in combined.columns:
        combined = combined.drop_duplicates(subset=['away', 'home', 'week', 'season'], keep='last')
    
    weeks_loaded = sorted(combined['week'].unique()) if 'week' in combined.columns else []
    print(f"✅ Loaded {len(combined)} games from {len(dfs)} week files (weeks: {weeks_loaded})")
    
    return combined

def load_latest_aii():
    """Load most recent AII data"""
    artifacts = Path("artifacts")
    csvs = sorted(artifacts.glob("aii_*.csv"))
    if not csvs:
        return None

    return pd.read_csv(csvs[-1])

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

    # Load team bias data for indicators
    team_win_rates = get_team_win_rates()

    # Generate betting recommendations from current predictions
    betting_recommendations = generate_betting_recommendations(df, current_week=current_week)

    return render_template('alpha_index_v3.html',
                          current_week=current_week,
                          all_weeks=all_weeks,
                          total_games=len(df),
                          team_win_rates=team_win_rates,
                          betting_recommendations=betting_recommendations)

def get_team_win_rates():
    """Get historical win rates for each team (for spread bets)"""
    from pathlib import Path
    import pandas as pd

    backtest_file = Path("simulation_engine/nflfastR_simulator/artifacts/backtest_all_games_conviction.csv")
    if not backtest_file.exists():
        return {}

    df = pd.read_csv(backtest_file)
    spread_bets = df[df['spread_bet'].notna() & (df['spread_bet'] != '')]

    team_stats = {}
    for idx, row in spread_bets.iterrows():
        home_team = row['home_team']
        away_team = row['away_team']
        spread_bet = str(row['spread_bet']).upper()
        spread_result = row['spread_result']

        # Determine which team we bet on
        if 'HOME' in spread_bet or home_team in spread_bet:
            bet_team = home_team
        elif 'AWAY' in spread_bet or away_team in spread_bet:
            bet_team = away_team
        else:
            continue

        if bet_team not in team_stats:
            team_stats[bet_team] = {'wins': 0, 'total': 0}

        team_stats[bet_team]['total'] += 1
        if spread_result == 1.0:
            team_stats[bet_team]['wins'] += 1

    # Calculate win rates
    team_win_rates = {}
    for team, stats in team_stats.items():
        if stats['total'] >= 3:  # Only show for teams with 3+ bets
            win_rate = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
            team_win_rates[team] = {
                'win_rate': round(win_rate, 1),
                'record': f"{stats['wins']}-{stats['total'] - stats['wins']}",
                'total': stats['total']
            }

    return team_win_rates

@app.route('/api/games')
def api_games():
    """API endpoint for game data with Edge Hunt signals"""
    df = load_latest_predictions()
    team_win_rates = get_team_win_rates()

    if df is None:
        print("❌ No predictions data found")
        return jsonify({'error': 'No data'}), 404

    print(f"✅ Loaded {len(df)} games for API")

    # Get current week
    try:
        from schedules import CURRENT_WEEK, CURRENT_SEASON
        current_week = CURRENT_WEEK
        current_season = CURRENT_SEASON
    except ImportError:
        current_week = 9
        current_season = 2025

    # Enrich with Edge Hunt signals (only if not already enriched)
    if 'adjusted_spread' not in df.columns or 'all_injuries' not in df.columns:
        try:
            df = enrich_predictions_with_signals(df, week=current_week, season=current_season)
        except Exception as e:
            print(f"⚠️ Could not enrich with Edge Hunt signals: {e}")
            # Add empty signal columns if enrichment fails
            df['has_edge_hunt_signal'] = False
            df['edge_hunt_signals'] = [[] for _ in range(len(df))]
    else:
        print("✅ Using pre-enriched predictions data")

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
            'confidence_pct': row.get('confidence_pct', 50),
            # Edge Hunt signals - parse Python repr string if needed
            'has_edge_hunt_signal': row.get('has_edge_hunt_signal', False),
            'edge_hunt_signals': _parse_signals(row.get('edge_hunt_signals', '[]')),
            # Injury data (ALL injuries for this game) - parse JSON string
            'all_injuries': json.loads(row.get('all_injuries', '[]')) if isinstance(row.get('all_injuries'), str) else row.get('all_injuries', []),
            'away_injury_impact': row.get('away_injury_impact', 0.0),
            'home_injury_impact': row.get('home_injury_impact', 0.0),
            # Market-implied and adjusted scores
            'market_implied_away': row.get('market_implied_away', 0),
            'market_implied_home': row.get('market_implied_home', 0),
            'adjusted_away': row.get('adjusted_away', 0),
            'adjusted_home': row.get('adjusted_home', 0),
            'adjusted_spread': row.get('adjusted_spread', 0),
            'adjusted_total': row.get('adjusted_total', 0)
        }
        games.append(game)

    return jsonify({
        'games': games,
        'team_win_rates': team_win_rates
    })

@app.route('/api/simulator-predictions')
def api_simulator_predictions():
    """API endpoint for simulator predictions with conviction badges."""
    df = load_simulator_predictions()
    team_win_rates = get_team_win_rates()

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
        'total': len(games),
        'team_win_rates': team_win_rates
    })

@app.route('/api/games/graded')
def api_games_graded():
    """API endpoint for games with actual results - SERVES PRE-COMPUTED BACKEND DATA."""
    df = load_latest_predictions()
    team_win_rates = get_team_win_rates()

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
        'total': len(games),
        'team_win_rates': team_win_rates
    })

@app.route('/api/best-bets')
def api_best_bets():
    """API endpoint for best betting opportunities (ADJUSTED vs MARKET)"""
    df = load_latest_predictions()

    if df is None:
        return jsonify({'error': 'No data'}), 404

    # Filter to only games with actual recommendations (not SKIP or NO PLAY)
    best = df[
        ((df.get('Rec_spread', 'SKIP') != 'SKIP') & (df.get('Rec_spread', 'NO PLAY') != 'NO PLAY')) |
        ((df.get('Rec_total', 'SKIP') != 'SKIP') & (df.get('Rec_total', 'NO PLAY') != 'NO PLAY'))
    ].copy()

    # Sort by edge (spread_edge_pts and total_edge_pts)
    if 'spread_edge_pts' in best.columns and 'total_edge_pts' in best.columns:
        best['max_edge'] = best[['spread_edge_pts', 'total_edge_pts']].abs().max(axis=1)
        best = best.sort_values('max_edge', ascending=False)

    bets = []
    for _, row in best.iterrows():
        # Determine which bet is better based on edge
        spread_edge = abs(row.get('spread_edge_pts', 0))
        total_edge = abs(row.get('total_edge_pts', 0))
        rec_spread = row.get('Rec_spread', 'SKIP')
        rec_total = row.get('Rec_total', 'SKIP')

        # Add spread bet if recommended
        if rec_spread not in ['SKIP', 'NO PLAY']:
            bets.append({
                'game': f"{row['away']} @ {row['home']}",
                'type': 'SPREAD',
                'recommendation': rec_spread,
                'edge_pts': spread_edge,
                'stake': 100.0,  # Fixed $100 per bet
            })

        # Add total bet if recommended
        if rec_total not in ['SKIP', 'NO PLAY']:
            bets.append({
                'game': f"{row['away']} @ {row['home']}",
                'type': 'TOTAL',
                'recommendation': rec_total,
                'edge_pts': total_edge,
                'stake': 100.0,  # Fixed $100 per bet
            })

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


@app.route('/betting-guide')
def betting_guide():
    """Betting guide page"""
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
    if week and 'week' in df_pred.columns:
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

        # Calculate basic rest days from schedule if not available
        if espn_data['away'].get('rest_days') is None:
            away_schedule = ESPNDataFetcher.fetch_team_schedule(away, 2025)
            if away_schedule and len(away_schedule) >= 2:
                # Use the last two games to estimate rest days
                try:
                    from datetime import datetime
                    sorted_games = sorted(away_schedule, key=lambda x: x['date'])
                    if len(sorted_games) >= 2:
                        last_game = datetime.fromisoformat(sorted_games[-2]['date'].replace('Z', '+00:00'))
                        current_game = datetime.fromisoformat(sorted_games[-1]['date'].replace('Z', '+00:00'))
                        espn_data['away']['rest_days'] = (current_game - last_game).days
                except:
                    espn_data['away']['rest_days'] = 7

        if espn_data['home'].get('rest_days') is None:
            home_schedule = ESPNDataFetcher.fetch_team_schedule(home, 2025)
            if home_schedule and len(home_schedule) >= 2:
                try:
                    from datetime import datetime
                    sorted_games = sorted(home_schedule, key=lambda x: x['date'])
                    if len(sorted_games) >= 2:
                        last_game = datetime.fromisoformat(sorted_games[-2]['date'].replace('Z', '+00:00'))
                        current_game = datetime.fromisoformat(sorted_games[-1]['date'].replace('Z', '+00:00'))
                        espn_data['home']['rest_days'] = (current_game - last_game).days
                except:
                    espn_data['home']['rest_days'] = 7

        # Set travel distance for home team to 0 (they don't travel)
        if espn_data['home'].get('travel_distance') is None:
            espn_data['home']['travel_distance'] = 0

        # Set a default for away team if not calculated
        if espn_data['away'].get('travel_distance') is None:
            espn_data['away']['travel_distance'] = 0  # Default to 0 if not calculated

        game_data['espn_data'] = espn_data
        print(f"✓ ESPN data loaded for {away} @ {home}", flush=True)
    except Exception as e:
        print(f"⚠️ Could not fetch ESPN data: {e}", flush=True)
        game_data['espn_data'] = {
            'away': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': [], 'rest_days': 7, 'travel_distance': 0},
            'home': {'team_info': {}, 'leaders': {}, 'splits': {'overall': {'games': 0}}, 'last_five': [], 'rest_days': 7, 'travel_distance': 0},
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

    # Get recent games from ESPN and transform to expected format
    away_last_five = espn.get('away', {}).get('last_five', [])
    home_last_five = espn.get('home', {}).get('last_five', [])

    # Transform historical game data to template format
    away_recent = []
    for game in away_last_five:
        away_recent.append({
            'week': game.get('week', 'N/A'),
            'opponent': game.get('opponent', 'Unknown'),
            'points_scored': game.get('team_score', 0),
            'points_allowed': game.get('opp_score', 0),
            'result': game.get('result', '-')
        })

    home_recent = []
    for game in home_last_five:
        home_recent.append({
            'week': game.get('week', 'N/A'),
            'opponent': game.get('opponent', 'Unknown'),
            'points_scored': game.get('team_score', 0),
            'points_allowed': game.get('opp_score', 0),
            'result': game.get('result', '-')
        })

    # Fetch nflverse data for stats - use RAW data with all columns
    try:
        import requests
        import io
        import pandas as pd
        nflverse_url = "https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_2025.csv"
        response = requests.get(nflverse_url, timeout=30)
        df_raw = pd.read_csv(io.BytesIO(response.content))

        # Get stats for both teams
        away_stats = df_raw[df_raw['team'] == away]
        home_stats = df_raw[df_raw['team'] == home]

        if not away_stats.empty:
            # Calculate points from TDs, FGs, etc. (nflverse doesn't have direct points column)
            td_cols = ['passing_tds', 'rushing_tds', 'receiving_tds', 'def_tds', 'special_teams_tds']
            away_tds = sum(away_stats.get(col, pd.Series([0])).sum() if col in away_stats.columns else 0 for col in td_cols)
            away_fgs = away_stats.get('fg_made', pd.Series([0])).sum() if 'fg_made' in away_stats.columns else 0
            away_pats = away_stats.get('pat_made', pd.Series([0])).sum() if 'pat_made' in away_stats.columns else 0
            away_safeties = away_stats.get('def_safeties', pd.Series([0])).sum() if 'def_safeties' in away_stats.columns else 0
            away_2pt = (away_stats.get('passing_2pt_conversions', pd.Series([0])).sum() if 'passing_2pt_conversions' in away_stats.columns else 0) + \
                      (away_stats.get('rushing_2pt_conversions', pd.Series([0])).sum() if 'rushing_2pt_conversions' in away_stats.columns else 0) + \
                      (away_stats.get('receiving_2pt_conversions', pd.Series([0])).sum() if 'receiving_2pt_conversions' in away_stats.columns else 0)
            # Calculate points per game from recent games
            away_recent_games = away_stats.head(5) if len(away_stats) >= 5 else away_stats
            away_points_list = []
            for _, row in away_recent_games.iterrows():
                row_tds = sum(row.get(col, 0) for col in td_cols if col in row.index)
                row_fgs = row.get('fg_made', 0) if 'fg_made' in row.index else 0
                row_pats = row.get('pat_made', 0) if 'pat_made' in row.index else 0
                row_safeties = row.get('def_safeties', 0) if 'def_safeties' in row.index else 0
                row_2pt = (row.get('passing_2pt_conversions', 0) if 'passing_2pt_conversions' in row.index else 0) + \
                         (row.get('rushing_2pt_conversions', 0) if 'rushing_2pt_conversions' in row.index else 0) + \
                         (row.get('receiving_2pt_conversions', 0) if 'receiving_2pt_conversions' in row.index else 0)
                pts = 6 * row_tds + 3 * row_fgs + 1 * row_pats + 2 * (row_safeties + row_2pt)
                away_points_list.append(pts)
            away_last_5_ppg = float(pd.Series(away_points_list).mean()) if away_points_list else 0

            # For points allowed, we need opponent data - use ESPN data instead
            away_last_5_pa = float(sum(game.get('opp_score', 0) for game in away_last_five[:5])) / min(len(away_last_five), 5) if len(away_last_five) > 0 else 0

            game_data['team_stats']['away'].update({
                'off_epa': float(away_stats['passing_epa'].mean() + away_stats['rushing_epa'].mean()),
                'def_epa': float(away_stats['def_epa_per_play'].mean()) if 'def_epa_per_play' in away_stats.columns else 0,
                'pass_epa': float(away_stats['passing_epa'].mean()),
                'rush_epa': float(away_stats['rushing_epa'].mean()),
                'passing_yards': float(away_stats['passing_yards'].mean()),
                'rushing_yards': float(away_stats['rushing_yards'].mean()),
                'turnovers': int(away_stats['passing_interceptions'].sum() + away_stats['sack_fumbles_lost'].sum() + away_stats['rushing_fumbles_lost'].sum()),
                'takeaways': int(away_stats['def_interceptions'].sum() + away_stats['fumble_recovery_opp'].sum()),
                'sacks_taken': int(away_stats['sacks_suffered'].sum()),
                'def_pass_epa': 0,  # Not in raw data
                'def_rush_epa': 0,  # Not in raw data
                'last_5_ppg': away_last_5_ppg,
                'last_5_pa': away_last_5_pa,
            })

        if not home_stats.empty:
            # Calculate points from TDs, FGs, etc. (nflverse doesn't have direct points column)
            td_cols = ['passing_tds', 'rushing_tds', 'receiving_tds', 'def_tds', 'special_teams_tds']
            home_recent_games = home_stats.head(5) if len(home_stats) >= 5 else home_stats
            home_points_list = []
            for _, row in home_recent_games.iterrows():
                row_tds = sum(row.get(col, 0) for col in td_cols if col in row.index)
                row_fgs = row.get('fg_made', 0) if 'fg_made' in row.index else 0
                row_pats = row.get('pat_made', 0) if 'pat_made' in row.index else 0
                row_safeties = row.get('def_safeties', 0) if 'def_safeties' in row.index else 0
                row_2pt = (row.get('passing_2pt_conversions', 0) if 'passing_2pt_conversions' in row.index else 0) + \
                         (row.get('rushing_2pt_conversions', 0) if 'rushing_2pt_conversions' in row.index else 0) + \
                         (row.get('receiving_2pt_conversions', 0) if 'receiving_2pt_conversions' in row.index else 0)
                pts = 6 * row_tds + 3 * row_fgs + 1 * row_pats + 2 * (row_safeties + row_2pt)
                home_points_list.append(pts)
            home_last_5_ppg = float(pd.Series(home_points_list).mean()) if home_points_list else 0

            # For points allowed, use ESPN data
            home_last_5_pa = float(sum(game.get('opp_score', 0) for game in home_last_five[:5])) / min(len(home_last_five), 5) if len(home_last_five) > 0 else 0

            game_data['team_stats']['home'].update({
                'off_epa': float(home_stats['passing_epa'].mean() + home_stats['rushing_epa'].mean()),
                'def_epa': float(home_stats['def_epa_per_play'].mean()) if 'def_epa_per_play' in home_stats.columns else 0,
                'pass_epa': float(home_stats['passing_epa'].mean()),
                'rush_epa': float(home_stats['rushing_epa'].mean()),
                'passing_yards': float(home_stats['passing_yards'].mean()),
                'rushing_yards': float(home_stats['rushing_yards'].mean()),
                'turnovers': int(home_stats['passing_interceptions'].sum() + home_stats['sack_fumbles_lost'].sum() + home_stats['rushing_fumbles_lost'].sum()),
                'takeaways': int(home_stats['def_interceptions'].sum() + home_stats['fumble_recovery_opp'].sum()),
                'sacks_taken': int(home_stats['sacks_suffered'].sum()),
                'def_pass_epa': 0,  # Not in raw data
                'def_rush_epa': 0,  # Not in raw data
                'last_5_ppg': home_last_5_ppg,
                'last_5_pa': home_last_5_pa,
            })
        print(f"✅ Loaded nflverse stats for {away} and {home}")
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch nflverse data: {e}")

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
                        'is_home': is_home,
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
                        'is_home': is_home,
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

    # Check if trace exists for this game
    trace_exists = False
    trace_path = None
    if week and 'week' in df_pred.columns:
        from pathlib import Path
        season = 2025  # Default season
        trace_dir = Path("artifacts/traces")
        trace_filename = f"{away}_{home}_{week}_{season}.jsonl"
        trace_path_check = trace_dir / trace_filename
        trace_exists = trace_path_check.exists()
        if trace_exists:
            trace_path = str(trace_path_check)

    # Load TeamProfile data for PFF/nflfastR metrics display
    away_profile_dict = None
    home_profile_dict = None
    try:
        from pathlib import Path
        import sys
        sys.path.insert(0, str(Path(__file__).parent / "simulation_engine" / "nflfastR_simulator"))
        from simulator.team_profile import TeamProfile

        season = 2025
        game_week = week if week else game_data.get('week', 10)
        # FIXED: TeamProfile expects data_dir to point to nflfastR subdirectory
        data_dir = Path(__file__).parent / "simulation_engine" / "nflfastR_simulator" / "data" / "nflfastR"

        try:
            away_profile = TeamProfile(away, season, game_week, data_dir, debug=False)
            away_profile_dict = away_profile.as_dict_for_audit()
            print(f"✅ Loaded TeamProfile for {away}")
        except Exception as e:
            print(f"⚠️  Could not load TeamProfile for {away}: {e}")
            import traceback
            traceback.print_exc()
            # Create minimal dict with available data from game_data
            away_profile_dict = {
                'team': away,
                'off_epa': game_data.get('team_stats', {}).get('away', {}).get('off_epa', 0.0),
                'def_epa': game_data.get('team_stats', {}).get('away', {}).get('def_epa', 0.0),
                'qb_name': 'N/A',
                'qb_completion_pct': 0.65,
                'qb_ypa': 7.0,
                'qb_any_a': 6.5,
                'yards_per_pass': 7.0,
                'yards_per_run': 4.5,
                'pace': 60.0,
                'pass_rate': 0.6,
                'ol_grade': 50.0,
                'dl_grade': 50.0,
                'ol_run_grade': 50.0,
                'dl_run_grade': 50.0,
                'passing_grade': 50.0,
                'coverage_grade': 50.0,
            }

        try:
            home_profile = TeamProfile(home, season, game_week, data_dir, debug=False)
            home_profile_dict = home_profile.as_dict_for_audit()
            print(f"✅ Loaded TeamProfile for {home}")
        except Exception as e:
            print(f"⚠️  Could not load TeamProfile for {home}: {e}")
            import traceback
            traceback.print_exc()
            # Create minimal dict with available data from game_data
            home_profile_dict = {
                'team': home,
                'off_epa': game_data.get('team_stats', {}).get('home', {}).get('off_epa', 0.0),
                'def_epa': game_data.get('team_stats', {}).get('home', {}).get('def_epa', 0.0),
                'qb_name': 'N/A',
                'qb_completion_pct': 0.65,
                'qb_ypa': 7.0,
                'qb_any_a': 6.5,
                'yards_per_pass': 7.0,
                'yards_per_run': 4.5,
                'pace': 60.0,
                'pass_rate': 0.6,
                'ol_grade': 50.0,
                'dl_grade': 50.0,
                'ol_run_grade': 50.0,
                'dl_run_grade': 50.0,
                'passing_grade': 50.0,
                'coverage_grade': 50.0,
            }

        # Load PFF matchup data (power rankings, QB names) - AFTER both profiles are loaded
        try:
            matchup_file = Path(__file__).parent / "simulation_engine" / "nflfastR_simulator" / "data" / f"pff_matchup_week{game_week}.csv"
            if matchup_file.exists():
                import pandas as pd
                matchup_df = pd.read_csv(matchup_file)
                game_matchup = matchup_df[
                    ((matchup_df['away_team'] == away) & (matchup_df['home_team'] == home)) |
                    ((matchup_df['away_team'] == home) & (matchup_df['home_team'] == away))
                ]

                if len(game_matchup) > 0:
                    row = game_matchup.iloc[0]
                    # Ensure profile dicts exist before merging
                    if away_profile_dict is None:
                        away_profile_dict = {}
                    if home_profile_dict is None:
                        home_profile_dict = {}

                    # Merge PFF data into profile dicts
                    if str(row['away_team']) == away:
                        away_profile_dict['power_rank_overall'] = int(row.get('away_power_rank_overall')) if pd.notna(row.get('away_power_rank_overall')) else None
                        away_profile_dict['power_rank_offense'] = int(row.get('away_power_rank_offense')) if pd.notna(row.get('away_power_rank_offense')) else None
                        away_profile_dict['power_rank_defense'] = int(row.get('away_power_rank_defense')) if pd.notna(row.get('away_power_rank_defense')) else None
                        away_profile_dict['qb_name'] = row.get('away_qb_name') or away_profile_dict.get('qb_name')

                        home_profile_dict['power_rank_overall'] = int(row.get('home_power_rank_overall')) if pd.notna(row.get('home_power_rank_overall')) else None
                        home_profile_dict['power_rank_offense'] = int(row.get('home_power_rank_offense')) if pd.notna(row.get('home_power_rank_offense')) else None
                        home_profile_dict['power_rank_defense'] = int(row.get('home_power_rank_defense')) if pd.notna(row.get('home_power_rank_defense')) else None
                        home_profile_dict['qb_name'] = row.get('home_qb_name') or home_profile_dict.get('qb_name')
                    else:
                        # Inverted
                        away_profile_dict['power_rank_overall'] = int(row.get('home_power_rank_overall')) if pd.notna(row.get('home_power_rank_overall')) else None
                        away_profile_dict['power_rank_offense'] = int(row.get('home_power_rank_offense')) if pd.notna(row.get('home_power_rank_offense')) else None
                        away_profile_dict['power_rank_defense'] = int(row.get('home_power_rank_defense')) if pd.notna(row.get('home_power_rank_defense')) else None
                        away_profile_dict['qb_name'] = row.get('home_qb_name') or away_profile_dict.get('qb_name')

                        home_profile_dict['power_rank_overall'] = int(row.get('away_power_rank_overall')) if pd.notna(row.get('away_power_rank_overall')) else None
                        home_profile_dict['power_rank_offense'] = int(row.get('away_power_rank_offense')) if pd.notna(row.get('away_power_rank_offense')) else None
                        home_profile_dict['power_rank_defense'] = int(row.get('away_power_rank_defense')) if pd.notna(row.get('away_power_rank_defense')) else None
                        home_profile_dict['qb_name'] = row.get('away_qb_name') or home_profile_dict.get('qb_name')

                    print(f"✅ Merged PFF matchup data for {away} @ {home}")
        except Exception as e:
            print(f"⚠️  Could not load PFF matchup data: {e}")

        # FIXED: Update team_stats with actual data from TeamProfile
        if away_profile_dict and home_profile_dict:
            try:
                # Calculate approximate yards per game from yards per play * plays per game
                # Average NFL team has ~65 plays per game
                avg_plays_per_game = 65.0

                # Away team stats - use actual TeamProfile fields
                away_ypp = away_profile_dict.get('off_yards_per_play', 0) or 0
                away_ypa_actual = away_profile_dict.get('off_yards_per_pass_attempt', 0) or away_profile_dict.get('qb_ypa', 7.0) or 7.0
                away_pass_rate = away_profile_dict.get('pass_rate', 0.6) or 0.6

                # Estimate YPR from YPP: YPP = (pass_rate * YPA) + ((1-pass_rate) * YPR)
                if away_ypp > 0 and away_pass_rate > 0 and away_pass_rate < 1:
                    away_ypr = (away_ypp - away_pass_rate * away_ypa_actual) / (1 - away_pass_rate)
                else:
                    away_ypr = 4.5  # League average

                # Estimate passing/rushing yards per game
                away_pass_plays = avg_plays_per_game * away_pass_rate
                away_rush_plays = avg_plays_per_game * (1 - away_pass_rate)
                away_pass_yards_per_game = away_pass_plays * away_ypa_actual
                away_rush_yards_per_game = away_rush_plays * away_ypr

                # Only update EPA and yards, preserve turnovers/sacks/takeaways from nflverse
                game_data['team_stats']['away'].update({
                    'off_epa': float(away_profile_dict.get('off_epa', 0) or 0),
                    'def_epa': float(away_profile_dict.get('def_epa', 0) or 0),
                    'pass_epa': float(away_profile_dict.get('off_epa', 0) or 0) * 0.7,  # Approximate: 70% of EPA is passing
                    'rush_epa': float(away_profile_dict.get('off_epa', 0) or 0) * 0.3,  # Approximate: 30% is rushing
                    'def_pass_epa': float(away_profile_dict.get('def_epa', 0) or 0) * 0.7,  # Approximate
                    'def_rush_epa': float(away_profile_dict.get('def_epa', 0) or 0) * 0.3,  # Approximate
                    'passing_yards': float(away_pass_yards_per_game),
                    'rushing_yards': float(away_rush_yards_per_game),
                    # Note: turnovers, sacks_taken, takeaways, last_5_ppg, last_5_pa are preserved from nflverse data above
                })

                # Home team stats
                home_ypp = home_profile_dict.get('off_yards_per_play', 0) or 0
                home_ypa_actual = home_profile_dict.get('off_yards_per_pass_attempt', 0) or home_profile_dict.get('qb_ypa', 7.0) or 7.0
                home_pass_rate = home_profile_dict.get('pass_rate', 0.6) or 0.6

                if home_ypp > 0 and home_pass_rate > 0 and home_pass_rate < 1:
                    home_ypr = (home_ypp - home_pass_rate * home_ypa_actual) / (1 - home_pass_rate)
                else:
                    home_ypr = 4.5

                home_pass_plays = avg_plays_per_game * home_pass_rate
                home_rush_plays = avg_plays_per_game * (1 - home_pass_rate)
                home_pass_yards_per_game = home_pass_plays * home_ypa_actual
                home_rush_yards_per_game = home_rush_plays * home_ypr

                # Only update EPA and yards, preserve turnovers/sacks/takeaways from nflverse
                game_data['team_stats']['home'].update({
                    'off_epa': float(home_profile_dict.get('off_epa', 0) or 0),
                    'def_epa': float(home_profile_dict.get('def_epa', 0) or 0),
                    'pass_epa': float(home_profile_dict.get('off_epa', 0) or 0) * 0.7,
                    'rush_epa': float(home_profile_dict.get('off_epa', 0) or 0) * 0.3,
                    'def_pass_epa': float(home_profile_dict.get('def_epa', 0) or 0) * 0.7,
                    'def_rush_epa': float(home_profile_dict.get('def_epa', 0) or 0) * 0.3,
                    'passing_yards': float(home_pass_yards_per_game),
                    'rushing_yards': float(home_rush_yards_per_game),
                    # Note: turnovers, sacks_taken, takeaways, last_5_ppg, last_5_pa are preserved from nflverse data above
                })
            except Exception as e:
                print(f"⚠️  Could not update team_stats from TeamProfile: {e}")

    except Exception as e:
        print(f"⚠️  Could not load TeamProfile data: {e}")
        # Create minimal dicts as fallback
        away_profile_dict = {
            'team': away,
            'off_epa': 0.0, 'def_epa': 0.0,
            'qb_name': 'N/A', 'qb_completion_pct': 0.65, 'qb_ypa': 7.0, 'qb_any_a': 6.5,
            'yards_per_pass': 7.0, 'yards_per_run': 4.5, 'pace': 60.0, 'pass_rate': 0.6,
            'ol_grade': 50.0, 'dl_grade': 50.0, 'ol_run_grade': 50.0, 'dl_run_grade': 50.0,
            'passing_grade': 50.0, 'coverage_grade': 50.0,
        }
        home_profile_dict = {
            'team': home,
            'off_epa': 0.0, 'def_epa': 0.0,
            'qb_name': 'N/A', 'qb_completion_pct': 0.65, 'qb_ypa': 7.0, 'qb_any_a': 6.5,
            'yards_per_pass': 7.0, 'yards_per_run': 4.5, 'pace': 60.0, 'pass_rate': 0.6,
            'ol_grade': 50.0, 'dl_grade': 50.0, 'ol_run_grade': 50.0, 'dl_run_grade': 50.0,
            'passing_grade': 50.0, 'coverage_grade': 50.0,
        }

    # Load injury data for impact players
    injury_data = {}
    try:
        from pathlib import Path
        injury_file = Path(__file__).parent / "simulation_engine" / "nflfastR_simulator" / "data" / "nflfastR" / "weekly_injuries.csv"
        if injury_file.exists():
            import pandas as pd
            season = 2025
            game_week = week if week else game_data.get('week', 10)
            df_inj = pd.read_csv(injury_file)
            week_inj = df_inj[(df_inj['season'] == season) & (df_inj['week'] == game_week)]

            # Get injury details for both teams
            away_inj = week_inj[week_inj['team'] == away].to_dict('records')
            home_inj = week_inj[week_inj['team'] == home].to_dict('records')

            injury_data = {
                'away': away_inj[0] if away_inj else None,
                'home': home_inj[0] if home_inj else None
            }
    except Exception as e:
        print(f"⚠️  Could not load injury data: {e}")
        injury_data = {'away': None, 'home': None}

    # Ensure profile dicts are not None
    if away_profile_dict is None:
        away_profile_dict = {}
    if home_profile_dict is None:
        home_profile_dict = {}

    return render_template('game_detail.html',
                         away=away,
                         home=home,
                         week=week if week else game_data.get('week'),
                         game=game_data,
                         away_season=game_data['team_stats']['away'],
                         home_season=game_data['team_stats']['home'],
                         trace_exists=trace_exists,
                         trace_path=trace_path,
                         away_recent=away_recent,
                         home_recent=home_recent,
                         external_predictions=external_predictions,
                         away_profile=away_profile_dict,
                         home_profile=home_profile_dict,
                         injury_data=injury_data)

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

@app.route('/model-performance')
def model_performance():
    """Model Performance by Conviction Level - Backend Analysis"""
    from pathlib import Path
    import pandas as pd

    # Load backtest results
    backtest_file = Path("simulation_engine/nflfastR_simulator/artifacts/backtest_all_games_conviction.csv")

    if not backtest_file.exists():
        return render_template('error.html',
                             message="Backtest data not found. Run backtest_all_games_conviction.py first.")

    df = pd.read_csv(backtest_file)

    # Calculate stats by conviction level (backend logic)
    def calc_spread_stats(bets_df):
        if len(bets_df) == 0:
            return {'count': 0, 'wins': 0, 'losses': 0, 'pushes': 0,
                    'win_rate': 0, 'roi': 0, 'avg_edge': 0}

        # Count wins/losses from spread_result column
        wins = int((bets_df['spread_result'] == 1.0).sum())
        losses = int((bets_df['spread_result'] == 0.0).sum())
        pushes = int(len(bets_df) - wins - losses)

        win_rate = (wins / len(bets_df) * 100) if len(bets_df) > 0 else 0

        # Assuming -110 odds: win +0.91, loss -1.00
        profit = (wins * 0.91) - losses
        roi = (profit / len(bets_df) * 100) if len(bets_df) > 0 else 0

        # Get average edge from spread_edge column
        avg_edge = (bets_df['spread_edge'].mean() * 100) if 'spread_edge' in bets_df.columns else 0

        return {
            'count': int(len(bets_df)),
            'wins': wins,
            'losses': losses,
            'pushes': pushes,
            'win_rate': round(win_rate, 1),
            'roi': round(roi, 1),
            'avg_edge': round(avg_edge, 1)
        }

    def calc_total_stats(bets_df):
        if len(bets_df) == 0:
            return {'count': 0, 'wins': 0, 'losses': 0, 'pushes': 0,
                    'win_rate': 0, 'roi': 0, 'avg_edge': 0}

        # Count wins/losses from total_result column
        wins = int((bets_df['total_result'] == 1.0).sum())
        losses = int((bets_df['total_result'] == 0.0).sum())
        pushes = int(len(bets_df) - wins - losses)

        win_rate = (wins / len(bets_df) * 100) if len(bets_df) > 0 else 0

        # Assuming -110 odds: win +0.91, loss -1.00
        profit = (wins * 0.91) - losses
        roi = (profit / len(bets_df) * 100) if len(bets_df) > 0 else 0

        # Get average edge from total_edge column
        avg_edge = (bets_df['total_edge'].mean() * 100) if 'total_edge' in bets_df.columns else 0

        return {
            'count': int(len(bets_df)),
            'wins': wins,
            'losses': losses,
            'pushes': pushes,
            'win_rate': round(win_rate, 1),
            'roi': round(roi, 1),
            'avg_edge': round(avg_edge, 1)
        }

    # Spread bets by conviction
    spread_bets = df[df['spread_bet'].notna() & (df['spread_bet'] != '')]
    spread_high = spread_bets[spread_bets['spread_conviction'] == 'HIGH']
    spread_medium = spread_bets[spread_bets['spread_conviction'] == 'MEDIUM']
    spread_low = spread_bets[spread_bets['spread_conviction'] == 'LOW']

    # Total bets by conviction
    total_bets = df[df['total_bet'].notna() & (df['total_bet'] != '')]
    total_high = total_bets[total_bets['total_conviction'] == 'HIGH']
    total_medium = total_bets[total_bets['total_conviction'] == 'MEDIUM']
    total_low = total_bets[total_bets['total_conviction'] == 'LOW']

    # Calculate all stats on backend
    stats = {
        'total_games': len(df),
        'weeks': sorted(df['week'].unique().tolist()),
        'spread': {
            'high': calc_spread_stats(spread_high),
            'medium': calc_spread_stats(spread_medium),
            'low': calc_spread_stats(spread_low),
            'all': calc_spread_stats(spread_bets)
        },
        'total': {
            'high': calc_total_stats(total_high),
            'medium': calc_total_stats(total_medium),
            'low': calc_total_stats(total_low),
            'all': calc_total_stats(total_bets)
        }
    }

    return render_template('model_performance.html', stats=stats)

@app.route('/model-performance/spread/<conviction>')
def model_performance_spread_detail(conviction):
    """Detailed breakdown of spread bets by conviction level"""
    from pathlib import Path
    import pandas as pd

    conviction = conviction.upper()
    if conviction not in ['HIGH', 'MEDIUM', 'LOW']:
        return "Invalid conviction level", 400

    # Load backtest results
    backtest_file = Path("simulation_engine/nflfastR_simulator/artifacts/backtest_all_games_conviction.csv")
    if not backtest_file.exists():
        return render_template('error.html',
                             message="Backtest data not found.")

    df = pd.read_csv(backtest_file)

    # Filter spread bets by conviction
    spread_bets = df[
        (df['spread_bet'].notna()) &
        (df['spread_bet'] != '') &
        (df['spread_conviction'] == conviction)
    ].copy()

    # Prepare bet details for display
    bets = []
    for idx, row in spread_bets.iterrows():
        bets.append({
            'week': int(row['week']),
            'away_team': row['away_team'],
            'home_team': row['home_team'],
            'market_spread': row['spread_line'],
            'our_spread': round(row['spread_mean'], 1),
            'bet': row['spread_bet'],
            'edge': round(row['spread_edge'] * 100, 1),
            'result': 'WIN' if row['spread_result'] == 1.0 else 'LOSS' if row['spread_result'] == 0.0 else 'PUSH',
            'actual_score': f"{int(row['actual_away_score'])}-{int(row['actual_home_score'])}" if pd.notna(row['actual_home_score']) else '-'
        })

    return render_template('model_performance_detail.html',
                         bet_type='Spread',
                         conviction=conviction,
                         bets=bets,
                         total=len(bets),
                         wins=len([b for b in bets if b['result'] == 'WIN']),
                         losses=len([b for b in bets if b['result'] == 'LOSS']))

@app.route('/model-performance/total/<conviction>')
def model_performance_total_detail(conviction):
    """Detailed breakdown of total bets by conviction level"""
    from pathlib import Path
    import pandas as pd

    conviction = conviction.upper()
    if conviction not in ['HIGH', 'MEDIUM', 'LOW']:
        return "Invalid conviction level", 400

    # Load backtest results
    backtest_file = Path("simulation_engine/nflfastR_simulator/artifacts/backtest_all_games_conviction.csv")
    if not backtest_file.exists():
        return render_template('error.html',
                             message="Backtest data not found.")

    df = pd.read_csv(backtest_file)

    # Filter total bets by conviction
    total_bets = df[
        (df['total_bet'].notna()) &
        (df['total_bet'] != '') &
        (df['total_conviction'] == conviction)
    ].copy()

    # Prepare bet details for display
    bets = []
    for idx, row in total_bets.iterrows():
        bets.append({
            'week': int(row['week']),
            'away_team': row['away_team'],
            'home_team': row['home_team'],
            'market_total': row['total_line'],
            'our_total': round(row['total_mean'], 1),
            'bet': row['total_bet'],
            'edge': round(row['total_edge'] * 100, 1),
            'result': 'WIN' if row['total_result'] == 1.0 else 'LOSS' if row['total_result'] == 0.0 else 'PUSH',
            'actual_total': int(row['actual_away_score'] + row['actual_home_score']) if pd.notna(row['actual_home_score']) else '-'
        })

    return render_template('model_performance_detail.html',
                         bet_type='Total',
                         conviction=conviction,
                         bets=bets,
                         total=len(bets),
                         wins=len([b for b in bets if b['result'] == 'WIN']),
                         losses=len([b for b in bets if b['result'] == 'LOSS']))

@app.route('/model-performance/team-analysis')
def model_performance_team_analysis():
    """Team-by-team performance analysis - identify biases"""
    from pathlib import Path
    import pandas as pd

    # Load backtest results
    backtest_file = Path("simulation_engine/nflfastR_simulator/artifacts/backtest_all_games_conviction.csv")
    if not backtest_file.exists():
        return render_template('error.html',
                             message="Backtest data not found.")

    df = pd.read_csv(backtest_file)

    # Analyze spread bets by team
    spread_bets = df[df['spread_bet'].notna() & (df['spread_bet'] != '')]
    team_spread_stats = {}

    for idx, row in spread_bets.iterrows():
        home_team = row['home_team']
        away_team = row['away_team']
        spread_bet = str(row['spread_bet']).upper()
        spread_result = row['spread_result']
        conviction = row['spread_conviction']

        # Determine which team we bet on
        if 'HOME' in spread_bet or home_team in spread_bet:
            bet_team = home_team
        elif 'AWAY' in spread_bet or away_team in spread_bet:
            bet_team = away_team
        else:
            continue

        # Initialize team stats if not exists
        if bet_team not in team_spread_stats:
            team_spread_stats[bet_team] = {
                'team': bet_team,
                'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0,
                'high_bets': 0, 'high_wins': 0,
                'med_bets': 0, 'med_wins': 0,
                'low_bets': 0, 'low_wins': 0
            }

        team_spread_stats[bet_team]['bets'] += 1
        if spread_result == 1.0:
            team_spread_stats[bet_team]['wins'] += 1
        elif spread_result == 0.0:
            team_spread_stats[bet_team]['losses'] += 1
        else:
            team_spread_stats[bet_team]['pushes'] += 1

        # Track by conviction
        if conviction == 'HIGH':
            team_spread_stats[bet_team]['high_bets'] += 1
            if spread_result == 1.0:
                team_spread_stats[bet_team]['high_wins'] += 1
        elif conviction == 'MEDIUM':
            team_spread_stats[bet_team]['med_bets'] += 1
            if spread_result == 1.0:
                team_spread_stats[bet_team]['med_wins'] += 1
        elif conviction == 'LOW':
            team_spread_stats[bet_team]['low_bets'] += 1
            if spread_result == 1.0:
                team_spread_stats[bet_team]['low_wins'] += 1

    # Analyze total bets by team (both teams involved in the game)
    total_bets = df[df['total_bet'].notna() & (df['total_bet'] != '')]
    team_total_stats = {}

    for idx, row in total_bets.iterrows():
        home_team = row['home_team']
        away_team = row['away_team']
        total_result = row['total_result']
        conviction = row['total_conviction']

        # Count both teams in the game
        for team in [home_team, away_team]:
            if team not in team_total_stats:
                team_total_stats[team] = {
                    'team': team,
                    'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0,
                    'high_bets': 0, 'high_wins': 0,
                    'med_bets': 0, 'med_wins': 0,
                    'low_bets': 0, 'low_wins': 0
                }

            team_total_stats[team]['bets'] += 1
            if total_result == 1.0:
                team_total_stats[team]['wins'] += 1
            elif total_result == 0.0:
                team_total_stats[team]['losses'] += 1
            else:
                team_total_stats[team]['pushes'] += 1

            # Track by conviction
            if conviction == 'HIGH':
                team_total_stats[team]['high_bets'] += 1
                if total_result == 1.0:
                    team_total_stats[team]['high_wins'] += 1
            elif conviction == 'MEDIUM':
                team_total_stats[team]['med_bets'] += 1
                if total_result == 1.0:
                    team_total_stats[team]['med_wins'] += 1
            elif conviction == 'LOW':
                team_total_stats[team]['low_bets'] += 1
                if total_result == 1.0:
                    team_total_stats[team]['low_wins'] += 1

    # Calculate win rates and prepare for display
    spread_teams = []
    for team, stats in team_spread_stats.items():
        if stats['bets'] >= 3:  # Only teams with 3+ bets
            win_rate = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
            high_wr = (stats['high_wins'] / stats['high_bets'] * 100) if stats['high_bets'] > 0 else None
            med_wr = (stats['med_wins'] / stats['med_bets'] * 100) if stats['med_bets'] > 0 else None
            low_wr = (stats['low_wins'] / stats['low_bets'] * 100) if stats['low_bets'] > 0 else None

            spread_teams.append({
                'team': team,
                'bets': stats['bets'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'pushes': stats['pushes'],
                'win_rate': round(win_rate, 1),
                'high_wr': round(high_wr, 1) if high_wr is not None else None,
                'med_wr': round(med_wr, 1) if med_wr is not None else None,
                'low_wr': round(low_wr, 1) if low_wr is not None else None
            })

    total_teams = []
    for team, stats in team_total_stats.items():
        if stats['bets'] >= 3:  # Only teams with 3+ bets
            win_rate = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
            high_wr = (stats['high_wins'] / stats['high_bets'] * 100) if stats['high_bets'] > 0 else None
            med_wr = (stats['med_wins'] / stats['med_bets'] * 100) if stats['med_bets'] > 0 else None
            low_wr = (stats['low_wins'] / stats['low_bets'] * 100) if stats['low_bets'] > 0 else None

            total_teams.append({
                'team': team,
                'bets': stats['bets'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'pushes': stats['pushes'],
                'win_rate': round(win_rate, 1),
                'high_wr': round(high_wr, 1) if high_wr is not None else None,
                'med_wr': round(med_wr, 1) if med_wr is not None else None,
                'low_wr': round(low_wr, 1) if low_wr is not None else None
            })

    return render_template('team_bias_analysis.html',
                         spread_teams=spread_teams,
                         total_teams=total_teams)

@app.route('/performance')
def performance():
    """Betting Performance Analytics - Database Version"""
    from nfl_edge.bets.db import BettingDB

    db = BettingDB()

    try:
        # Get overall stats
        summary = db.get_performance_summary()

        stats = {
            'total_profit': float(summary['total_profit']) if summary['total_profit'] is not None else 0.0,
            'total_wagered': float(summary['total_wagered']) if summary['total_wagered'] is not None else 0.0,
            'roi': float(summary['roi']) if summary['roi'] is not None else 0.0,
            'win_rate': float(summary['win_rate']) if summary['win_rate'] is not None else 0.0,
            'total_bets': int(summary['total_bets']) if summary['total_bets'] is not None else 0,
            'won_count': int(summary['won_count']) if summary['won_count'] is not None else 0,
            'lost_count': int(summary['lost_count']) if summary['lost_count'] is not None else 0,
            'pending_count': int(summary['pending_count']) if summary['pending_count'] is not None else 0,
            'pending_amount': float(summary['pending_amount']) if summary['pending_amount'] is not None else 0.0
        }

        # Performance by bet type
        by_type_list = db.get_performance_by_type()
        by_type = {}
        for bt in by_type_list:
            by_type[bt['bet_type']] = {
                'count': int(bt['total_bets']) if bt['total_bets'] is not None else 0,
                'wagered': float(bt['total_wagered']) if bt['total_wagered'] is not None else 0.0,
                'won': int(bt['won_count']) if bt['won_count'] is not None else 0,
                'lost': int(bt['lost_count']) if bt['lost_count'] is not None else 0,
                'profit': float(bt['total_profit']) if bt['total_profit'] is not None else 0.0,
                'win_rate': float(bt['win_rate_percentage']) if bt['win_rate_percentage'] is not None else 0.0,
                'roi': float(bt['roi_percentage']) if bt['roi_percentage'] is not None else 0.0
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
            'weeks': [str(w['week_key']) for w in weekly_data],
            'values': [float(w['profit']) if w['profit'] is not None else 0.0 for w in weekly_data]
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
            bet_dict = {
                'date': bet['date'].strftime('%m/%d/%Y') if bet['date'] else '',
                'teams': bet.get('teams', ''),
                'description': bet.get('description', ''),
                'type': bet['bet_type'],
                'amount': float(bet['amount']) if bet['amount'] is not None else 0.0,
                'odds': bet.get('odds', 'N/A'),
                'profit': float(bet['profit']) if bet['profit'] is not None else 0.0,
                'status': bet['status'],
                'to_win': float(bet['to_win']) if bet['to_win'] is not None else 0.0
            }
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

@app.route('/api/run-script/sim_week9_10', methods=['POST'])
def api_run_simulator_predictions():
    """Run simulator predictions for next 2 weeks (dynamically determined)"""
    try:
        import subprocess
        from pathlib import Path

        # Check if request specifies a specific week
        week = None
        if request.is_json:
            data = request.get_json()
            week = data.get('week')

        script_path = Path(__file__).parent / 'simulation_engine' / 'nflfastR_simulator' / 'scripts' / 'generate_week9_10_predictions.py'

        # Build command with optional week argument
        cmd = ['python3', str(script_path)]
        if week:
            cmd.append(str(week))

        # Run the simulator prediction script
        result = subprocess.run(
            cmd,
            cwd='/Users/steveridder/Git/Football',
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '✅ Predictions generated successfully! Reload page to see Week 10.',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Prediction generation failed',
                'error': result.stderr or 'Script failed to run',
                'output': result.stdout
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Script timed out after 5 minutes'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

@app.route('/api/fetch-live-scores', methods=['POST'])
def api_fetch_live_scores():
    """Fetch live scores from ESPN and update predictions"""
    try:
        import subprocess
        from pathlib import Path

        # Run the fetch_live_scores script
        script_path = Path(__file__).parent / 'scripts' / 'fetch_live_scores.py'

        result = subprocess.run(
            ['python3', str(script_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            # Count how many games were updated from the output
            output_lines = result.stdout.split('\n')
            updated_games = 0
            for line in output_lines:
                if 'Updated' in line and 'games' in line:
                    # Extract number from "✅ Updated X games"
                    import re
                    match = re.search(r'Updated (\d+) games', line)
                    if match:
                        updated_games = int(match.group(1))

            return jsonify({
                'success': True,
                'message': f'Updated {updated_games} games with live scores',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Script failed: {result.stderr}',
                'output': result.stdout
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/run-weekly-prep', methods=['POST'])
def api_run_weekly_prep():
    """Run weekly data preparation script (NFLverse + calibration)"""
    try:
        import subprocess
        from pathlib import Path
        import os

        script_path = Path(__file__).parent / 'scripts' / 'weekly_data_prep.sh'

        # Make sure script is executable
        os.chmod(script_path, 0o755)

        result = subprocess.run(
            ['bash', str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '✅ Weekly data prep complete! NFLverse stats updated and calibration re-fit.',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr or 'Script failed',
                'output': result.stdout
            })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Script timed out after 5 minutes. This is unusual - check logs.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/generate-ai-picks', methods=['POST'])
def generate_ai_picks_route():
    """Generate ChatGPT picks for the week"""
    try:
        from edge_hunt.chatgpt_picks import generate_weekly_picks

        week = request.args.get('week', type=int)
        result = generate_weekly_picks(current_week=week, save_to_file=True)

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'error': f'Failed to generate picks: {str(e)}'
        }), 500


@app.route('/api/ai-picks')
def get_ai_picks():
    """Get saved ChatGPT picks for a week"""
    try:
        from edge_hunt.chatgpt_picks import load_weekly_picks

        week = request.args.get('week', type=int)
        result = load_weekly_picks(week=week)

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'error': f'Failed to load picks: {str(e)}'
        }), 500

@app.route('/api/trace/<away>/<home>/<int:week>')
def get_trace(away, home, week):
    """API endpoint to get trace data for a game."""
    from pathlib import Path
    import json

    season = 2025  # Default season
    trace_dir = Path("artifacts/traces")
    trace_filename = f"{away}_{home}_{week}_{season}.jsonl"
    trace_path = trace_dir / trace_filename

    if not trace_path.exists():
        return jsonify({'error': 'Trace not found'}), 404

    # Load trace events
    events = []
    with trace_path.open() as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    return jsonify({
        'game_id': f"{season}_{week}_{away}_{home}",
        'events': events,
        'total_events': len(events)
    })

@app.route('/trace/<away>/<home>/<int:week>')
def trace_viewer(away, home, week):
    """Trace viewer page."""
    return render_template('trace_viewer.html', away=away, home=home, week=week)

if __name__ == '__main__':
    app.run(debug=False, port=9876, host='0.0.0.0')

