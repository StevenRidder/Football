"""
Enhanced EPA Interaction Features for NFL Betting Model

This module creates offense-vs-defense EPA matchup features using nflfastR play-by-play data.
These features capture true team strength beyond raw points for/against and provide
early-week signals that may not be fully priced into opening lines.

Key Features:
- Offense EPA vs Defense EPA allowed (pass/rush splits)
- Success rate matchups by down and distance
- Situational EPA (neutral script, red zone, explosive plays)
- Recent performance weighting (last 4 games vs season-long)

References:
- nflfastR EPA model: https://www.opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/
- EPA methodology: Expected Points Added per play, calibrated on millions of NFL snaps
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
from typing import Dict, Tuple


def fetch_pbp_data(season: int, weeks: list = None) -> pd.DataFrame:
    """
    Fetch play-by-play data from nflfastR for specified season and weeks.
    
    Args:
        season: NFL season year (e.g., 2025)
        weeks: List of week numbers to fetch (None = all weeks)
    
    Returns:
        DataFrame with play-by-play data
    """
    print(f"Fetching play-by-play data for {season} season...")
    pbp = nfl.import_pbp_data([season])
    
    if weeks:
        pbp = pbp[pbp['week'].isin(weeks)]
    
    # Filter to regular plays only (no penalties, timeouts, etc)
    pbp = pbp[
        (pbp['play_type'].isin(['pass', 'run'])) &
        (pbp['epa'].notna()) &
        (pbp['success'].notna())
    ].copy()
    
    print(f"Loaded {len(pbp):,} plays")
    return pbp


def calculate_team_epa_stats(pbp: pd.DataFrame, recent_weeks: int = 4) -> pd.DataFrame:
    """
    Calculate comprehensive EPA statistics for each team (offense and defense).
    
    Args:
        pbp: Play-by-play DataFrame from nflfastR
        recent_weeks: Number of recent weeks to emphasize (default: 4)
    
    Returns:
        DataFrame with team EPA statistics
    """
    stats_list = []
    
    for team in pbp['posteam'].dropna().unique():
        # Offensive stats (when team has possession)
        off_plays = pbp[pbp['posteam'] == team].copy()
        
        # Defensive stats (when opponent has possession)
        def_plays = pbp[pbp['defteam'] == team].copy()
        
        if len(off_plays) == 0 or len(def_plays) == 0:
            continue
        
        # Get recent weeks for recency weighting
        max_week = pbp['week'].max()
        recent_cutoff = max(1, max_week - recent_weeks + 1)
        
        off_recent = off_plays[off_plays['week'] >= recent_cutoff]
        def_recent = def_plays[def_plays['week'] >= recent_cutoff]
        
        stats = {
            'team': team,
            'max_week': max_week,
            
            # Overall EPA
            'off_epa_play': off_plays['epa'].mean(),
            'off_epa_play_recent': off_recent['epa'].mean() if len(off_recent) > 0 else off_plays['epa'].mean(),
            'def_epa_play': def_plays['epa'].mean(),  # Lower is better for defense
            'def_epa_play_recent': def_recent['epa'].mean() if len(def_recent) > 0 else def_plays['epa'].mean(),
            
            # Pass vs Rush splits
            'off_pass_epa': off_plays[off_plays['play_type'] == 'pass']['epa'].mean(),
            'off_rush_epa': off_plays[off_plays['play_type'] == 'run']['epa'].mean(),
            'def_pass_epa': def_plays[def_plays['play_type'] == 'pass']['epa'].mean(),
            'def_rush_epa': def_plays[def_plays['play_type'] == 'run']['epa'].mean(),
            
            # Success rate (% of plays with positive EPA)
            'off_success_rate': off_plays['success'].mean(),
            'off_success_rate_recent': off_recent['success'].mean() if len(off_recent) > 0 else off_plays['success'].mean(),
            'def_success_rate': def_plays['success'].mean(),
            'def_success_rate_recent': def_recent['success'].mean() if len(def_recent) > 0 else def_plays['success'].mean(),
            
            # Situational EPA (neutral script = score within 7 points in first 3 quarters)
            'off_neutral_epa': off_plays[
                (off_plays['score_differential'].abs() <= 7) & 
                (off_plays['qtr'] <= 3)
            ]['epa'].mean(),
            'def_neutral_epa': def_plays[
                (def_plays['score_differential'].abs() <= 7) & 
                (def_plays['qtr'] <= 3)
            ]['epa'].mean(),
            
            # Red zone efficiency (inside opponent 20)
            'off_rz_epa': off_plays[off_plays['yardline_100'] <= 20]['epa'].mean(),
            'def_rz_epa': def_plays[def_plays['yardline_100'] <= 20]['epa'].mean(),
            
            # Explosive play rate (EPA > 1.0)
            'off_explosive_rate': (off_plays['epa'] > 1.0).mean(),
            'def_explosive_rate': (def_plays['epa'] > 1.0).mean(),
            
            # Down-distance context
            'off_early_down_epa': off_plays[off_plays['down'].isin([1, 2])]['epa'].mean(),
            'off_third_down_success': off_plays[off_plays['down'] == 3]['success'].mean(),
            'def_early_down_epa': def_plays[def_plays['down'].isin([1, 2])]['epa'].mean(),
            'def_third_down_success': def_plays[def_plays['down'] == 3]['success'].mean(),
            
            # Play counts for weighting
            'off_plays': len(off_plays),
            'def_plays': len(def_plays),
        }
        
        stats_list.append(stats)
    
    return pd.DataFrame(stats_list)


def create_matchup_features(matchups: pd.DataFrame, team_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Create offense-vs-defense interaction features for each matchup.
    
    Args:
        matchups: DataFrame with 'away' and 'home' columns
        team_stats: DataFrame with team EPA statistics
    
    Returns:
        DataFrame with matchup interaction features added
    """
    df = matchups.copy()
    
    # Merge away team stats (all columns)
    away_stats = team_stats.copy()
    away_stats = away_stats.rename(columns={'team': 'away'})
    away_stats.columns = ['away' if col == 'away' else f'away_{col}' for col in away_stats.columns]
    df = df.merge(away_stats, on='away', how='left')
    
    # Merge home team stats (all columns)
    home_stats = team_stats.copy()
    home_stats = home_stats.rename(columns={'team': 'home'})
    home_stats.columns = ['home' if col == 'home' else f'home_{col}' for col in home_stats.columns]
    df = df.merge(home_stats, on='home', how='left')
    
    # Create interaction features (offense EPA - defense EPA allowed)
    # Positive = offense advantage, Negative = defense advantage
    
    # Away offense vs Home defense
    df['away_off_vs_home_def_epa'] = df['away_off_epa_play'] - df['home_def_epa_play']
    df['away_off_vs_home_def_epa_recent'] = df['away_off_epa_play_recent'] - df['home_def_epa_play_recent']
    df['away_pass_vs_home_pass_def'] = df['away_off_pass_epa'] - df['home_def_pass_epa']
    df['away_rush_vs_home_rush_def'] = df['away_off_rush_epa'] - df['home_def_rush_epa']
    
    # Home offense vs Away defense
    df['home_off_vs_away_def_epa'] = df['home_off_epa_play'] - df['away_def_epa_play']
    df['home_off_vs_away_def_epa_recent'] = df['home_off_epa_play_recent'] - df['away_def_epa_play_recent']
    df['home_pass_vs_away_pass_def'] = df['home_off_pass_epa'] - df['away_def_pass_epa']
    df['home_rush_vs_away_rush_def'] = df['home_off_rush_epa'] - df['away_def_rush_epa']
    
    # Net matchup advantage (home - away)
    df['net_epa_matchup'] = df['home_off_vs_away_def_epa'] - df['away_off_vs_home_def_epa']
    df['net_epa_matchup_recent'] = df['home_off_vs_away_def_epa_recent'] - df['away_off_vs_home_def_epa_recent']
    
    # Success rate matchups
    df['away_success_vs_home_def'] = df['away_off_success_rate'] - df['home_def_success_rate']
    df['home_success_vs_away_def'] = df['home_off_success_rate'] - df['away_def_success_rate']
    df['net_success_matchup'] = df['home_success_vs_away_def'] - df['away_success_vs_home_def']
    
    # Explosive play matchups
    df['away_explosive_vs_home_def'] = df['away_off_explosive_rate'] - df['home_def_explosive_rate']
    df['home_explosive_vs_away_def'] = df['home_off_explosive_rate'] - df['away_def_explosive_rate']
    
    # Red zone matchups
    df['away_rz_vs_home_def'] = df['away_off_rz_epa'] - df['home_def_rz_epa']
    df['home_rz_vs_away_def'] = df['home_off_rz_epa'] - df['away_def_rz_epa']
    
    # Third down matchups
    df['away_3rd_vs_home_def'] = df['away_off_third_down_success'] - df['home_def_third_down_success']
    df['home_3rd_vs_away_def'] = df['home_off_third_down_success'] - df['away_def_third_down_success']
    
    print(f"Created {len([c for c in df.columns if 'vs' in c or 'net' in c])} interaction features")
    
    return df


