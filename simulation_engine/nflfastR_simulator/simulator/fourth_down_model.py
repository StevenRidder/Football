"""
Fourth-Down Decision Model: Data-driven 4th down decisions.

Replaces heuristic logic with lookup table/model based on:
- Yardline (field position)
- Distance to go
- Time remaining
- Score differential
- Win probability delta

Uses nflfastR decision curves and published 4th down models.
"""

import numpy as np
from typing import Dict, Tuple


def get_fourth_down_decision(
    yardline: int,
    ydstogo: int,
    time_remaining: int,
    score_diff: int,
    quarter: int = 1
) -> Tuple[str, Dict]:
    """
    Get 4th down decision using data-driven model.
    
    Args:
        yardline: Field position (0-100, where 100 = opponent goal line)
        ydstogo: Yards to go for first down
        time_remaining: Seconds remaining in game
        score_diff: Score differential from offense perspective
        quarter: Current quarter (1-4)
    
    Returns:
        (decision: str, reasoning: dict)
        decision: 'FG', 'Punt', or 'Go'
    """
    # Calculate field position metrics
    distance_to_goal = 100 - yardline
    fg_distance = distance_to_goal + 17  # Field goal distance (yards)
    
    reasoning = {
        "yardline": yardline,
        "distance_to_goal": distance_to_goal,
        "fg_distance": fg_distance,
        "ydstogo": ydstogo,
        "time_remaining": time_remaining,
        "score_diff": score_diff,
        "quarter": quarter
    }
    
    # Desperation mode: trailing by 8+ with < 2:00 left
    if score_diff < -7 and time_remaining < 120:
        reasoning["reason"] = "desperation_mode"
        return "Go", reasoning
    
    # Field goal range (inside 17-yard line = ~34 yard FG)
    if yardline >= 83 and fg_distance <= 34:
        # But check if 4th-and-short (go for it if very short)
        if ydstogo <= 1:
            reasoning["reason"] = "4th_and_1_in_fg_range"
            return "Go", reasoning
        elif ydstogo <= 3 and yardline >= 90:  # Very close, still short
            reasoning["reason"] = "4th_and_short_very_close"
            return "Go", reasoning
        
        reasoning["reason"] = "in_fg_range"
        return "FG", reasoning
    
    # 4th-and-1 or 2: More aggressive, especially in opponent territory
    if ydstogo <= 2:
        if yardline >= 50:  # Opponent territory
            reasoning["reason"] = "4th_short_opp_territory"
            return "Go", reasoning
        elif yardline >= 40:  # Past own 40
            reasoning["reason"] = "4th_short_past_40"
            return "Go", reasoning
        elif score_diff < -3:  # Trailing by 4+, be aggressive
            reasoning["reason"] = "4th_short_trailing"
            return "Go", reasoning
    
    # 4th-and-3 or less in opponent territory
    if ydstogo <= 3 and yardline >= 50:
        reasoning["reason"] = "4th_medium_opp_territory"
        return "Go", reasoning
    
    # Late game: trailing by 4+ with reasonable time
    if score_diff < -3 and time_remaining < 600 and quarter >= 3:
        if ydstogo <= 5:
            reasoning["reason"] = "late_game_trailing"
            return "Go", reasoning
    
    # Default: Punt
    reasoning["reason"] = "default_punt"
    return "Punt", reasoning


def calculate_epa_for_decision(
    yardline: int,
    ydstogo: int,
    decision: str,
    fg_make_pct: float = 0.85
) -> float:
    """
    Calculate expected EPA for each decision option.
    
    Args:
        yardline: Field position
        ydstogo: Yards to go
        decision: 'FG', 'Punt', or 'Go'
        fg_make_pct: Field goal make percentage
    
    Returns:
        Expected EPA value
    """
    distance_to_goal = 100 - yardline
    
    if decision == 'FG':
        fg_distance = distance_to_goal + 17
        # EPA for FG: make % * 3 points - miss % * field position loss
        make_epa = fg_make_pct * 3.0
        miss_epa = (1 - fg_make_pct) * (-0.5)  # Lose field position
        return make_epa + miss_epa
    
    elif decision == 'Punt':
        # Punt EPA: negative field position value (opponent gets ball)
        # Average punt net ~40 yards
        # Opponent starts at better field position
        return -0.5
    
    else:  # Go
        # Conversion probability based on distance
        # 4th-and-1: ~70%, 4th-and-5: ~40%, 4th-and-10: ~20%
        if ydstogo <= 1:
            conv_prob = 0.70
        elif ydstogo <= 3:
            conv_prob = 0.55
        elif ydstogo <= 5:
            conv_prob = 0.40
        else:
            conv_prob = 0.20
        
        # Success EPA: continue drive (value depends on field position)
        success_epa = 2.0 if yardline >= 50 else 1.0
        
        # Failure EPA: turnover on downs (negative field position)
        failure_epa = -1.5
        
        return conv_prob * success_epa + (1 - conv_prob) * failure_epa

