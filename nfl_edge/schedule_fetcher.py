"""
Automatically fetch upcoming NFL schedule instead of hardcoded lists.
"""

from typing import List, Tuple
from nfl_edge.data_ingest import NFLVERSE_TEAM_BASE, _read_url_csv


def get_current_week(season: int = 2025) -> int:
    """
    Determine the current NFL week based on what data exists.
    
    Returns:
        Next week to predict (last completed week + 1)
    """
    url = f"{NFLVERSE_TEAM_BASE}stats_team_week_{season}.csv"
    df = _read_url_csv(url)
    df = df[df['season_type'] == 'REG']
    
    # Find the last week with complete data
    last_complete_week = 0
    for week in sorted(df['week'].unique()):
        week_data = df[df['week'] == week]
        n_teams = len(week_data)
        # Full week should have 32 teams (16 games) or 28 teams (14 games with byes)
        if n_teams >= 28:
            last_complete_week = week
    
    return last_complete_week + 1


def get_upcoming_matchups(season: int = 2025) -> List[Tuple[str, str]]:
    """
    Get the upcoming week's matchups from nflverse schedules.
    
    Returns:
        List of (away_team, home_team) tuples
    """
    try:
        # Try to fetch schedule data
        schedule_url = "https://github.com/nflverse/nflverse-data/releases/download/schedules/schedules.csv"
        schedules = _read_url_csv(schedule_url)
        
        # Filter to current season
        schedules = schedules[schedules['season'] == season].copy()
        schedules = schedules[schedules['game_type'] == 'REG'].copy()
        
        # Get the week we want to predict
        current_week = get_current_week(season)
        
        week_games = schedules[schedules['week'] == current_week].copy()
        
        if week_games.empty:
            print(f"⚠️  No schedule found for Week {current_week}, using fallback")
            return get_fallback_schedule()
        
        # Extract matchups
        matchups = []
        for _, row in week_games.iterrows():
            away = row['away_team']
            home = row['home_team']
            matchups.append((away, home))
        
        print(f"✅ Fetched {len(matchups)} games for Week {current_week}")
        return matchups
        
    except Exception as e:
        print(f"⚠️  Could not fetch schedule: {e}")
        print("Using fallback schedule from schedules.py")
        return get_fallback_schedule()


def get_fallback_schedule() -> List[Tuple[str, str]]:
    """
    Fallback to hardcoded schedule if dynamic fetch fails.
    """
    from schedules import THIS_WEEK
    return THIS_WEEK


if __name__ == "__main__":
    print("=" * 80)
    print("NFL Schedule Fetcher Test")
    print("=" * 80)
    
    current_week = get_current_week()
    print(f"\nCurrent Week: {current_week}")
    
    matchups = get_upcoming_matchups()
    print(f"\nUpcoming Games ({len(matchups)}):")
    for away, home in matchups:
        print(f"  {away} @ {home}")

