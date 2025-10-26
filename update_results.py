"""
Auto-update actual results for accuracy tracking

Run this after games have been played to fetch actual scores
and update the accuracy tracker.

Usage:
    python3 update_results.py           # Update current week
    python3 update_results.py --week 8  # Update specific week
"""

import argparse
from nfl_edge.accuracy_tracker import create_tracker
import datetime


def fetch_completed_games(week: int, season: int = 2025):
    """Fetch completed games from ESPN API"""
    import requests
    
    print(f"Fetching completed games for Week {week}, {season}...")
    
    completed_games = []
    
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {
            'seasontype': 2,  # Regular season
            'week': week,
            'year': season
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            
            for event in events:
                for comp in event.get('competitions', []):
                    # Check if game is completed
                    status = comp.get('status', {})
                    if not status.get('type', {}).get('completed', False):
                        continue
                    
                    competitors = comp.get('competitors', [])
                    if len(competitors) == 2:
                        home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                        away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                        
                        if home_team and away_team:
                            completed_games.append({
                                'week': week,
                                'season': season,
                                'away': away_team['team']['abbreviation'],
                                'home': home_team['team']['abbreviation'],
                                'away_score': int(away_team.get('score', 0)),
                                'home_score': int(home_team.get('score', 0))
                            })
            
            print(f"✅ Found {len(completed_games)} completed games")
            return completed_games
        
        else:
            print(f"❌ ESPN API returned status {response.status_code}")
            return []
    
    except Exception as e:
        print(f"❌ Error fetching games: {e}")
        return []


def update_results(week: int = None, season: int = 2025):
    """Update actual results for a given week"""
    
    if week is None:
        # Auto-detect current week
        now = datetime.datetime.now()
        week = now.isocalendar()[1] - 35  # Approximate NFL week
    
    print(f"\n{'='*70}")
    print(f"UPDATING RESULTS - Week {week}, {season}")
    print(f"{'='*70}\n")
    
    # Fetch completed games
    games = fetch_completed_games(week, season)
    
    if not games:
        print("⚠️  No completed games found for this week")
        return
    
    # Record results in accuracy tracker
    tracker = create_tracker()
    
    recorded = 0
    for game in games:
        try:
            tracker.record_result(
                week=game['week'],
                season=game['season'],
                away=game['away'],
                home=game['home'],
                away_score=game['away_score'],
                home_score=game['home_score']
            )
            print(f"✅ {game['away']} @ {game['home']}: {game['away_score']}-{game['home_score']}")
            recorded += 1
        except Exception as e:
            print(f"❌ Error recording {game['away']} @ {game['home']}: {e}")
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Games found: {len(games)}")
    print(f"Results recorded: {recorded}")
    print("\n✅ Results updated! Visit http://localhost:9876/accuracy to see accuracy")
    
    # Show quick accuracy summary
    try:
        report = tracker.get_accuracy_report(season=season, min_games=1)
        if report.get('models', {}).get('your_model'):
            model = report['models']['your_model']
            print(f"\n📊 Current Accuracy: {model['accuracy_pct']}% ({model['correct_picks']}/{model['games']} correct)")
            print(f"   Brier Score: {model['brier_score']}")
    except:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update actual game results for accuracy tracking')
    parser.add_argument('--week', type=int, help='Week number to update (default: auto-detect current week)')
    parser.add_argument('--season', type=int, default=2025, help='Season year (default: 2025)')
    
    args = parser.parse_args()
    
    update_results(week=args.week, season=args.season)