def add_epa_interaction_features(matchups: pd.DataFrame, season: int = 2025, weeks_to_fetch: list = None) -> pd.DataFrame:
    """
    Main function to add enhanced EPA interaction features to matchups DataFrame.
    
    Args:
        matchups: DataFrame with 'away' and 'home' columns
        season: NFL season year
        weeks_to_fetch: List of weeks to include in calculations (None = all available)
    
    Returns:
        DataFrame with EPA interaction features added
    """
    # Fetch play-by-play data
    pbp = fetch_pbp_data(season, weeks_to_fetch)
    
    # Calculate team EPA statistics
    team_stats = calculate_team_epa_stats(pbp)
    
    # Create matchup features
    df_enhanced = create_matchup_features(matchups, team_stats)
    
    # Fill NaNs with 0 for teams with missing data
    epa_cols = [c for c in df_enhanced.columns if any(x in c for x in ['epa', 'success', 'explosive', 'rz', '3rd', 'vs', 'net'])]
    df_enhanced[epa_cols] = df_enhanced[epa_cols].fillna(0)
    
    print(f"Enhanced EPA features added successfully")
    return df_enhanced


if __name__ == "__main__":
    # Test the module
    print("Testing EPA interaction features...")
    
    # Create sample matchups
    test_matchups = pd.DataFrame({
        'away': ['BUF', 'KC', 'SF'],
        'home': ['MIA', 'LAC', 'DAL']
    })
    
    # Add features
    enhanced = add_epa_interaction_features(test_matchups, season=2025, weeks_to_fetch=[1, 2, 3, 4])
    
    # Display key features
    key_cols = ['away', 'home', 'net_epa_matchup', 'net_epa_matchup_recent', 'net_success_matchup']
    print("\nSample matchup features:")
    print(enhanced[key_cols].to_string())
    
    print("\nAll EPA interaction columns:")
    epa_cols = [c for c in enhanced.columns if 'vs' in c or 'net' in c]
    for col in sorted(epa_cols):
        print(f"  - {col}")

