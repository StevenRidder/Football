#!/usr/bin/env python3
"""
Backfill Accuracy Data for Weeks 1-7

This script populates the accuracy tracker with historical predictions and results
for the 2025 season Weeks 1-7, allowing immediate comparison of model performance.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import requests
import io
from nfl_edge.accuracy_tracker import create_tracker
from nfl_edge.predictions_api import fetch_all_predictions


def fetch_historical_games(season=2025, start_week=1, end_week=7):
    """Fetch completed games from ESPN for specified weeks"""
    print(f"\n{'='*80}")
    print(f"Fetching historical games for {season} Weeks {start_week}-{end_week}")
    print(f"{'='*80}\n")
    
    all_games = []
    
    for week in range(start_week, end_week + 1):
        try:
            espn_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
            params = {'seasontype': 2, 'week': week, 'year': season}
            response = requests.get(espn_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                week_games = []
                for event in events:
                    for comp in event.get('competitions', []):
                        competitors = comp.get('competitors', [])
                        if len(competitors) == 2:
                            home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                            away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                            
                            if home_team and away_team:
                                completed = comp.get('status', {}).get('type', {}).get('completed', False)
                                
                                if completed:
                                    game = {
                                        'week': week,
                                        'season': season,
                                        'home_team': home_team['team']['abbreviation'],
                                        'away_team': away_team['team']['abbreviation'],
                                        'home_score': int(home_team.get('score', 0)),
                                        'away_score': int(away_team.get('score', 0)),
                                        'completed': completed
                                    }
                                    week_games.append(game)
                                    all_games.append(game)
                
                print(f"  Week {week}: {len(week_games)} completed games")
        
        except Exception as e:
            print(f"  Week {week}: Error - {e}")
    
    print(f"\n✅ Total games fetched: {len(all_games)}")
    return all_games


def load_model_predictions(season=2025):
    """Load predictions from artifacts directory"""
    print(f"\n{'='*80}")
    print(f"Loading model predictions from artifacts")
    print(f"{'='*80}\n")
    
    artifacts_dir = Path('artifacts')
    if not artifacts_dir.exists():
        print("❌ Artifacts directory not found")
        return {}
    
    predictions = {}
    
    # Find all projection files
    for file in artifacts_dir.glob(f'week_{season}-*_projections.csv'):
        try:
            df = pd.read_csv(file)
            print(f"  Found: {file.name} ({len(df)} games)")
            
            for _, row in df.iterrows():
                key = (row['away'], row['home'])
                predictions[key] = {
                    'away': row['away'],
                    'home': row['home'],
                    'away_win_prob': 100 - row.get('Home win %', 50),
                    'home_win_prob': row.get('Home win %', 50),
                    'spread': row.get('Spread used (home-)', 0),
                    'total': row.get('Total used', 0)
                }
        
        except Exception as e:
            print(f"  Error loading {file.name}: {e}")
    
    print(f"\n✅ Loaded predictions for {len(predictions)} games")
    return predictions


def backfill_data(games, model_predictions):
    """Record historical predictions and results"""
    print(f"\n{'='*80}")
    print(f"Backfilling accuracy tracker")
    print(f"{'='*80}\n")
    
    tracker = create_tracker()
    
    recorded_predictions = 0
    recorded_results = 0
    skipped = 0
    
    for game in games:
        week = game['week']
        season = game['season']
        away = game['away_team']
        home = game['home_team']
        
        # Get model prediction
        key = (away, home)
        your_model_pred = model_predictions.get(key)
        
        if not your_model_pred:
            print(f"  Week {week}: {away} @ {home} - No prediction found, skipping")
            skipped += 1
            continue
        
        # Format prediction for tracker
        your_model = {
            'away_win_prob': your_model_pred['away_win_prob'],
            'home_win_prob': your_model_pred['home_win_prob'],
            'spread': your_model_pred['spread'],
            'total': your_model_pred['total']
        }
        
        # Get external predictions (may not be available for all games)
        external_preds = fetch_all_predictions(away, home)
        
        fivethirtyeight = None
        if external_preds.get('fivethirtyeight'):
            fivethirtyeight = external_preds['fivethirtyeight']
        
        vegas = None
        if external_preds.get('vegas'):
            vegas = external_preds['vegas']
        
        # Record prediction
        try:
            tracker.record_prediction(
                week=week,
                season=season,
                away=away,
                home=home,
                your_model=your_model,
                fivethirtyeight=fivethirtyeight,
                vegas=vegas
            )
            recorded_predictions += 1
        except Exception as e:
            print(f"  Week {week}: {away} @ {home} - Error recording prediction: {e}")
        
        # Record result
        try:
            tracker.record_result(
                week=week,
                season=season,
                away=away,
                home=home,
                away_score=game['away_score'],
                home_score=game['home_score'],
                spread_line=your_model_pred['spread'],
                total_line=your_model_pred['total']
            )
            recorded_results += 1
            print(f"  ✅ Week {week}: {away} @ {home} - {game['away_score']}-{game['home_score']}")
        except Exception as e:
            print(f"  Week {week}: {away} @ {home} - Error recording result: {e}")
    
    print(f"\n{'='*80}")
    print(f"BACKFILL SUMMARY")
    print(f"{'='*80}")
    print(f"  Predictions recorded: {recorded_predictions}")
    print(f"  Results recorded: {recorded_results}")
    print(f"  Skipped (no prediction): {skipped}")
    print(f"\n✅ Backfill complete!")


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("ACCURACY DATA BACKFILL - 2025 Season Weeks 1-7")
    print("="*80)
    
    # Fetch historical games
    games = fetch_historical_games(season=2025, start_week=1, end_week=7)
    
    if not games:
        print("\n❌ No games found. Exiting.")
        return
    
    # Load model predictions
    predictions = load_model_predictions(season=2025)
    
    if not predictions:
        print("\n❌ No predictions found. Run 'python3 run_week.py' first to generate predictions.")
        return
    
    # Backfill the data
    backfill_data(games, predictions)
    
    # Show accuracy report
    print(f"\n{'='*80}")
    print("ACCURACY REPORT")
    print(f"{'='*80}\n")
    
    tracker = create_tracker()
    report = tracker.get_accuracy_report(season=2025, min_games=1)
    
    if report.get('error'):
        print(f"❌ {report['error']}")
    else:
        print(f"Total games tracked: {report['total_games']}\n")
        
        for model_name, metrics in report.get('models', {}).items():
            if not metrics.get('error'):
                print(f"{model_name.upper()}:")
                print(f"  Games: {metrics['games']}")
                print(f"  Accuracy: {metrics['accuracy_pct']}%")
                print(f"  Correct picks: {metrics['correct_picks']}")
                print(f"  Brier score: {metrics['brier_score']}")
                print(f"  Calibration: {metrics['calibration']}")
                print()
    
    print(f"{'='*80}")
    print("✅ Done! Visit http://localhost:9876/accuracy to see the results")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()

