"""
Parse parlay bet descriptions into structured leg data
"""
import re
from typing import List, Dict, Any, Optional


class ParlayLegParser:
    """Parse parlay leg descriptions from various formats"""
    
    @staticmethod
    def parse_legs(description: str, bet_type: str) -> List[Dict[str, Any]]:
        """
        Parse parlay legs from bet description.
        Returns list of leg dictionaries with: description, team, line, odds
        """
        # Only parse if it's a parlay
        if 'parlay' not in bet_type.lower():
            return []
        
        desc_upper = description.upper()
        
        # Format 1: BetOnline format with "Football - NFL -" repeated for each leg
        # Example: "Football - NFL - Team1 vs Team2 - Parlay | 451 Team1 -2½ -115 For Game | DATE | TIMEFootball - NFL - Team3 vs Team4..."
        # Must check this FIRST before generic pipe-separated, as this format also contains pipes
        if 'FOOTBALL - NFL -' in desc_upper and 'FOR GAME' in desc_upper:
            return ParlayLegParser._parse_betonline_format(description)
        
        # Format 2: Simple pipe-separated format
        # "FOOTBALL - NFL - Kansas City Chiefs v Washington Commanders | Player stats - P. Mahomes over 227.5 Passing yds (Game) | Spread - Commanders +11.5 (Game)"
        if ' | ' in description:
            return ParlayLegParser._parse_pipe_separated(description)
        
        # Format 3: Newline-separated format
        # "FOOTBALL - NFL - Kansas City Chiefs v Washington Commanders\n\nPlayer TDs - P. Mahomes Score anytime (Game)\nSpread - Commanders +11.5 (Game)"
        if '\n' in description and ('FOOTBALL - NFL -' in desc_upper):
            return ParlayLegParser._parse_newline_separated(description)
        
        # Format 4: Comma-separated short format
        # "12-team parlay: CAR +7, NYG +7.5, MIA +7.5"
        if 'parlay:' in description.lower():
            return ParlayLegParser._parse_comma_separated(description)
        
        return []
    
    @staticmethod
    def _parse_pipe_separated(description: str) -> List[Dict[str, Any]]:
        """Parse pipe-separated format"""
        legs = []
        parts = description.split(' | ')
        
        for part in parts:
            part_upper = part.upper()
            
            # Skip the game header
            if 'FOOTBALL - NFL -' in part_upper:
                continue
            
            # Check if it's a valid leg
            if any(keyword in part_upper for keyword in [
                'MONEY LINE -', 'PLAYER STATS -', 'SPREAD -', 
                'TOTAL POINTS -', 'PLAYER TDS -'
            ]):
                leg = ParlayLegParser._parse_single_leg(part.strip())
                if leg:
                    legs.append(leg)
        
        return legs
    
    @staticmethod
    def _parse_newline_separated(description: str) -> List[Dict[str, Any]]:
        """Parse newline-separated format"""
        legs = []
        lines = description.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_upper = line.upper()
            
            # Skip the game header
            if 'FOOTBALL - NFL -' in line_upper:
                continue
            
            # Check if it's a valid leg
            if any(keyword in line_upper for keyword in [
                'MONEY LINE -', 'PLAYER STATS -', 'SPREAD -', 
                'TOTAL POINTS -', 'PLAYER TDS -'
            ]):
                leg = ParlayLegParser._parse_single_leg(line)
                if leg:
                    legs.append(leg)
        
        return legs
    
    @staticmethod
    def _parse_comma_separated(description: str) -> List[Dict[str, Any]]:
        """Parse comma-separated format: 'parlay: CAR +7, NYG +7.5, MIA +7.5'"""
        legs = []
        match = re.search(r'parlay:\s*(.+)', description, re.IGNORECASE)
        if match:
            legs_str = match.group(1)
            for leg_str in legs_str.split(','):
                leg_str = leg_str.strip()
                leg = ParlayLegParser._parse_single_leg(leg_str)
                if leg:
                    legs.append(leg)
        return legs
    
    @staticmethod
    def _parse_betonline_format(description: str) -> List[Dict[str, Any]]:
        """Parse old BetOnline format with 'Football - NFL -' separators"""
        legs = []
        
        # Split by "Football - NFL -" to separate each game's leg
        # Handle both clean splits and run-together text
        games = re.split(r'Football - NFL -', description, flags=re.IGNORECASE)
        
        for game in games:
            if not game.strip():
                continue
            
            # Try to extract bet line: "| NUMBER TEAM SPREAD ODDS For Game | DATE | TIME | STATUS"
            # Example: "| 451 Chicago Bears -2½ -115 For Game | 11/02/2025 | 01:00:00 PM (EST) | Pending"
            bet_match = re.search(
                r'\|\s*(\d+)\s+(.+?)\s+([-+]?\d+(?:½)?)\s+([-+]?\d+)\s+For\s+Game',
                game,
                re.IGNORECASE
            )
            if bet_match:
                game_num = bet_match.group(1)
                team_name = bet_match.group(2).strip()
                spread = bet_match.group(3)
                odds = bet_match.group(4)
                
                leg = {
                    'description': f"{team_name} {spread}",
                    'team_name': team_name,
                    'bet_type': 'Spread',
                    'line': spread,
                    'odds': odds,
                    'game_num': game_num
                }
                legs.append(leg)
        
        return legs
    
    @staticmethod
    def _parse_single_leg(leg_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single leg string into structured data.
        Examples:
          - "Player stats - P. Mahomes over 227.5 Passing yds (Game)"
          - "Spread - Commanders +11.5 (Game)"
          - "Total points - Under 48.5 (Game)"
          - "Money line - Chiefs (Game)"
          - "CAR +7"
        """
        leg_str = leg_str.strip()
        
        # Strip out status indicators (| Won, | Lost, | Pending, | Push)
        # These are added by BetOnline and should be removed before parsing
        leg_str = re.sub(r'\s*\|\s*(Won|Lost|Pending|Push)\s*$', '', leg_str, flags=re.IGNORECASE)
        
        leg_upper = leg_str.upper()
        
        # Player prop: "Player stats - P. Mahomes over 227.5 Passing yds (Game)"
        if 'PLAYER STATS -' in leg_upper or 'PLAYER TDS -' in leg_upper:
            # Extract player name and prop
            match = re.search(r'Player (?:stats|TDs) - (.+)', leg_str, re.IGNORECASE)
            if match:
                prop_desc = match.group(1).strip()
                # Extract player name (first part before over/under)
                player_match = re.search(r'^([A-Z]\.\s+[A-Za-z]+)', prop_desc)
                player = player_match.group(1) if player_match else None
                
                return {
                    'description': leg_str,
                    'team': player,  # Store player name in team field
                    'line': prop_desc,
                    'odds': None
                }
        
        # Spread: "Spread - Commanders +11.5 (Game)"
        elif 'SPREAD -' in leg_upper:
            match = re.search(r'Spread - ([A-Za-z\s]+)\s+([-+][\d.]+)', leg_str, re.IGNORECASE)
            if match:
                team = match.group(1).strip()
                line = match.group(2)
                return {
                    'description': leg_str,
                    'team': team,
                    'line': line,
                    'odds': None
                }
        
        # Total: "Total points - Under 48.5 (Game)"
        elif 'TOTAL POINTS -' in leg_upper:
            match = re.search(r'Total points - (Over|Under)\s+([\d.]+)', leg_str, re.IGNORECASE)
            if match:
                over_under = match.group(1)
                line = match.group(2)
                return {
                    'description': leg_str,
                    'team': None,  # Totals don't have a team
                    'line': f"{over_under} {line}",
                    'odds': None
                }
        
        # Moneyline: "Money line - Chiefs (Game)"
        elif 'MONEY LINE -' in leg_upper:
            match = re.search(r'Money line - ([A-Za-z\s]+)', leg_str, re.IGNORECASE)
            if match:
                team = match.group(1).strip().replace('(Game)', '').strip()
                return {
                    'description': leg_str,
                    'team': team,
                    'line': 'ML',
                    'odds': None
                }
        
        # Simple format: "CAR +7" or "MIA -3.5"
        elif re.match(r'^[A-Z]{2,4}\s+[-+][\d.]+', leg_str):
            match = re.match(r'^([A-Z]{2,4})\s+([-+][\d.]+)', leg_str)
            if match:
                team = match.group(1)
                line = match.group(2)
                return {
                    'description': leg_str,
                    'team': team,
                    'line': line,
                    'odds': None
                }
        
        # If we can't parse it, store the raw description
        return {
            'description': leg_str,
            'team': None,
            'line': None,
            'odds': None
        }

