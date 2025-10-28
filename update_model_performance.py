#!/usr/bin/env python3
"""
Auto-update model performance by fetching final scores and comparing to predictions.
Run this daily after games complete.
"""
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
from nfl_edge.accuracy_tracker import AccuracyTracker
import requests

def fetch_espn_scores(week, season=2025):
    """Fetch final scores from ESPN API"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {
            'dates': season,
            'seasontype': 2,  # Regular season
            'week': week
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for event in data.get('events', []):
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) != 2:
                continue
            
            # Get teams and scores (use abbreviations to match predictions)
            home_team = None
            away_team = None
            home_score = None
            away_score = None
            
            for comp in competitors:
                team_abbr = comp.get('team', {}).get('abbreviation', '')
                score = int(comp.get('score', 0))
                
                if comp.get('homeAway') == 'home':
                    home_team = team_abbr
                    home_score = score
                else:
                    away_team = team_abbr
                    away_score = score
            
            # Include completed and in-progress games
            status = competition.get('status', {}).get('type', {}).get('name', '')
            if status in ['STATUS_FINAL', 'STATUS_IN_PROGRESS'] and home_team and away_team:
                games.append({
                    'away_team': away_team,
                    'home_team': home_team,
                    'away_score': away_score,
                    'home_score': home_score,
                    'status': status
                })
        
        return games
        
    except Exception as e:
        print(f"Error fetching ESPN scores: {e}")
        return []

def update_performance(week=None, season=2025):
    """Update model performance for a specific week"""
    
    # If no week specified, use current week
    if week is None:
        # Estimate current week (rough approximation)
        season_start = datetime(2025, 9, 4)  # Typical NFL season start
        weeks_elapsed = (datetime.now() - season_start).days // 7
        week = max(1, min(18, weeks_elapsed + 1))
    
    print(f"Updating model performance for Week {week}, {season}...")
    
    # Load predictions from artifacts
    artifacts = Path("artifacts")
    
    # Try to find predictions for the specific week
    week_file = artifacts / f"predictions_2025_week{week}_*.csv"
    csvs = sorted(artifacts.glob(f"predictions_2025_week{week}_*.csv"))
    
    # If no week-specific file, try generic pattern
    if not csvs:
        csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
        # Filter to get the one without "week" in name (current week)
        csvs = [f for f in csvs if '_week' not in f.name]
    
    if not csvs:
        print("❌ No prediction files found in artifacts/")
        return False
    
    predictions = pd.read_csv(csvs[-1])
    if predictions is None or predictions.empty:
        print("❌ No predictions found")
        return False
    
    # Use all predictions from the latest file (week is in filename)
    week_preds = predictions.copy()
    print(f"Found {len(week_preds)} predictions in {csvs[-1].name}")
    
    # Fetch actual scores
    scores = fetch_espn_scores(week, season)
    if not scores:
        print("❌ No scores found")
        return False
    
    print(f"Found {len(scores)} completed games")
    
    # Initialize tracker
    tracker = AccuracyTracker()
    
    # Match predictions to scores and record results
    updated_count = 0
    for _, pred in week_preds.iterrows():
        away = pred['away']
        home = pred['home']
        
        # Find matching score (exact match on abbreviations)
        score = next((s for s in scores 
                     if s['away_team'] == away and s['home_team'] == home), None)
        
        if score and score['status'] == 'STATUS_FINAL':
            try:
                # Record the result
                tracker.record_result(
                    week=week,
                    season=season,
                    away=away,
                    home=home,
                    away_score=score['away_score'],
                    home_score=score['home_score']
                )
                updated_count += 1
                print(f"✓ {away} @ {home}: {score['away_score']}-{score['home_score']}")
            except Exception as e:
                print(f"✗ Error recording {away} @ {home}: {e}")
        else:
            print(f"⚠ No score found for {away} @ {home}")
    
    print(f"\n✅ Updated {updated_count} game results")
    
    # Show updated stats
    report = tracker.get_accuracy_report(season=season)
    if report and 'overall' in report:
        overall = report['overall']
        print("\n📊 Updated Performance:")
        print(f"  Spread: {overall.get('spread_correct', 0)}-{overall.get('spread_incorrect', 0)} ({overall.get('spread_accuracy', 0):.1f}%)")
        print(f"  Total: {overall.get('total_correct', 0)}-{overall.get('total_incorrect', 0)} ({overall.get('total_accuracy', 0):.1f}%)")
        print(f"  ML: {overall.get('ml_correct', 0)}-{overall.get('ml_incorrect', 0)} ({overall.get('ml_accuracy', 0):.1f}%)")
    
    return True

if __name__ == '__main__':
    week = int(sys.argv[1]) if len(sys.argv) > 1 else None
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    
    success = update_performance(week, season)
    sys.exit(0 if success else 1)

