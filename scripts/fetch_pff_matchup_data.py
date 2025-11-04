#!/usr/bin/env python3
"""
Fetch PFF matchup data for a specific week.
This uses the public PFF API endpoint (no authentication required).

Data fetched:
- Power rankings (overall, offense, defense)
- QB names
- Team stats (if available)

Usage:
    python3 scripts/fetch_pff_matchup_data.py --week 10 --season 2025
"""

import argparse
import json
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional

# PFF public API endpoint
PFF_API_BASE = "https://www.pff.com/api/scoreboard/matchup"

def get_game_slug(away: str, home: str, week: int, season: int) -> str:
    """Convert team abbreviations to PFF game slug format."""
    # PFF uses full team names in slugs
    team_map = {
        'LV': 'las-vegas-raiders',
        'DEN': 'denver-broncos',
        'NE': 'new-england-patriots',
        'TB': 'tampa-bay-buccaneers',
        # Add more as needed
    }
    away_slug = team_map.get(away, away.lower().replace(' ', '-'))
    home_slug = team_map.get(home, home.lower().replace(' ', '-'))
    return f"{away_slug}_at_{home_slug}"

def fetch_matchup_data(season: int, week: int, away: str, home: str, game_id: Optional[int] = None) -> Optional[Dict]:
    """
    Fetch matchup data from PFF API.
    
    Args:
        season: Season year
        week: Week number
        away: Away team abbreviation
        home: Home team abbreviation
        game_id: Optional PFF game ID (if known)
    
    Returns:
        Dict with matchup data or None if fetch fails
    """
    # Try with game slug first
    game_slug = get_game_slug(away, home, week, season)
    if game_id:
        game_slug = f"{game_slug}_{game_id}"
    
    url = f"{PFF_API_BASE}?league=nfl&season={season}&week={week}&game={game_slug}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  HTTP {response.status_code} for {away} @ {home}")
            return None
    except Exception as e:
        print(f"❌ Error fetching {away} @ {home}: {e}")
        return None

def extract_matchup_stats(data: Dict, away: str, home: str) -> Dict:
    """Extract relevant stats from PFF matchup API response."""
    result = {
        'away_team': away,
        'home_team': home,
        'away_power_rank_overall': None,
        'away_power_rank_offense': None,
        'away_power_rank_defense': None,
        'home_power_rank_overall': None,
        'home_power_rank_offense': None,
        'home_power_rank_defense': None,
        'away_qb_name': None,
        'home_qb_name': None,
    }
    
    if 'away_power_rankings' in data:
        rankings = data['away_power_rankings']
        result['away_power_rank_overall'] = rankings.get('overall')
        result['away_power_rank_offense'] = rankings.get('offense')
        result['away_power_rank_defense'] = rankings.get('defense')
    
    if 'home_power_rankings' in data:
        rankings = data['home_power_rankings']
        result['home_power_rank_overall'] = rankings.get('overall')
        result['home_power_rank_offense'] = rankings.get('offense')
        result['home_power_rank_defense'] = rankings.get('defense')
    
    if 'away_qb' in data and 'player' in data['away_qb']:
        result['away_qb_name'] = data['away_qb']['player']
    
    if 'home_qb' in data and 'player' in data['home_qb']:
        result['home_qb_name'] = data['home_qb']['player']
    
    return result

def fetch_week_matchups(season: int, week: int, games: List[Dict]) -> pd.DataFrame:
    """
    Fetch matchup data for all games in a week.
    
    Args:
        season: Season year
        week: Week number
        games: List of game dicts with 'away', 'home', and optionally 'pff_game_id'
    
    Returns:
        DataFrame with matchup data
    """
    all_stats = []
    
    for game in games:
        away = game['away']
        home = game['home']
        game_id = game.get('pff_game_id')
        
        print(f"📥 Fetching {away} @ {home}...")
        data = fetch_matchup_data(season, week, away, home, game_id)
        
        if data:
            stats = extract_matchup_stats(data, away, home)
            stats['season'] = season
            stats['week'] = week
            all_stats.append(stats)
            print(f"   ✅ Got rankings: Away={stats['away_power_rank_overall']}, Home={stats['home_power_rank_overall']}")
        else:
            print(f"   ⚠️  No data available")
    
    if all_stats:
        return pd.DataFrame(all_stats)
    else:
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description='Fetch PFF matchup data for a week')
    parser.add_argument('--week', type=int, required=True, help='Week number')
    parser.add_argument('--season', type=int, default=2025, help='Season year')
    parser.add_argument('--output', type=str, help='Output CSV file path')
    
    args = parser.parse_args()
    
    # Load games from schedule
    script_dir = Path(__file__).parent.parent
    schedule_file = script_dir / "data" / "full_2025_schedule.csv"
    
    if not schedule_file.exists():
        print(f"❌ Schedule file not found: {schedule_file}")
        print("   Please provide game list manually or create schedule file")
        return
    
    schedule_df = pd.read_csv(schedule_file)
    week_games = schedule_df[
        (schedule_df['season'] == args.season) &
        (schedule_df['week'] == args.week)
    ]
    
    if len(week_games) == 0:
        print(f"❌ No games found for {args.season} Week {args.week}")
        return
    
    games = []
    for _, row in week_games.iterrows():
        games.append({
            'away': row['away'],
            'home': row['home'],
            'pff_game_id': row.get('pff_game_id')  # Optional
        })
    
    # Fetch matchup data
    df = fetch_week_matchups(args.season, args.week, games)
    
    if len(df) == 0:
        print("❌ No matchup data fetched")
        return
    
    # Save to CSV
    if args.output:
        output_file = Path(args.output)
    else:
        output_dir = script_dir / "simulation_engine" / "nflfastR_simulator" / "data"
        output_file = output_dir / f"pff_matchup_week{args.week}.csv"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"\n✅ Saved {len(df)} matchups to: {output_file}")

if __name__ == "__main__":
    main()

