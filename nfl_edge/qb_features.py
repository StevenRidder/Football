"""
QB Features for Residual Model

Extracts quarterback-specific features:
- Starter vs backup flag
- Last 3 games EPA
- Pressure-to-sack rate
- Scramble rate
- Average depth of target (aDOT)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import nfl_data_py as nfl


def fetch_qb_stats(season: int = 2025) -> pd.DataFrame:
    """
    Fetch QB stats from nflverse.
    
    Args:
        season: NFL season year
    
    Returns:
        DataFrame with QB stats by team
    """
    try:
        # Fetch play-by-play data
        pbp = nfl.import_pbp_data([season], downcast=False)
        
        # Filter to passing plays
        passing = pbp[
            (pbp['play_type'] == 'pass') & 
            (pbp['passer_player_id'].notna())
        ].copy()
        
        # Calculate QB stats by team
        qb_stats = []
        
        for team in passing['posteam'].unique():
            team_passing = passing[passing['posteam'] == team]
            
            if len(team_passing) == 0:
                continue
            
            # Get primary QB (most dropbacks)
            qb_counts = team_passing['passer_player_name'].value_counts()
            if len(qb_counts) == 0:
                continue
            
            primary_qb = qb_counts.index[0]
            primary_qb_plays = team_passing[team_passing['passer_player_name'] == primary_qb]
            
            # Calculate stats
            stats = {
                'team': team,
                'qb_name': primary_qb,
                'qb_dropbacks': len(primary_qb_plays),
                'qb_epa': primary_qb_plays['qb_epa'].mean(),
                'qb_cpoe': primary_qb_plays['cpoe'].mean(),
                'qb_air_yards': primary_qb_plays['air_yards'].mean(),  # aDOT
                'qb_scrambles': (primary_qb_plays['qb_scramble'] == 1).sum(),
                'qb_scramble_rate': (primary_qb_plays['qb_scramble'] == 1).mean(),
                'qb_sacks': (primary_qb_plays['sack'] == 1).sum(),
                'qb_pressures': primary_qb_plays['qb_hit'].sum() + primary_qb_plays['sack'].sum(),
            }
            
            # Pressure-to-sack rate
            if stats['qb_pressures'] > 0:
                stats['qb_pressure_to_sack_rate'] = stats['qb_sacks'] / stats['qb_pressures']
            else:
                stats['qb_pressure_to_sack_rate'] = 0
            
            qb_stats.append(stats)
        
        return pd.DataFrame(qb_stats)
    
    except Exception as e:
        print(f"⚠️  Error fetching QB stats: {e}")
        return pd.DataFrame()


def get_recent_qb_performance(season: int = 2025, weeks: int = 3) -> pd.DataFrame:
    """
    Get QB performance over last N weeks.
    
    Args:
        season: NFL season
        weeks: Number of recent weeks to analyze
    
    Returns:
        DataFrame with recent QB stats
    """
    try:
        pbp = nfl.import_pbp_data([season], downcast=False)
        
        # Get max week
        max_week = pbp['week'].max()
        recent_weeks = list(range(max(1, max_week - weeks + 1), max_week + 1))
        
        # Filter to recent weeks
        recent_pbp = pbp[pbp['week'].isin(recent_weeks)]
        passing = recent_pbp[
            (recent_pbp['play_type'] == 'pass') & 
            (recent_pbp['passer_player_id'].notna())
        ]
        
        qb_stats = []
        
        for team in passing['posteam'].unique():
            team_passing = passing[passing['posteam'] == team]
            
            if len(team_passing) == 0:
                continue
            
            qb_counts = team_passing['passer_player_name'].value_counts()
            if len(qb_counts) == 0:
                continue
            
            primary_qb = qb_counts.index[0]
            primary_qb_plays = team_passing[team_passing['passer_player_name'] == primary_qb]
            
            stats = {
                'team': team,
                'qb_name': primary_qb,
                'qb_recent_dropbacks': len(primary_qb_plays),
                'qb_recent_epa': primary_qb_plays['qb_epa'].mean(),
                'qb_recent_cpoe': primary_qb_plays['cpoe'].mean(),
                'qb_recent_scramble_rate': (primary_qb_plays['qb_scramble'] == 1).mean(),
            }
            
            qb_stats.append(stats)
        
        return pd.DataFrame(qb_stats)
    
    except Exception as e:
        print(f"⚠️  Error fetching recent QB performance: {e}")
        return pd.DataFrame()


def add_qb_features(matchups: pd.DataFrame, season: int = 2025) -> pd.DataFrame:
    """
    Add QB features to matchup DataFrame.
    
    Args:
        matchups: DataFrame with away/home teams
        season: NFL season
    
    Returns:
        Matchups with QB features added
    """
    # Fetch QB stats
    qb_stats = fetch_qb_stats(season)
    qb_recent = get_recent_qb_performance(season, weeks=3)
    
    if qb_stats.empty:
        print("⚠️  No QB stats available, using defaults")
        return matchups
    
    # Merge season-long stats
    matchups = matchups.merge(
        qb_stats.add_prefix('away_'),
        left_on='away',
        right_on='away_team',
        how='left'
    )
    matchups = matchups.merge(
        qb_stats.add_prefix('home_'),
        left_on='home',
        right_on='home_team',
        how='left'
    )
    
    # Merge recent stats
    if not qb_recent.empty:
        matchups = matchups.merge(
            qb_recent.add_prefix('away_'),
            left_on='away',
            right_on='away_team',
            how='left',
            suffixes=('', '_recent')
        )
        matchups = matchups.merge(
            qb_recent.add_prefix('home_'),
            left_on='home',
            right_on='home_team',
            how='left',
            suffixes=('', '_recent')
        )
    
    # Fill NaNs with league average (numeric columns only)
    qb_cols = [c for c in matchups.columns if 'qb_' in c.lower() and matchups[c].dtype in ['float64', 'int64']]
    for col in qb_cols:
        matchups[col] = matchups[col].fillna(matchups[col].median())
    
    # QB delta features (away - home)
    if 'away_qb_epa' in matchups.columns and 'home_qb_epa' in matchups.columns:
        matchups['qb_epa_delta'] = matchups['away_qb_epa'] - matchups['home_qb_epa']
    
    if 'away_qb_recent_epa' in matchups.columns and 'home_qb_recent_epa' in matchups.columns:
        matchups['qb_recent_epa_delta'] = matchups['away_qb_recent_epa'] - matchups['home_qb_recent_epa']
    
    return matchups

