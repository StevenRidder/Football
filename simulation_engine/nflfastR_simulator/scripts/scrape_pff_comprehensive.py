#!/usr/bin/env python3
"""
Comprehensive PFF Data Scraper
Extracts 5 years of PFF data (2020-2024 full seasons + 2025 weeks 1-8)

Data extracted:
1. Team-level grades (OL pass blocking, DL pass rush, coverage, run blocking, run defense)
2. Player-level grades (QB, OL, DL, WR, RB, TE)
3. Matchup-specific data
4. Advanced metrics (pressure rates, win rates, EPA)

Usage: Run this script while logged into PFF Premium in your browser.
The script will use the browser's session cookies.
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

# PFF API endpoints
BASE_URL = "https://premium.pff.com/api/v1"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "pff_raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def save_json(data, filename):
    """Save data to JSON file."""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved: {filepath}")

def fetch_team_overview(session, season, weeks=None):
    """
    Fetch team overview data including all position grades.
    
    Includes:
    - OFF, PASS, PBLK (pass blocking), RECV, RUN, RBLK (run blocking)
    - DEF, RDEF (run defense), TACK, PRSH (pass rush), COV (coverage)
    - SPEC (special teams)
    """
    if weeks is None:
        # Full season + playoffs
        weeks = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,28,29,30,32"
    else:
        weeks = ",".join(map(str, weeks))
    
    url = f"{BASE_URL}/teams/overview"
    params = {
        "league": "nfl",
        "season": season,
        "week": weeks
    }
    
    print(f"   Fetching team overview for {season} weeks {weeks[:20]}...")
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_player_grades(session, season, position, weeks=None):
    """
    Fetch player-level grades by position.
    
    Positions: QB, RB, WR, TE, T, G, C, EDGE, DI, LB, CB, S
    """
    if weeks is None:
        weeks = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,28,29,30,32"
    else:
        weeks = ",".join(map(str, weeks))
    
    url = f"{BASE_URL}/players"
    params = {
        "league": "nfl",
        "season": season,
        "week": weeks,
        "position": position
    }
    
    print(f"   Fetching {position} grades for {season}...")
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_team_stats(session, season, weeks=None):
    """
    Fetch detailed team statistics.
    
    Includes EPA, success rates, explosive play rates, etc.
    """
    if weeks is None:
        weeks = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,28,29,30,32"
    else:
        weeks = ",".join(map(str, weeks))
    
    url = f"{BASE_URL}/teams"
    params = {
        "league": "nfl",
        "season": season,
        "week": weeks
    }
    
    print(f"   Fetching team stats for {season}...")
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_games(session, season, week=None):
    """
    Fetch game-level data including grades for each game.
    """
    url = f"{BASE_URL}/games"
    params = {
        "league": "nfl",
        "season": season
    }
    if week:
        params["week"] = week
    
    print(f"   Fetching games for {season}" + (f" week {week}" if week else "") + "...")
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()

def main():
    """Main scraping function."""
    print("🚀 PFF Comprehensive Data Scraper")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: You must be logged into PFF Premium in your browser!")
    print("   This script will attempt to use your browser's session.\n")
    
    # Prompt user to paste session cookie
    print("📋 Instructions:")
    print("   1. Open Chrome DevTools (F12)")
    print("   2. Go to Application > Cookies > https://premium.pff.com")
    print("   3. Find the '_premium_session' cookie")
    print("   4. Copy its VALUE (the long string)")
    print("   5. Paste it below\n")
    
    session_cookie = input("Paste your PFF session cookie: ").strip()
    
    if not session_cookie:
        print("❌ No session cookie provided. Exiting.")
        return
    
    # Create session with cookie
    session = requests.Session()
    session.cookies.set("_premium_session", session_cookie, domain="premium.pff.com")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://premium.pff.com/nfl/teams/2024/REGPO"
    })
    
    # Test authentication
    print("\n🔐 Testing authentication...")
    try:
        test_response = session.get(f"{BASE_URL}/leagues")
        test_response.raise_for_status()
        print("✅ Authentication successful!\n")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("   Make sure you copied the correct session cookie.")
        return
    
    # Define what to scrape
    seasons_full = [2020, 2021, 2022, 2023, 2024]
    season_2025_weeks = list(range(1, 9))  # Weeks 1-8
    
    positions = ["QB", "RB", "WR", "TE", "T", "G", "C", "EDGE", "DI", "LB", "CB", "S"]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("📊 Starting data extraction...")
    print("=" * 60)
    
    # ========================================
    # 1. TEAM OVERVIEW DATA (All Grades)
    # ========================================
    print("\n1️⃣  Extracting Team Overview Data (OL/DL/Coverage grades)")
    for season in seasons_full:
        try:
            data = fetch_team_overview(session, season)
            save_json(data, f"team_overview_{season}_full.json")
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"   ❌ Error fetching {season}: {e}")
    
    # 2025 weeks 1-8
    try:
        data = fetch_team_overview(session, 2025, weeks=season_2025_weeks)
        save_json(data, f"team_overview_2025_weeks1-8.json")
        time.sleep(1)
    except Exception as e:
        print(f"   ❌ Error fetching 2025: {e}")
    
    # ========================================
    # 2. TEAM STATS (EPA, Success Rates, etc.)
    # ========================================
    print("\n2️⃣  Extracting Team Statistics")
    for season in seasons_full:
        try:
            data = fetch_team_stats(session, season)
            save_json(data, f"team_stats_{season}_full.json")
            time.sleep(1)
        except Exception as e:
            print(f"   ❌ Error fetching {season}: {e}")
    
    try:
        data = fetch_team_stats(session, 2025, weeks=season_2025_weeks)
        save_json(data, f"team_stats_2025_weeks1-8.json")
        time.sleep(1)
    except Exception as e:
        print(f"   ❌ Error fetching 2025: {e}")
    
    # ========================================
    # 3. PLAYER GRADES (All Positions)
    # ========================================
    print("\n3️⃣  Extracting Player Grades by Position")
    for season in seasons_full:
        for position in positions:
            try:
                data = fetch_player_grades(session, season, position)
                save_json(data, f"players_{position}_{season}_full.json")
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"   ❌ Error fetching {position} {season}: {e}")
    
    # 2025 player grades
    for position in positions:
        try:
            data = fetch_player_grades(session, 2025, position, weeks=season_2025_weeks)
            save_json(data, f"players_{position}_2025_weeks1-8.json")
            time.sleep(0.5)
        except Exception as e:
            print(f"   ❌ Error fetching {position} 2025: {e}")
    
    # ========================================
    # 4. GAME-LEVEL DATA
    # ========================================
    print("\n4️⃣  Extracting Game-Level Data")
    for season in seasons_full:
        try:
            data = fetch_games(session, season)
            save_json(data, f"games_{season}_full.json")
            time.sleep(1)
        except Exception as e:
            print(f"   ❌ Error fetching games {season}: {e}")
    
    # 2025 games by week
    for week in season_2025_weeks:
        try:
            data = fetch_games(session, 2025, week=week)
            save_json(data, f"games_2025_week{week}.json")
            time.sleep(0.5)
        except Exception as e:
            print(f"   ❌ Error fetching 2025 week {week}: {e}")
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "=" * 60)
    print("✅ Data extraction complete!")
    print(f"📁 Data saved to: {OUTPUT_DIR}")
    print("\nData includes:")
    print("  • Team grades (OL pass blocking, DL pass rush, coverage, etc.)")
    print("  • Player grades (QB, OL, DL, WR, RB, TE, etc.)")
    print("  • Team statistics (EPA, success rates, explosive plays)")
    print("  • Game-level data")
    print(f"  • Seasons: 2020-2024 (full) + 2025 (weeks 1-8)")
    print(f"  • Total files: ~{len(seasons_full) * (2 + len(positions)) + len(season_2025_weeks) * 2 + len(positions) + 3}")
    
    # Create metadata file
    metadata = {
        "extraction_date": datetime.now().isoformat(),
        "seasons_full": seasons_full,
        "season_2025_weeks": season_2025_weeks,
        "positions": positions,
        "data_types": [
            "team_overview",
            "team_stats",
            "player_grades",
            "games"
        ],
        "notes": "Comprehensive PFF data extraction for NFL betting model"
    }
    save_json(metadata, f"_metadata_{timestamp}.json")

if __name__ == "__main__":
    main()

