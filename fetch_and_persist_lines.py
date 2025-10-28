"""
Fetch current lines from Odds API and persist them
Run this periodically (e.g., every hour) to track line movements
"""
import os
import sys
from dotenv import load_dotenv
from line_tracker import LineTracker
from nfl_edge.data_ingest import fetch_market_lines_live
from schedules import CURRENT_WEEK, CURRENT_SEASON

load_dotenv()


def main():
    """Fetch and persist current lines"""
    print(f"Fetching lines for Week {CURRENT_WEEK}, {CURRENT_SEASON} season...")
    
    # Check API key is set
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key:
        print("ERROR: ODDS_API_KEY not set in .env")
        sys.exit(1)
    
    try:
        market_lines = fetch_market_lines_live()
        
        if not market_lines:
            print("No lines returned from Odds API")
            return
        
        # Convert to format for line tracker
        games = []
        for matchup, lines in market_lines.items():
            # matchup is already a tuple (away, home)
            away, home = matchup
            games.append({
                'away': away,
                'home': home,
                'spread': lines.get('spread'),
                'total': lines.get('total'),
                'away_ml': lines.get('away_ml'),
                'home_ml': lines.get('home_ml')
            })
        
        # Persist to database
        tracker = LineTracker()
        tracker.record_lines(CURRENT_SEASON, CURRENT_WEEK, games)
        
        print(f"✓ Recorded lines for {len(games)} games")
        
        # Show summary
        for game in games:
            spread_str = f"{game['spread']:+.1f}" if game['spread'] is not None else "N/A"
            total_str = f"{game['total']:.1f}" if game['total'] is not None else "N/A"
            print(f"  {game['away']:3} @ {game['home']:3}: "
                  f"Spread {spread_str:>6}, Total {total_str:>5}")
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

