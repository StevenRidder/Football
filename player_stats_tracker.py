#!/usr/bin/env python3
"""
Player Stats Tracker - Track player props using ESPN API
Supports: Passing yards, Passing TDs, Rushing yards, Receiving yards, Receptions, etc.
"""

import requests
import re
from typing import Dict, Optional, List

class PlayerStatsTracker:
    """Track live player statistics for prop bets"""
    
    ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
    
    def __init__(self):
        self.game_cache = {}  # Cache game summaries to avoid repeated API calls
    
    def get_game_summary(self, game_id: str) -> Optional[Dict]:
        """Fetch detailed game summary including player stats"""
        if game_id in self.game_cache:
            return self.game_cache[game_id]
        
        try:
            response = requests.get(f"{self.ESPN_SUMMARY_URL}?event={game_id}", timeout=5)
            response.raise_for_status()
            data = response.json()
            self.game_cache[game_id] = data
            return data
        except Exception as e:
            print(f"Error fetching game summary for {game_id}: {e}")
            return None
    
    def get_player_stats(self, game_id: str, player_name: str) -> Optional[Dict]:
        """
        Get stats for a specific player in a game
        Returns: {
            'passing_yards': 228,
            'passing_tds': 2,
            'rushing_yards': 15,
            'receptions': 5,
            'receiving_yards': 67,
            'receiving_tds': 1
        }
        """
        summary = self.get_game_summary(game_id)
        if not summary:
            return None
        
        # Navigate to boxscore players
        boxscore = summary.get('boxscore', {})
        players = boxscore.get('players', [])
        
        # Normalize player name for matching
        player_name_normalized = player_name.lower().strip()
        
        for team_data in players:
            statistics = team_data.get('statistics', [])
            
            for stat_category in statistics:
                category_name = stat_category.get('name', '')
                athletes = stat_category.get('athletes', [])
                
                for athlete_data in athletes:
                    athlete = athlete_data.get('athlete', {})
                    athlete_name = athlete.get('displayName', '').lower()
                    
                    # Check if this is our player
                    if player_name_normalized in athlete_name or athlete_name in player_name_normalized:
                        stats = athlete_data.get('stats', [])
                        
                        # Parse stats based on category
                        if category_name == 'passing':
                            return self._parse_passing_stats(stats)
                        elif category_name == 'rushing':
                            return self._parse_rushing_stats(stats)
                        elif category_name == 'receiving':
                            return self._parse_receiving_stats(stats)
        
        return None
    
    def _parse_passing_stats(self, stats: List[str]) -> Dict:
        """Parse passing stats: [C/ATT, YDS, TD, INT, ...]"""
        result = {}
        try:
            if len(stats) >= 3:
                # stats[0] = "15/22" (completions/attempts)
                # stats[1] = "228" (yards)
                # stats[2] = "2" (TDs)
                result['passing_yards'] = float(stats[1]) if stats[1] else 0
                result['passing_tds'] = float(stats[2]) if stats[2] else 0
        except (ValueError, IndexError):
            pass
        return result
    
    def _parse_rushing_stats(self, stats: List[str]) -> Dict:
        """Parse rushing stats: [CAR, YDS, AVG, TD, LONG]"""
        result = {}
        try:
            if len(stats) >= 2:
                result['rushing_yards'] = float(stats[1]) if stats[1] else 0
                if len(stats) >= 4:
                    result['rushing_tds'] = float(stats[3]) if stats[3] else 0
        except (ValueError, IndexError):
            pass
        return result
    
    def _parse_receiving_stats(self, stats: List[str]) -> Dict:
        """Parse receiving stats: [REC, YDS, AVG, TD, LONG, TGTS]"""
        result = {}
        try:
            if len(stats) >= 2:
                result['receptions'] = float(stats[0]) if stats[0] else 0
                result['receiving_yards'] = float(stats[1]) if stats[1] else 0
                if len(stats) >= 4:
                    result['receiving_tds'] = float(stats[3]) if stats[3] else 0
        except (ValueError, IndexError):
            pass
        return result
    
    def check_prop_bet(self, game_id: str, prop_description: str) -> Optional[str]:
        """
        Check if a player prop bet is winning, losing, or neutral
        
        Examples:
        - "DJ 2+ Passing TDs thrown"
        - "DJ over 211.5 Passing yds"
        - "Travis Kelce over 65.5 Receiving yds"
        - "Josh Allen under 1.5 Passing TDs"
        
        Returns: 'winning', 'losing', 'neutral', or None (can't determine)
        """
        # Parse the prop description
        prop_info = self._parse_prop_description(prop_description)
        if not prop_info:
            return None
        
        player_name = prop_info['player']
        stat_type = prop_info['stat_type']
        threshold = prop_info['threshold']
        over_under = prop_info['over_under']
        
        # Get player stats
        stats = self.get_player_stats(game_id, player_name)
        if not stats:
            return None  # Player not found or game not started
        
        # Get the relevant stat
        current_value = stats.get(stat_type, 0)
        
        # Determine if winning/losing
        # Only consider it "neutral/push" if very close to the line (within 10%)
        margin = threshold * 0.1
        
        if over_under == 'over':
            if current_value > threshold:
                return 'winning'
            elif current_value >= threshold - margin:
                return 'neutral'  # Close to the line, could go either way
            else:
                return 'losing'  # Not close to hitting it
        else:  # under
            if current_value < threshold:
                return 'winning'
            elif current_value <= threshold + margin:
                return 'neutral'  # Close to the line
            else:
                return 'losing'  # Already over the threshold
    
    def _parse_prop_description(self, description: str) -> Optional[Dict]:
        """
        Parse prop bet description into structured data
        
        Examples:
        - "DJ 2+ Passing TDs thrown" → {player: "Daniel Jones", stat: "passing_tds", threshold: 2, over_under: "over"}
        - "DJ over 211.5 Passing yds" → {player: "Daniel Jones", stat: "passing_yards", threshold: 211.5, over_under: "over"}
        - "Player stats - Daniel Jones 2+ Passing TDs thrown (Game)" → BetOnline format
        """
        description_lower = description.lower()
        
        # Common player abbreviations
        player_abbrevs = {
            'dj': 'daniel jones',
            'tb12': 'tom brady',
            'pm': 'patrick mahomes',
            'ja': 'josh allen',
        }
        
        # Handle BetOnline format: "Player stats - Daniel Jones 2+ Passing TDs thrown (Game)"
        betonline_match = re.search(r'player stats - ([a-z\s]+?)\s+(\d+\+?|over|under)', description_lower)
        if betonline_match:
            player = betonline_match.group(1).strip()
        else:
            # Extract player name (first 1-3 words or abbreviation)
            player_match = re.match(r'^([A-Za-z\s]+?)\s+(?:over|under|\d)', description)
            if player_match:
                player = player_match.group(1).strip()
                # Check if it's an abbreviation
                if player.lower() in player_abbrevs:
                    player = player_abbrevs[player.lower()]
            else:
                return None
        
        # Determine stat type
        stat_type = None
        if 'passing td' in description_lower or 'pass td' in description_lower:
            stat_type = 'passing_tds'
        elif 'passing yd' in description_lower or 'pass yd' in description_lower:
            stat_type = 'passing_yards'
        elif 'rushing yd' in description_lower or 'rush yd' in description_lower:
            stat_type = 'rushing_yards'
        elif 'rushing td' in description_lower or 'rush td' in description_lower:
            stat_type = 'rushing_tds'
        elif 'receiving yd' in description_lower or 'rec yd' in description_lower:
            stat_type = 'receiving_yards'
        elif 'receiving td' in description_lower or 'rec td' in description_lower:
            stat_type = 'receiving_tds'
        elif 'reception' in description_lower or 'rec' in description_lower:
            stat_type = 'receptions'
        else:
            return None
        
        # Extract threshold and over/under
        over_under = 'over'
        if 'under' in description_lower:
            over_under = 'under'
        
        # Extract number (e.g., "2+", "211.5", "1.5")
        number_match = re.search(r'(\d+(?:\.\d+)?)\+?', description)
        if number_match:
            threshold = float(number_match.group(1))
        else:
            return None
        
        return {
            'player': player,
            'stat_type': stat_type,
            'threshold': threshold,
            'over_under': over_under
        }


def main():
    """Test the player stats tracker"""
    tracker = PlayerStatsTracker()
    
    # Example: Check Daniel Jones stats in a live game
    # You would get game_id from the live games API
    test_game_id = "401671760"  # Example game ID
    
    print("Testing player stats tracker...")
    print()
    
    # Test getting player stats
    stats = tracker.get_player_stats(test_game_id, "Daniel Jones")
    if stats:
        print(f"Daniel Jones stats: {stats}")
    else:
        print("Could not find Daniel Jones stats (game may not be live)")
    
    print()
    
    # Test checking prop bets
    test_props = [
        "DJ 2+ Passing TDs thrown",
        "DJ over 211.5 Passing yds",
    ]
    
    for prop in test_props:
        status = tracker.check_prop_bet(test_game_id, prop)
        print(f"{prop}: {status}")


if __name__ == '__main__':
    main()

