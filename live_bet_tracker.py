#!/usr/bin/env python3
"""
Live Bet Tracker - Colors bets based on real-time game status
Uses ESPN API for live scores (no auth required)
"""

import requests
import time
from datetime import datetime
from nfl_edge.bets.db import BettingDB

class LiveBetTracker:
    """Track live game status and determine bet status"""
    
    ESPN_SCOREBOARD_URLS = {
        'NFL': 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard',
        'NCAAF': 'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard',
        'NBA': 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
        'NCAAB': 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard',
        'MLB': 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard',
        'NHL': 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard',
    }
    
    def __init__(self):
        self.db = BettingDB()
        self.live_games = {}
    
    def get_pending_bets(self):
        """Get all pending bets from database"""
        pending = self.db.get_pending_bets()
        
        bets = []
        for bet in pending:
            bet_dict = dict(bet)
            bets.append({
                'ticket_number': bet_dict.get('ticket_number'),
                'description': bet_dict.get('description', ''),
                'bet_type': bet_dict.get('type', ''),
                'date': bet_dict.get('date'),
                'amount': bet_dict.get('amount', 0),
                'to_win': bet_dict.get('to_win', 0),
                'team': self._extract_team(bet_dict.get('description', '')),
                'line': self._extract_line(bet_dict.get('description', ''))
            })
        
        return bets
    
    def _extract_team(self, description):
        """Extract team name from bet description"""
        # Simple extraction - improve based on actual format
        if ' @ ' in description:
            parts = description.split(' @ ')
            return parts[0].strip() if len(parts) > 0 else ''
        return ''
    
    def _extract_line(self, description):
        """Extract line/spread from bet description"""
        # Look for numbers with +/- signs
        import re
        match = re.search(r'([+-]?\d+\.?\d*)', description)
        return float(match.group(1)) if match else 0.0
    
    def get_live_games(self, sport='NFL'):
        """Fetch live games from ESPN API"""
        url = self.ESPN_SCOREBOARD_URLS.get(sport.upper())
        if not url:
            return []
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            games = []
            for event in data.get('events', []):
                competition = event.get('competitions', [{}])[0]
                status = competition.get('status', {})
                
                # Only include live or recently completed games
                if status.get('type', {}).get('state') in ['in', 'post']:
                    game_info = self._parse_game(event, competition, status)
                    if game_info:
                        games.append(game_info)
            
            return games
        except Exception as e:
            print(f"Error fetching {sport} scores: {e}")
            return []
    
    def _parse_game(self, event, competition, status):
        """Parse game data from ESPN response"""
        competitors = competition.get('competitors', [])
        if len(competitors) < 2:
            return None
        
        home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
        away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
        
        return {
            'id': event.get('id'),
            'name': event.get('name'),
            'home_team': home.get('team', {}).get('displayName'),
            'away_team': away.get('team', {}).get('displayName'),
            'home_score': int(home.get('score', 0)),
            'away_score': int(away.get('score', 0)),
            'status': status.get('type', {}).get('state'),  # 'in' or 'post'
            'period': status.get('period', 0),
            'clock': status.get('displayClock', ''),
            'is_live': status.get('type', {}).get('state') == 'in',
        }
    
    def get_bet_status(self, bet, game):
        """
        Determine if bet is winning, losing, or neutral
        Returns: 'winning', 'losing', 'neutral', or None (not live)
        """
        if not game or not game['is_live']:
            return None
        
        bet_type = bet.get('bet_type', '').lower()
        team = bet.get('team', '')
        
        # Determine which team the bet is on
        is_home = team == game['home_team']
        is_away = team == game['away_team']
        
        if not (is_home or is_away):
            return None
        
        home_score = game['home_score']
        away_score = game['away_score']
        
        # Handle different bet types
        if 'spread' in bet_type or 'point spread' in bet_type:
            spread = float(bet.get('line', 0))
            
            if is_home:
                current_diff = home_score - away_score
                if current_diff > spread:
                    return 'winning'
                elif current_diff < spread:
                    return 'losing'
            else:  # away team
                current_diff = away_score - home_score
                if current_diff > abs(spread):
                    return 'winning'
                elif current_diff < abs(spread):
                    return 'losing'
        
        elif 'moneyline' in bet_type or 'ml' in bet_type:
            if is_home:
                if home_score > away_score:
                    return 'winning'
                elif home_score < away_score:
                    return 'losing'
            else:  # away team
                if away_score > home_score:
                    return 'winning'
                elif away_score < home_score:
                    return 'losing'
        
        elif 'over' in bet_type or 'under' in bet_type:
            total = float(bet.get('line', 0))
            current_total = home_score + away_score
            
            if 'over' in bet_type:
                if current_total > total:
                    return 'winning'
                elif current_total < total * 0.8:  # Likely to stay under
                    return 'losing'
            else:  # under
                if current_total < total:
                    return 'winning'
                elif current_total > total * 0.8:  # Likely to go over
                    return 'losing'
        
        return 'neutral'
    
    def update_all_bets(self):
        """Update status for all pending bets"""
        # Fetch live games for all sports
        all_games = []
        for sport in self.ESPN_SCOREBOARD_URLS.keys():
            games = self.get_live_games(sport)
            all_games.extend(games)
            time.sleep(0.5)  # Rate limiting
        
        # Get all pending bets
        pending_bets = self.get_pending_bets()
        
        # Match bets to games and determine status
        bet_statuses = []
        for bet in pending_bets:
            status = None
            matched_game = None
            
            # Try to match bet to a live game
            for game in all_games:
                if (bet.get('team') in [game['home_team'], game['away_team']] or
                    bet.get('opponent') in [game['home_team'], game['away_team']]):
                    matched_game = game
                    status = self.get_bet_status(bet, game)
                    break
            
            bet_statuses.append({
                'ticket_number': bet['ticket_number'],
                'live_status': status,
                'game_info': matched_game
            })
        
        return bet_statuses
    
    def get_status_color(self, status):
        """Get Tabler color class for status"""
        if status == 'winning':
            return 'success'  # Green
        elif status == 'losing':
            return 'danger'   # Red
        elif status == 'neutral':
            return 'warning'  # Yellow
        else:
            return None  # Default (white)

def main():
    """Test the live tracker"""
    tracker = LiveBetTracker()
    
    print("Fetching live games...")
    statuses = tracker.update_all_bets()
    
    print(f"\nFound {len(statuses)} bets")
    
    live_count = sum(1 for s in statuses if s['live_status'])
    print(f"Live bets: {live_count}")
    
    for bet_status in statuses:
        if bet_status['live_status']:
            print(f"\nTicket: {bet_status['ticket_number']}")
            print(f"Status: {bet_status['live_status']}")
            if bet_status['game_info']:
                game = bet_status['game_info']
                print(f"Game: {game['away_team']} @ {game['home_team']}")
                print(f"Score: {game['away_score']} - {game['home_score']}")
                print(f"Clock: {game['clock']} (Period {game['period']})")

if __name__ == '__main__':
    main()

