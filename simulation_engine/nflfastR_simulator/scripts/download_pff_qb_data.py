#!/usr/bin/env python3
"""
Download PFF QB data including depth charts and injury status.

Uses PFF Premium API to get:
1. QB grades by week
2. Depth chart information (who's starting)
3. Player status (active/injured)
4. Projected starters for future weeks
"""

import requests
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# PFF API endpoints
BASE_URL = "https://premium.pff.com/api/v1"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "pff_raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_session():
    """Get authenticated PFF session."""
    print("\n🔐 PFF Authentication")
    print("=" * 80)
    print("📋 Instructions:")
    print("   1. Open Chrome DevTools (F12)")
    print("   2. Go to Application > Cookies > https://premium.pff.com")
    print("   3. Find the '_premium_session' cookie")
    print("   4. Copy its VALUE (the long string)")
    print("   5. Paste it below\n")
    
    session_cookie = input("Paste your PFF session cookie: ").strip()
    
    if not session_cookie:
        print("❌ No session cookie provided. Exiting.")
        return None
    
    session = requests.Session()
    session.cookies.set("_premium_session", session_cookie, domain="premium.pff.com")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://premium.pff.com/nfl/players"
    })
    
    # Test authentication
    print("\n🔐 Testing authentication...")
    try:
        test_response = session.get(f"{BASE_URL}/leagues")
        test_response.raise_for_status()
        print("✅ Authentication successful!\n")
        return session
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

def fetch_players(session, season, position="QB", weeks=None):
    """
    Fetch player data from PFF API.
    
    Endpoints to try:
    - /api/v1/players?position=QB&season=2025
    - /api/v1/players/grades?position=QB&season=2025&week=1,2,3,4,5,6,7,8
    - /api/v1/facet/summary?position=QB&season=2025
    """
    print(f"\n📥 Fetching {position} data for {season}...")
    
    # Try multiple endpoints
    endpoints = [
        f"/players/grades?position={position}&league=nfl&season={season}&week={weeks}" if weeks else f"/players/grades?position={position}&league=nfl&season={season}",
        f"/players?position={position}&league=nfl&season={season}",
        f"/facet/summary?position={position}&league=nfl&season={season}",
    ]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"   Trying: {endpoint[:50]}...")
        
        try:
            response = session.get(url)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success! Got {len(data) if isinstance(data, list) else 'data'}")
                
                # Save raw response
                filename = f"pff_qb_{season}_{datetime.now().strftime('%Y%m%d')}.json"
                filepath = OUTPUT_DIR / filename
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"   💾 Saved to: {filepath}")
                
                return data
            else:
                print(f"   ❌ {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n⚠️  Could not fetch {position} data from any endpoint")
    return None

def fetch_depth_charts(session, season, week=None):
    """
    Fetch depth chart data (projected starters).
    
    Endpoints to try:
    - /api/v1/depth-charts?league=nfl&season=2025
    - /api/v1/rosters?league=nfl&season=2025
    """
    print(f"\n📥 Fetching depth charts for {season}...")
    
    endpoints = [
        f"/depth-charts?league=nfl&season={season}" + (f"&week={week}" if week else ""),
        f"/rosters?league=nfl&season={season}",
        f"/teams/rosters?league=nfl&season={season}",
    ]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"   Trying: {endpoint[:50]}...")
        
        try:
            response = session.get(url)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success!")
                
                # Save raw response
                filename = f"pff_depth_charts_{season}_{datetime.now().strftime('%Y%m%d')}.json"
                filepath = OUTPUT_DIR / filename
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"   💾 Saved to: {filepath}")
                
                return data
            else:
                print(f"   ❌ {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n⚠️  Could not fetch depth charts from any endpoint")
    return None

def extract_qb_starters(data, season):
    """Extract QB starter information from depth chart or player data."""
    starters = []
    
    # Parse the data structure (depends on what endpoint worked)
    if isinstance(data, dict):
        if 'players' in data:
            players = data['players']
        elif 'depth_charts' in data:
            # Extract QBs from depth charts
            depth_charts = data['depth_charts']
            for team_chart in depth_charts:
                if 'qb' in team_chart or 'QB' in team_chart:
                    # Extract QB1
                    pass
        else:
            players = [data]
    elif isinstance(data, list):
        players = data
    else:
        return []
    
    # Extract QB info
    for player in players:
        if isinstance(player, dict):
            starters.append({
                'season': season,
                'player_name': player.get('name', player.get('player_name')),
                'team': player.get('team', player.get('team_abbreviation')),
                'position': player.get('position', 'QB'),
                'grade': player.get('grade', player.get('overall_grade')),
                'depth': player.get('depth', 1),  # 1 = starter, 2 = backup
                'status': player.get('status', 'active'),  # active/injured/out
            })
    
    return starters

def main():
    """Main function to download PFF QB data."""
    print("="*80)
    print("PFF QB DATA DOWNLOADER")
    print("="*80)
    
    session = get_session()
    if not session:
        return
    
    # Download for 2024 and 2025
    for season in [2024, 2025]:
        weeks = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18" if season == 2024 else "1,2,3,4,5,6,7,8,9,10"
        
        # Get QB data
        qb_data = fetch_players(session, season, "QB", weeks)
        
        # Get depth charts (starters/injuries)
        depth_data = fetch_depth_charts(session, season)
    
    print("\n" + "="*80)
    print("✅ Download complete!")
    print("="*80)
    print("\n📝 Next steps:")
    print("   1. Check data/pff_raw/ for new QB files")
    print("   2. Parse the JSON to extract starter information")
    print("   3. Create projected_starters.csv for future weeks")

if __name__ == '__main__':
    main()

