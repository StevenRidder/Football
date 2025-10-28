"""
Line Movement Tracker
Persists odds data over time to track line movements
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class LineTracker:
    def __init__(self, db_path: str = "data/line_movements.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                away_team TEXT NOT NULL,
                home_team TEXT NOT NULL,
                spread REAL,
                total REAL,
                away_ml INTEGER,
                home_ml INTEGER,
                source TEXT DEFAULT 'odds_api',
                UNIQUE(timestamp, away_team, home_team)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_game 
            ON line_movements(season, week, away_team, home_team)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON line_movements(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def record_lines(self, season: int, week: int, games: List[Dict]):
        """
        Record current lines for multiple games
        
        Args:
            season: NFL season year
            week: Week number
            games: List of dicts with keys: away, home, spread, total, away_ml, home_ml
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        for game in games:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO line_movements 
                    (timestamp, season, week, away_team, home_team, spread, total, away_ml, home_ml)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    season,
                    week,
                    game['away'],
                    game['home'],
                    game.get('spread'),
                    game.get('total'),
                    game.get('away_ml'),
                    game.get('home_ml')
                ))
            except Exception as e:
                print(f"Error recording line for {game['away']} @ {game['home']}: {e}")
        
        conn.commit()
        conn.close()
    
    def get_line_history(self, away: str, home: str, season: int, week: int) -> List[Dict]:
        """Get all recorded lines for a specific game"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, spread, total, away_ml, home_ml
            FROM line_movements
            WHERE season = ? AND week = ? AND away_team = ? AND home_team = ?
            ORDER BY timestamp ASC
        """, (season, week, away, home))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'spread': row[1],
                'total': row[2],
                'away_ml': row[3],
                'home_ml': row[4]
            }
            for row in rows
        ]
    
    def get_week_movements(self, season: int, week: int) -> Dict[str, List[Dict]]:
        """Get line movements for all games in a week"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT away_team, home_team, timestamp, spread, total, away_ml, home_ml
            FROM line_movements
            WHERE season = ? AND week = ?
            ORDER BY away_team, home_team, timestamp ASC
        """, (season, week))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Group by game
        games = {}
        for row in rows:
            game_key = f"{row[0]}@{row[1]}"
            if game_key not in games:
                games[game_key] = {
                    'away': row[0],
                    'home': row[1],
                    'movements': []
                }
            
            games[game_key]['movements'].append({
                'timestamp': row[2],
                'spread': row[3],
                'total': row[4],
                'away_ml': row[5],
                'home_ml': row[6]
            })
        
        return games
    
    def get_latest_lines(self, season: int, week: int) -> Dict[str, Dict]:
        """Get the most recent lines for all games in a week"""
        movements = self.get_week_movements(season, week)
        
        latest = {}
        for game_key, data in movements.items():
            if data['movements']:
                latest[game_key] = {
                    'away': data['away'],
                    'home': data['home'],
                    **data['movements'][-1]  # Most recent
                }
        
        return latest

