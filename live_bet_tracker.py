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
            description = bet_dict.get('description', '')
            bets.append({
                'ticket_number': bet_dict.get('ticket_id'),  # Changed from ticket_number to ticket_id
                'description': description,
                'bet_type': bet_dict.get('bet_type', ''),  # Changed from type to bet_type
                'date': bet_dict.get('date'),
                'amount': bet_dict.get('amount', 0),
                'to_win': bet_dict.get('to_win', 0),
                'team': self._extract_team(description),
                'teams': self._extract_teams(description),  # All teams involved (for totals)
                'line': self._extract_line(description)
            })
        
        return bets
    
    def _extract_teams(self, description):
        """Extract team names from bet description (returns list of teams)"""
        import re
        
        # For totals: "Green Bay Packers/Pittsburgh Steelers over 46"
        if '/' in description and ('over' in description.lower() or 'under' in description.lower()):
            match = re.search(r'([A-Za-z\s]+)/([A-Za-z\s]+)\s+(over|under)', description, re.IGNORECASE)
            if match:
                team1 = match.group(1).strip()
                team2 = match.group(2).strip()
                return [team1, team2]
        
        # Try format: "Team1 @ Team2"
        if ' @ ' in description:
            parts = description.split(' @ ')
            if len(parts) >= 2:
                return [parts[0].strip(), parts[1].split()[0].strip()]
        
        # Try format: "FOOTBALL - 279 Dallas Cowboys +3½ -118"
        # Remove the number prefix first
        desc_clean = re.sub(r'FOOTBALL\s*-\s*\d+\s+', '', description)
        
        # Try format: "Indianapolis Colts -15" or "New England Patriots +7" or "Dallas Cowboys +3½"
        # Look for team name followed by +/- and number
        match = re.search(r'([A-Za-z\s]+?)\s+([+-]\d+(?:½)?)', desc_clean)
        if match:
            team = match.group(1).strip()
            # Remove any trailing numbers
            team = re.sub(r'\d+$', '', team).strip()
            return [team]
        
        # Try format: "FOOTBALL - NFL - Team1 v Team2"
        if ' v ' in description or ' vs ' in description:
            parts = re.split(r'\s+v\s+|\s+vs\s+', description)
            if len(parts) >= 2:
                # Extract just the team names, removing "FOOTBALL - NFL -" prefix
                team = parts[0].split(' - ')[-1].strip()
                return [team]
        
        return []
    
    def _extract_team(self, description):
        """Extract primary team name (for backward compatibility)"""
        teams = self._extract_teams(description)
        return teams[0] if teams else ''
    
    def _extract_line(self, description):
        """Extract line/spread from bet description"""
        # Look for numbers with +/- signs (but not the bet number at the start)
        import re
        
        # Remove "FOOTBALL - 279" style prefixes
        desc_clean = re.sub(r'FOOTBALL\s*-\s*\d+\s+', '', description)
        
        # For totals: "over 46" or "under 47.5"
        if 'over' in description.lower() or 'under' in description.lower():
            match = re.search(r'(over|under)\s+(\d+(?:\.5)?)', description, re.IGNORECASE)
            if match:
                return float(match.group(2))
        
        # Look for spread like "+3½" or "-7"
        match = re.search(r'([+-]\d+(?:½|\.5)?)', desc_clean)
        if match:
            line_str = match.group(1).replace('½', '.5')
            return float(line_str)
        
        return 0.0
    
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
        # Team name to abbreviation mapping
        TEAM_MAP = {
            'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
            'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'
        }
        
        competitors = competition.get('competitors', [])
        if len(competitors) < 2:
            return None
        
        home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
        away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
        
        home_team_name = home.get('team', {}).get('displayName')
        away_team_name = away.get('team', {}).get('displayName')
        
        return {
            'id': event.get('id'),
            'name': event.get('name'),
            'home_team': home_team_name,
            'away_team': away_team_name,
            'home_abbr': TEAM_MAP.get(home_team_name, home_team_name),
            'away_abbr': TEAM_MAP.get(away_team_name, away_team_name),
            'home_score': int(home.get('score', 0)),
            'away_score': int(away.get('score', 0)),
            'status': status.get('type', {}).get('shortDetail', ''),
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
        description = bet.get('description', '').lower()
        team = bet.get('team', '')
        
        home_score = game['home_score']
        away_score = game['away_score']
        
        # Handle totals (over/under) - don't need team match
        if 'total' in bet_type or 'over' in description or 'under' in description:
            total = float(bet.get('line', 0))
            current_total = home_score + away_score
            
            if 'over' in description:
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
        
        # For spread/moneyline, we need team match
        # Determine which team the bet is on
        is_home = team == game['home_team']
        is_away = team == game['away_team']
        
        if not (is_home or is_away):
            return None
        
        # Handle different bet types
        if 'spread' in bet_type or 'point spread' in bet_type:
            spread = float(bet.get('line', 0))
            
            if is_home:
                # For home team: add spread to their score
                # e.g., IND -15: if IND wins by more than 15, they cover
                effective_diff = (home_score - away_score) + spread
                if effective_diff > 0:
                    return 'winning'
                elif effective_diff < 0:
                    return 'losing'
            else:  # away team
                # For away team: add spread to their score
                effective_diff = (away_score - home_score) + spread
                if effective_diff > 0:
                    return 'winning'
                elif effective_diff < 0:
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
                bet_teams = bet.get('teams', [])
                game_teams = [game['home_team'], game['away_team']]
                
                # For totals, check if any of the bet's teams match the game
                # For spread/ML, check if the primary team matches
                if bet_teams:
                    # Check if any bet team is in the game
                    if any(team in game_teams for team in bet_teams):
                        matched_game = game
                        status = self.get_bet_status(bet, game)
                        break
                elif bet.get('team') in game_teams:
                    # Fallback to single team match
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

