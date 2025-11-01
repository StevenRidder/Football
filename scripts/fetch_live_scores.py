#!/usr/bin/env python3
"""
Fetch live scores from ESPN API and update predictions CSV with actual results.
Run this every hour during game days to keep results fresh.
"""
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import sys

def fetch_espn_scores(season: int, week: int):
    """Fetch actual scores from ESPN for a specific week"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {'seasontype': 2, 'week': week, 'year': season}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            scores = []
            
            for event in data.get('events', []):
                competition = event.get('competitions', [{}])[0]
                competitors = competition.get('competitors', [])
                status = competition.get('status', {})
                
                # Get teams
                home_team = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                away_team = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                
                if home_team and away_team:
                    game_state = status.get('type', {}).get('state', 'pre')  # pre, in, post
                    completed = status.get('type', {}).get('completed', False)
                    
                    game_info = {
                        'week': week,
                        'season': season,
                        'home_team': home_team['team']['abbreviation'],
                        'away_team': away_team['team']['abbreviation'],
                        'home_score': int(home_team.get('score', 0)) if game_state != 'pre' else None,
                        'away_score': int(away_team.get('score', 0)) if game_state != 'pre' else None,
                        'completed': completed,
                        'game_state': game_state,  # pre, in, post
                        'quarter': status.get('period', 0),
                        'clock': status.get('displayClock', ''),
                        'game_id': event.get('id'),
                        'last_updated': datetime.now().isoformat()
                    }
                    scores.append(game_info)
            
            return scores
        else:
            print(f"❌ ESPN API returned {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching ESPN scores: {e}")
        return []


def update_predictions_with_actuals(predictions_file: Path, scores: list):
    """Update predictions CSV with actual scores and results"""
    
    if not predictions_file.exists():
        print(f"❌ Predictions file not found: {predictions_file}")
        return
    
    # Load predictions
    df = pd.read_csv(predictions_file)
    
    updates = 0
    for score in scores:
        # Find matching game
        mask = (
            (df['home_team'] == score['home_team']) & 
            (df['away_team'] == score['away_team']) & 
            (df['week'] == score['week']) &
            (df['season'] == score['season'])
        )
        
        matching_rows = df[mask]
        
        if len(matching_rows) > 0:
            idx = matching_rows.index[0]
            
            # Update actual scores if game has started
            if score['home_score'] is not None:
                df.loc[idx, 'actual_home_score'] = score['home_score']
                df.loc[idx, 'actual_away_score'] = score['away_score']
                df.loc[idx, 'is_completed'] = score['completed']
                
                # Update final score string
                df.loc[idx, 'final_score'] = f"{score['away_score']}-{score['home_score']}"
                
                # Calculate spread and total results if completed
                if score['completed']:
                    actual_spread = score['home_score'] - score['away_score']
                    actual_total = score['home_score'] + score['away_score']
                    
                    # Get market lines
                    closing_spread = df.loc[idx, 'closing_spread']
                    closing_total = df.loc[idx, 'closing_total']
                    
                    # Determine spread result
                    spread_rec = df.loc[idx, 'spread_recommendation']
                    if pd.notna(spread_rec) and spread_rec != 'Pass':
                        if 'Home' in spread_rec:
                            # We bet on home to cover
                            df.loc[idx, 'spread_result'] = 'WIN' if actual_spread > closing_spread else 'LOSS'
                        elif 'Away' in spread_rec:
                            # We bet on away to cover
                            df.loc[idx, 'spread_result'] = 'WIN' if actual_spread < closing_spread else 'LOSS'
                    
                    # Determine total result
                    total_rec = df.loc[idx, 'total_recommendation']
                    if pd.notna(total_rec) and total_rec != 'Pass':
                        if 'Over' in total_rec:
                            df.loc[idx, 'total_result'] = 'WIN' if actual_total > closing_total else 'LOSS'
                        elif 'Under' in total_rec:
                            df.loc[idx, 'total_result'] = 'WIN' if actual_total < closing_total else 'LOSS'
                
                updates += 1
                
                status_emoji = "🔴" if score['game_state'] == 'in' else "✅" if score['completed'] else "⏰"
                quarter_info = f"Q{score['quarter']} {score['clock']}"
                game_status = 'FINAL' if score['completed'] else quarter_info
                print(f"{status_emoji} {score['away_team']}@{score['home_team']}: {score['away_score']}-{score['home_score']} {game_status}")
    
    if updates > 0:
        # Save updated predictions
        df.to_csv(predictions_file, index=False)
        print(f"\n✅ Updated {updates} games in {predictions_file.name}")
    else:
        print(f"\n⚠️  No games updated")
    
    return updates


def main():
    """Main function to fetch and update scores"""
    
    # Configuration
    PREDICTIONS_FILE = Path(__file__).parent.parent / "artifacts" / "simulator_predictions.csv"
    CURRENT_SEASON = 2025
    
    # Determine which weeks to fetch (weeks 1-18)
    # For now, fetch current and upcoming weeks
    weeks_to_check = list(range(1, 11))  # Weeks 1-10
    
    print("=" * 80)
    print("🏈 ESPN LIVE SCORE FETCHER")
    print("=" * 80)
    print(f"📅 Season: {CURRENT_SEASON}")
    print(f"📊 Checking weeks: {min(weeks_to_check)}-{max(weeks_to_check)}")
    print(f"💾 Target file: {PREDICTIONS_FILE.name}")
    print("=" * 80)
    
    total_updates = 0
    
    for week in weeks_to_check:
        print(f"\n📥 Fetching Week {week}...")
        scores = fetch_espn_scores(CURRENT_SEASON, week)
        
        if scores:
            print(f"   Found {len(scores)} games")
            updates = update_predictions_with_actuals(PREDICTIONS_FILE, scores)
            total_updates += updates
        else:
            print(f"   No data available")
    
    print("\n" + "=" * 80)
    print(f"✅ Score fetch complete! Updated {total_updates} games total.")
    print(f"⏰ Last run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

