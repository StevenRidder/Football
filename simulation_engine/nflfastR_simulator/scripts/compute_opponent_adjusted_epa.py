"""
Compute opponent-adjusted EPA for each team

CRITICAL: This must be zero-mean within each week
- Adjusts offensive EPA based on opponent defensive strength
- Adjusts defensive EPA based on opponent offensive strength
- Z-scored within week to maintain zero-mean property
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import nfl_data_py as nfl
from scipy import stats

def compute_opponent_adjusted_epa(season, weeks=None):
    """
    Compute opponent-adjusted EPA for a season.
    
    Returns DataFrame with:
    - team, week, season
    - off_epa_raw: raw offensive EPA
    - def_epa_raw: raw defensive EPA  
    - opp_def_strength: average opponent defensive EPA faced
    - opp_off_strength: average opponent offensive EPA faced
    - off_epa_adj: opponent-adjusted offensive EPA
    - def_epa_adj: opponent-adjusted defensive EPA
    - off_epa_adj_z: zero-mean z-score within week
    - def_epa_adj_z: zero-mean z-score within week
    """
    # Load play-by-play data
    print(f"Loading {season} play-by-play data...")
    pbp = nfl.import_pbp_data([season])
    
    # Filter to regular season
    pbp = pbp[pbp['season_type'] == 'REG'].copy()
    
    if weeks:
        pbp = pbp[pbp['week'].isin(weeks)]
    
    # Calculate EPA by team and week
    results = []
    
    for week in sorted(pbp['week'].unique()):
        week_pbp = pbp[pbp['week'] == week].copy()
        
        # Get all teams playing this week
        teams = set(week_pbp['posteam'].unique()) | set(week_pbp['defteam'].unique())
        teams = {t for t in teams if pd.notna(t)}
        
        team_stats = {}
        
        # Calculate raw EPA for each team
        for team in teams:
            # Offensive EPA
            off_plays = week_pbp[week_pbp['posteam'] == team]
            off_epa = off_plays['epa'].mean() if len(off_plays) > 0 else 0
            
            # Defensive EPA (lower is better)
            def_plays = week_pbp[week_pbp['defteam'] == team]
            def_epa = def_plays['epa'].mean() if len(def_plays) > 0 else 0
            
            team_stats[team] = {
                'off_epa_raw': off_epa,
                'def_epa_raw': def_epa,
            }
        
        # Calculate opponent adjustments
        for team in teams:
            # Get opponents faced
            team_games = week_pbp[
                (week_pbp['posteam'] == team) | (week_pbp['defteam'] == team)
            ]
            
            opponents = set()
            if len(team_games[team_games['posteam'] == team]) > 0:
                opponents.update(team_games[team_games['posteam'] == team]['defteam'].unique())
            if len(team_games[team_games['defteam'] == team]) > 0:
                opponents.update(team_games[team_games['defteam'] == team]['posteam'].unique())
            
            opponents = {o for o in opponents if pd.notna(o) and o != team}
            
            # Average opponent strength
            if len(opponents) > 0:
                opp_def_strength = np.mean([team_stats[o]['def_epa_raw'] for o in opponents if o in team_stats])
                opp_off_strength = np.mean([team_stats[o]['off_epa_raw'] for o in opponents if o in team_stats])
            else:
                opp_def_strength = 0
                opp_off_strength = 0
            
            # Adjust EPA based on opponent strength
            # If you faced tough defenses, boost your offensive EPA
            # If you faced weak offenses, reduce your defensive EPA credit
            off_epa_adj = team_stats[team]['off_epa_raw'] - opp_def_strength
            def_epa_adj = team_stats[team]['def_epa_raw'] - opp_off_strength
            
            results.append({
                'season': season,
                'week': week,
                'team': team,
                'off_epa_raw': team_stats[team]['off_epa_raw'],
                'def_epa_raw': team_stats[team]['def_epa_raw'],
                'opp_def_strength': opp_def_strength,
                'opp_off_strength': opp_off_strength,
                'off_epa_adj': off_epa_adj,
                'def_epa_adj': def_epa_adj,
            })
    
    df = pd.DataFrame(results)
    
    # Z-score within each week to ensure zero-mean
    for week in df['week'].unique():
        week_mask = df['week'] == week
        
        if df[week_mask]['off_epa_adj'].std() > 0:
            df.loc[week_mask, 'off_epa_adj_z'] = stats.zscore(df[week_mask]['off_epa_adj'])
        else:
            df.loc[week_mask, 'off_epa_adj_z'] = 0
        
        if df[week_mask]['def_epa_adj'].std() > 0:
            df.loc[week_mask, 'def_epa_adj_z'] = stats.zscore(df[week_mask]['def_epa_adj'])
        else:
            df.loc[week_mask, 'def_epa_adj_z'] = 0
    
    return df

if __name__ == "__main__":
    print("=" * 70)
    print("COMPUTING OPPONENT-ADJUSTED EPA")
    print("=" * 70)
    print("Market sets mean. This is a zero-mean shape modifier.")
    print("=" * 70)
    
    # Compute for 2024 weeks 1-8
    df = compute_opponent_adjusted_epa(2024, weeks=range(1, 9))
    
    print(f"\n✅ Computed for {len(df)} team-weeks")
    
    # Verify zero-mean
    print("\n📊 ZERO-MEAN VERIFICATION:")
    for week in sorted(df['week'].unique()):
        week_data = df[df['week'] == week]
        off_mean = week_data['off_epa_adj_z'].mean()
        def_mean = week_data['def_epa_adj_z'].mean()
        print(f"   Week {week}: off_z={off_mean:+.4f}, def_z={def_mean:+.4f}")
    
    # Save
    output_file = Path(__file__).parent.parent / "data" / "opponent_adjusted_epa_2024.csv"
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved to {output_file}")
    
    # Show sample
    print("\n📊 SAMPLE (Week 1, Top 5 Offenses):")
    week1 = df[df['week'] == 1].sort_values('off_epa_adj', ascending=False).head(5)
    print(week1[['team', 'off_epa_raw', 'opp_def_strength', 'off_epa_adj', 'off_epa_adj_z']])
    
    print("\n" + "=" * 70)

