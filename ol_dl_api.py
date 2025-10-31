"""
Flask API endpoints for OL/DL continuity and matchup stress features.

All data is pre-computed and cached in CSV files for fast access (<10ms).
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Paths
FEATURES_DIR = Path("data/features")

# In-memory cache (loaded once at startup)
_OL_CONTINUITY_CACHE: Optional[pd.DataFrame] = None
_DL_PRESSURE_CACHE: Optional[pd.DataFrame] = None
_MATCHUP_STRESS_CACHE: Optional[pd.DataFrame] = None

def load_caches():
    """Load all feature CSVs into memory once at startup."""
    global _OL_CONTINUITY_CACHE, _DL_PRESSURE_CACHE, _MATCHUP_STRESS_CACHE
    
    print("📂 Loading OL/DL feature caches...")
    
    ol_file = FEATURES_DIR / "ol_continuity_2022_2025.csv"
    dl_file = FEATURES_DIR / "dl_pressure_2022_2025.csv"
    stress_file = FEATURES_DIR / "matchup_stress_2022_2025.csv"
    
    if ol_file.exists():
        _OL_CONTINUITY_CACHE = pd.read_csv(ol_file)
        print(f"  ✅ OL continuity: {len(_OL_CONTINUITY_CACHE):,} rows")
    else:
        print(f"  ❌ OL continuity not found: {ol_file}")
    
    if dl_file.exists():
        _DL_PRESSURE_CACHE = pd.read_csv(dl_file)
        print(f"  ✅ DL pressure: {len(_DL_PRESSURE_CACHE):,} rows")
    else:
        print(f"  ❌ DL pressure not found: {dl_file}")
    
    if stress_file.exists():
        _MATCHUP_STRESS_CACHE = pd.read_csv(stress_file)
        print(f"  ✅ Matchup stress: {len(_MATCHUP_STRESS_CACHE):,} rows")
    else:
        print(f"  ❌ Matchup stress not found: {stress_file}")

def get_ol_continuity(team: str, week: int, season: int = 2025) -> Optional[Dict]:
    """
    Get OL continuity features for a team in a given week.
    
    Returns:
        {
            'team': str,
            'week': int,
            'season': int,
            'ol_continuity_full': int (0 or 1),
            'ol_continuity_count': int (0-5),
            'ol_position_shifts': int,
            'ol_snaps_together_last3': float,
            'center_missing': int (0 or 1),
            'left_tackle_missing': int (0 or 1)
        }
    """
    if _OL_CONTINUITY_CACHE is None:
        return None
    
    result = _OL_CONTINUITY_CACHE[
        (_OL_CONTINUITY_CACHE['team'] == team) &
        (_OL_CONTINUITY_CACHE['week'] == week) &
        (_OL_CONTINUITY_CACHE['season'] == season)
    ]
    
    if len(result) == 0:
        return None
    
    return result.iloc[0].to_dict()

def get_dl_pressure(team: str, week: int, season: int = 2025) -> Optional[Dict]:
    """
    Get DL pressure features for a team in a given week.
    
    Returns:
        {
            'team': str,
            'week': int,
            'season': int,
            'dl_pressure_rate': float,
            'dl_continuity_same4': int (0 or 1),
            'total_dropbacks': int,
            'total_pressures': int
        }
    """
    if _DL_PRESSURE_CACHE is None:
        return None
    
    result = _DL_PRESSURE_CACHE[
        (_DL_PRESSURE_CACHE['team'] == team) &
        (_DL_PRESSURE_CACHE['week'] == week) &
        (_DL_PRESSURE_CACHE['season'] == season)
    ]
    
    if len(result) == 0:
        return None
    
    return result.iloc[0].to_dict()

def get_matchup_stress(away: str, home: str, week: int, season: int = 2025) -> Optional[Dict]:
    """
    Get matchup stress for a specific game.
    
    Returns:
        {
            'game_id': str,
            'season': int,
            'week': int,
            'away': str,
            'home': str,
            'ol_pass_stress_away': float,
            'ol_pass_stress_home': float,
            'ol_chaos_index_away': float,
            'ol_chaos_index_home': float,
            'stress_diff': float,
            'stress_z_score': float,
            'away_ol_continuity_full': int,
            'home_ol_continuity_full': int,
            'away_ol_continuity_count': int,
            'home_ol_continuity_count': int,
            'away_center_missing': int,
            'home_center_missing': int,
            'away_left_tackle_missing': int,
            'home_left_tackle_missing': int
        }
    """
    if _MATCHUP_STRESS_CACHE is None:
        return None
    
    result = _MATCHUP_STRESS_CACHE[
        (_MATCHUP_STRESS_CACHE['away'] == away) &
        (_MATCHUP_STRESS_CACHE['home'] == home) &
        (_MATCHUP_STRESS_CACHE['week'] == week) &
        (_MATCHUP_STRESS_CACHE['season'] == season)
    ]
    
    if len(result) == 0:
        return None
    
    return result.iloc[0].to_dict()

def get_high_stress_games(week: int, season: int = 2025, threshold: float = 1.5) -> List[Dict]:
    """
    Get all games in a week with high OL/DL stress (|z| > threshold).
    
    Args:
        week: Week number
        season: Season year
        threshold: Z-score threshold (default 1.5)
    
    Returns:
        List of games sorted by absolute stress_z_score (descending)
    """
    if _MATCHUP_STRESS_CACHE is None:
        return []
    
    week_games = _MATCHUP_STRESS_CACHE[
        (_MATCHUP_STRESS_CACHE['week'] == week) &
        (_MATCHUP_STRESS_CACHE['season'] == season)
    ].copy()
    
    if len(week_games) == 0:
        return []
    
    # Filter to high stress
    week_games['abs_stress_z'] = week_games['stress_z_score'].abs()
    high_stress = week_games[week_games['abs_stress_z'] >= threshold]
    
    # Sort by absolute z-score
    high_stress = high_stress.sort_values('abs_stress_z', ascending=False)
    
    return high_stress.to_dict('records')

def get_betting_signals(week: int, season: int = 2025) -> List[Dict]:
    """
    Get betting signals for a week based on OL/DL stress.
    
    Betting rule:
    - Only bet if stress_z_score > 1.5 (extreme mismatch)
    - Bet the AWAY team if z > 1.5 (away OL stressed, home DL advantage)
    - Bet the HOME team if z < -1.5 (home OL stressed, away DL advantage)
    
    Returns:
        List of betting signals with recommended side and edge explanation
    """
    high_stress = get_high_stress_games(week, season, threshold=1.5)
    
    signals = []
    
    for game in high_stress:
        z = game['stress_z_score']
        
        if z > 1.5:
            # Away OL stressed, home DL advantage → Bet HOME
            signals.append({
                'game_id': game['game_id'],
                'away': game['away'],
                'home': game['home'],
                'week': week,
                'season': season,
                'bet_side': 'HOME',
                'bet_team': game['home'],
                'stress_z_score': z,
                'edge_type': 'OL_STRESS',
                'explanation': f"{game['away']} OL stressed (chaos={game['ol_chaos_index_away']:.1f}, pass_stress={game['ol_pass_stress_away']:+.3f}). {game['home']} DL advantage.",
                'away_ol_continuity': game['away_ol_continuity_count'],
                'home_ol_continuity': game['home_ol_continuity_count'],
                'away_center_missing': game['away_center_missing'],
                'home_center_missing': game['home_center_missing'],
            })
        elif z < -1.5:
            # Home OL stressed, away DL advantage → Bet AWAY
            signals.append({
                'game_id': game['game_id'],
                'away': game['away'],
                'home': game['home'],
                'week': week,
                'season': season,
                'bet_side': 'AWAY',
                'bet_team': game['away'],
                'stress_z_score': z,
                'edge_type': 'OL_STRESS',
                'explanation': f"{game['home']} OL stressed (chaos={game['ol_chaos_index_home']:.1f}, pass_stress={game['ol_pass_stress_home']:+.3f}). {game['away']} DL advantage.",
                'away_ol_continuity': game['away_ol_continuity_count'],
                'home_ol_continuity': game['home_ol_continuity_count'],
                'away_center_missing': game['away_center_missing'],
                'home_center_missing': game['home_center_missing'],
            })
    
    return signals

# Load caches on module import
load_caches()

