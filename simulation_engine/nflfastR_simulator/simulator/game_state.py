"""
GameState: Tracks current game situation during simulation.

Per strategy doc:
- Down, distance, field position
- Score differential, time remaining
- Possession, timeouts
- Game flow tracking
"""

from dataclasses import dataclass
from typing import Literal, Dict, Tuple


@dataclass
class GameState:
    """Tracks the current state of the game during simulation."""
    
    # Game clock
    quarter: int = 1
    time_remaining: int = 900  # Seconds in current quarter
    
    # Field position
    possession: str = 'home'  # 'home' or 'away'
    down: int = 1
    ydstogo: int = 10
    yardline: int = 25  # 0-100 (0 = own goal line, 100 = opponent goal line)
    
    # Score
    home_score: int = 0
    away_score: int = 0
    
    # Timeouts
    home_timeouts: int = 3
    away_timeouts: int = 3
    
    # Drive tracking
    drive_number: int = 1
    plays_this_drive: int = 0
    
    # CALIBRATION: Track last play for persistence bias
    last_play_yards: int = 0
    
    def __post_init__(self):
        """Initialize derived properties."""
        self._validate_state()
    
    def _validate_state(self):
        """Ensure game state is valid."""
        assert self.quarter in [1, 2, 3, 4], f"Invalid quarter: {self.quarter}"
        assert 0 <= self.time_remaining <= 900, f"Invalid time: {self.time_remaining}"
        assert self.possession in ['home', 'away'], f"Invalid possession: {self.possession}"
        assert 1 <= self.down <= 4, f"Invalid down: {self.down}"
        assert 0 <= self.yardline <= 100, f"Invalid yardline: {self.yardline}"
    
    @property
    def score_differential(self) -> int:
        """Score differential from perspective of team with possession."""
        if self.possession == 'home':
            return self.home_score - self.away_score
        else:
            return self.away_score - self.home_score
    
    @property
    def game_seconds_remaining(self) -> int:
        """Total seconds remaining in game."""
        return (4 - self.quarter) * 900 + self.time_remaining
    
    @property
    def is_red_zone(self) -> bool:
        """Is offense in red zone (inside opponent 20)?"""
        return self.yardline >= 80
    
    @property
    def is_goal_to_go(self) -> bool:
        """Is it goal-to-go situation?"""
        return self.ydstogo >= self.yardline
    
    @property
    def field_position_bucket(self) -> str:
        """
        Bucket field position for drive probability lookup.
        
        Buckets (from offense perspective):
        - own_10: 0-10 yards (own 10 or worse)
        - own_20: 11-20 yards
        - own_35: 21-35 yards
        - midfield: 36-50 yards
        - opp_35: 51-65 yards
        - opp_20: 66-80 yards
        - opp_10: 81-100 yards (opponent 20 or better)
        """
        if self.yardline <= 10:
            return 'own_10'
        elif self.yardline <= 20:
            return 'own_20'
        elif self.yardline <= 35:
            return 'own_35'
        elif self.yardline <= 50:
            return 'midfield'
        elif self.yardline <= 65:
            return 'opp_35'
        elif self.yardline <= 80:
            return 'opp_20'
        else:
            return 'opp_10'
    
    @property
    def distance_bucket(self) -> str:
        """Bucket distance for play-calling lookup."""
        if self.ydstogo <= 3:
            return 'short'
        elif self.ydstogo <= 7:
            return 'medium'
        else:
            return 'long'
    
    @property
    def score_diff_bucket(self) -> str:
        """Bucket score differential for play-calling lookup."""
        diff = self.score_differential
        if diff <= -14:
            return 'down_14+'
        elif diff <= -7:
            return 'down_7-13'
        elif diff <= -1:
            return 'down_1-6'
        elif diff == 0:
            return 'tied'
        elif diff <= 6:
            return 'up_1-6'
        elif diff <= 13:
            return 'up_7-13'
        else:
            return 'up_14+'
    
    @property
    def time_bucket(self) -> str:
        """Bucket time remaining for play-calling lookup."""
        seconds = self.game_seconds_remaining
        if seconds < 120:
            return '2min'
        elif seconds < 900:
            return 'Q4_late'
        elif seconds < 1800:
            return 'Q3-Q4'
        elif seconds < 2700:
            return 'Q2-Q3'
        else:
            return 'Q1-Q2'
    
    def update_from_play(self, play_result: dict):
        """
        Update game state after a play.
        
        Args:
            play_result: Dict with keys:
                - type: 'completion', 'incomplete', 'sack', 'interception', 'run', 'scramble'
                - yards: Yards gained (negative for sacks)
                - td: True if touchdown
                - fumble: True if fumble lost
                - turnover: True if turnover (INT or fumble)
        """
        self.plays_this_drive += 1
        
        # Update yardline
        yards_gained = play_result.get('yards', 0)
        self.yardline = min(100, max(0, self.yardline + yards_gained))
        
        # CALIBRATION: Track yards for persistence bias
        self.last_play_yards = yards_gained
        
        # Check for touchdown
        if play_result.get('td', False):
            self.add_points(7, self.possession)
            self.switch_possession()
            self.start_new_drive()
            return
        
        # Check for turnover
        if play_result.get('turnover', False) or play_result.get('type') == 'interception':
            self.switch_possession()
            self.start_new_drive()
            return
        
        # Update down and distance
        if yards_gained >= self.ydstogo:
            # First down
            self.down = 1
            self.ydstogo = min(10, 100 - self.yardline)  # Goal-to-go if close
        else:
            # Advance down
            self.down += 1
            self.ydstogo -= yards_gained
            
            # Check for turnover on downs
            if self.down > 4:
                self.switch_possession()
                self.start_new_drive()
                return
        
        # FIXED: Clock advancement is now handled by GameSimulator
        # which passes time_per_play based on pace
        # This method is kept for backward compatibility but should not be called
        # The actual clock advancement happens in GameSimulator._simulate_drive
        pass
        
        # Check for end of quarter
        if self.time_remaining == 0:
            self.advance_quarter()
    
    def add_points(self, points: int, team: str):
        """Add points to a team's score."""
        if team == 'home':
            self.home_score += points
        else:
            self.away_score += points
    
    def switch_possession(self):
        """Switch possession to other team."""
        self.possession = 'away' if self.possession == 'home' else 'home'
        # Flip field position (new team starts from their own side)
        self.yardline = 100 - self.yardline
    
    def start_new_drive(self):
        """Start a new drive (after score or turnover)."""
        self.drive_number += 1
        self.plays_this_drive = 0
        self.down = 1
        self.ydstogo = 10
        # Kickoff: start at own 25 (touchback)
        self.yardline = 25
    
    def advance_quarter(self):
        """Advance to next quarter."""
        self.quarter += 1
        self.time_remaining = 900
        
        # Halftime: switch possession
        if self.quarter == 3:
            self.switch_possession()
    
    def is_game_over(self) -> bool:
        """Check if game is over."""
        return self.quarter > 4 or (self.quarter == 4 and self.time_remaining == 0)
    
    def should_punt(self) -> Tuple[bool, Dict]:
        """
        Decide if team should punt on 4th down.
        
        Uses fourth_down_model for data-driven decisions.
        
        Returns:
            (decision: bool, reasoning: dict)
            True = Punt, False = Go for it or FG
        """
        if self.down != 4:
            return False, {"reason": "not_4th_down", "down": self.down}
        
        try:
            from .fourth_down_model import get_fourth_down_decision
            decision, reasoning = get_fourth_down_decision(
                yardline=self.yardline,
                ydstogo=self.ydstogo,
                time_remaining=self.game_seconds_remaining,
                score_diff=self.score_differential,
                quarter=self.quarter
            )
            
            # Convert to boolean: Punt = True, Go/FG = False
            return decision == "Punt", reasoning
            
        except ImportError:
            # Fallback to old heuristic if model not available
            reasoning = {
                "yardline": self.yardline,
                "to_go": self.ydstogo,
                "score_diff": self.score_differential,
                "time_remaining": self.game_seconds_remaining,
                "reason": "heuristic_fallback"
            }
            
            if self.score_differential < -7 and self.game_seconds_remaining < 300:
                return False, reasoning
            if self.yardline >= 70:
                return False, reasoning
            if self.yardline >= 50 and self.ydstogo <= 3:
                return False, reasoning
            if self.yardline >= 40 and self.ydstogo <= 1:
                return False, reasoning
            return True, reasoning
    
    def should_attempt_fg(self) -> Tuple[bool, Dict]:
        """
        Decide if team should attempt field goal on 4th down.
        
        Uses fourth_down_model for data-driven decisions.
        
        Returns:
            (decision: bool, reasoning: dict)
            True = Attempt FG, False = Go for it or Punt
        """
        if self.down != 4:
            return False, {"reason": "not_4th_down", "down": self.down}
        
        try:
            from .fourth_down_model import get_fourth_down_decision
            decision, reasoning = get_fourth_down_decision(
                yardline=self.yardline,
                ydstogo=self.ydstogo,
                time_remaining=self.game_seconds_remaining,
                score_diff=self.score_differential,
                quarter=self.quarter
            )
            
            # Convert to boolean: FG = True, Go/Punt = False
            return decision == "FG", reasoning
            
        except ImportError:
            # Fallback to old heuristic
            distance_to_goal = 100 - self.yardline
            reasoning = {
                "yardline": self.yardline,
                "distance_to_goal": distance_to_goal,
                "to_go": self.ydstogo,
                "reason": "heuristic_fallback"
            }
            decision = self.yardline >= 83 and distance_to_goal <= 17 and self.ydstogo > 3
            return decision, reasoning
    
    def __repr__(self):
        """String representation of game state."""
        return (f"Q{self.quarter} {self.time_remaining//60}:{self.time_remaining%60:02d} | "
                f"{self.possession.upper()} ball | "
                f"{self.down}{['st','nd','rd','th'][self.down-1]} & {self.ydstogo} at {100-self.yardline} | "
                f"Score: {self.home_score}-{self.away_score}")

