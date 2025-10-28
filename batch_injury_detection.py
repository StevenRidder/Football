"""
Batch LLM injury detection - runs 2-3x per day, caches to SQLite DB.

Schedule:
- Wednesday 6 PM ET: First pass (early injury reports)
- Friday 6 PM ET: Second pass (updated injury reports)
- Sunday 11 AM ET: Final pass (game day inactives)
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict
import pandas as pd

from edge_hunt.llm_injury_detector import detect_injuries_openai, calculate_injury_impact

# Database setup
DB_PATH = Path("artifacts/injury_cache.db")


def init_db():
    """Initialize SQLite database for injury caching."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS injury_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week INTEGER NOT NULL,
            season INTEGER NOT NULL,
            away_team TEXT NOT NULL,
            home_team TEXT NOT NULL,
            detection_time TEXT NOT NULL,
            injuries_json TEXT NOT NULL,
            away_impact REAL NOT NULL,
            home_impact REAL NOT NULL,
            UNIQUE(week, season, away_team, home_team, detection_time)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_game 
        ON injury_reports(week, season, away_team, home_team)
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def batch_detect_injuries(week: int, season: int = 2025, pass_name: str = "wednesday"):
    """
    Batch detect injuries for all games in a week.
    
    Args:
        week: NFL week number
        season: NFL season year
        pass_name: "wednesday", "friday", or "sunday"
    """
    print(f"\n{'='*80}")
    print(f"BATCH INJURY DETECTION - Week {week} - {pass_name.upper()} PASS")
    print(f"{'='*80}\n")
    
    # Load current week's games
    artifacts = Path("artifacts")
    csvs = sorted(artifacts.glob(f"predictions_{season}_*.csv"))
    current_week_files = [f for f in csvs if '_week' not in f.name]
    latest = current_week_files[-1] if current_week_files else csvs[-1]
    
    df = pd.read_csv(latest)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    detection_time = datetime.now(timezone.utc).isoformat()
    total_games = len(df)
    processed = 0
    
    for idx, row in df.iterrows():
        away = row['away']
        home = row['home']
        
        print(f"\n[{idx+1}/{total_games}] {away} @ {home}")
        print(f"  🔍 Detecting injuries via OpenAI...")
        
        try:
            # Detect injuries
            injuries = detect_injuries_openai(away, home)
            injury_impacts = calculate_injury_impact(injuries)
            
            # Store in database
            injuries_json = json.dumps([
                {
                    'team': inj.team,
                    'player': inj.player_name,
                    'position': inj.position,
                    'status': inj.status,
                    'injury_type': inj.injury_type,
                    'impact_level': inj.impact_level
                }
                for inj in injuries
            ])
            
            cursor.execute("""
                INSERT OR REPLACE INTO injury_reports 
                (week, season, away_team, home_team, detection_time, injuries_json, away_impact, home_impact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                week, season, away, home, detection_time, injuries_json,
                injury_impacts.get(away, 0.0),
                injury_impacts.get(home, 0.0)
            ))
            
            print(f"  ✅ Found {len(injuries)} injuries")
            print(f"     {away} impact: {injury_impacts.get(away, 0.0):.1f} pts")
            print(f"     {home} impact: {injury_impacts.get(home, 0.0):.1f} pts")
            
            processed += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"✅ Batch complete: {processed}/{total_games} games processed")
    print(f"💾 Cached to: {DB_PATH}")
    print(f"{'='*80}\n")


def get_cached_injuries(week: int, away: str, home: str, season: int = 2025) -> Dict:
    """
    Get cached injury data from database.
    
    Returns most recent detection for the game.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT injuries_json, away_impact, home_impact, detection_time
        FROM injury_reports
        WHERE week = ? AND season = ? AND away_team = ? AND home_team = ?
        ORDER BY detection_time DESC
        LIMIT 1
    """, (week, season, away, home))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        injuries_json, away_impact, home_impact, detection_time = row
        return {
            'injuries': json.loads(injuries_json),
            'away_impact': away_impact,
            'home_impact': home_impact,
            'detection_time': detection_time,
            'cached': True
        }
    
    return {
        'injuries': [],
        'away_impact': 0.0,
        'home_impact': 0.0,
        'detection_time': None,
        'cached': False
    }


def show_injury_summary(week: int, season: int = 2025):
    """Show summary of cached injuries for the week."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT away_team, home_team, away_impact, home_impact, detection_time
        FROM injury_reports
        WHERE week = ? AND season = ?
        ORDER BY detection_time DESC
    """, (week, season))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"No cached injuries for Week {week}")
        return
    
    print(f"\n{'='*80}")
    print(f"CACHED INJURIES - Week {week}")
    print(f"{'='*80}\n")
    
    for away, home, away_impact, home_impact, detection_time in rows:
        if away_impact != 0 or home_impact != 0:
            print(f"{away} @ {home}:")
            if away_impact != 0:
                print(f"  {away}: {away_impact:+.1f} pts")
            if home_impact != 0:
                print(f"  {home}: {home_impact:+.1f} pts")
            print(f"  Detected: {detection_time[:19]}")
            print()


if __name__ == "__main__":
    import sys
    
    # Initialize DB
    init_db()
    
    # Get arguments
    if len(sys.argv) < 2:
        print("Usage: python batch_injury_detection.py <command> [args]")
        print()
        print("Commands:")
        print("  detect <week> <pass_name>  - Batch detect injuries")
        print("  summary <week>             - Show cached injuries")
        print()
        print("Examples:")
        print("  python batch_injury_detection.py detect 9 wednesday")
        print("  python batch_injury_detection.py detect 9 friday")
        print("  python batch_injury_detection.py detect 9 sunday")
        print("  python batch_injury_detection.py summary 9")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "detect":
        if len(sys.argv) < 4:
            print("Usage: python batch_injury_detection.py detect <week> <pass_name>")
            sys.exit(1)
        
        week = int(sys.argv[2])
        pass_name = sys.argv[3]
        
        batch_detect_injuries(week, season=2025, pass_name=pass_name)
        show_injury_summary(week)
    
    elif command == "summary":
        if len(sys.argv) < 3:
            print("Usage: python batch_injury_detection.py summary <week>")
            sys.exit(1)
        
        week = int(sys.argv[2])
        show_injury_summary(week)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

