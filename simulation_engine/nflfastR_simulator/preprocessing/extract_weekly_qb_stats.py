#!/usr/bin/env python3
"""
Extract weekly QB stats with actual QB names for each team/week.

This fixes the issue where we use league-average QB stats instead of the actual
QB who played (e.g., SF backup QB when Purdy is injured).
"""

import pandas as pd
import nfl_data_py as nfl
from pathlib import Path

def extract_weekly_qb_stats(seasons=[2024, 2025], output_dir='data/nflfastR'):
    """
    Extract QB stats by team and week, including:
    - QB name (actual starter for that week)
    - Passing EPA, CPOE, completion %, yards/att
    - Performance under pressure
    - PFF grades if available
    """
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("EXTRACTING WEEKLY QB STATS")
    print("="*80)
    
    all_qb_stats = []
    
    for season in seasons:
        print(f"\n📥 Loading play-by-play data for {season}...")
        
        try:
            pbp = nfl.import_pbp_data([season])
        except Exception as e:
            print(f"❌ Error loading {season}: {e}")
            continue
        
        print(f"   Loaded {len(pbp):,} plays")
        
        # Filter to passing plays only
        passing = pbp[
            (pbp['play_type'].isin(['pass', 'qb_kneel', 'qb_spike'])) &
            (pbp['passer_player_name'].notna())
        ].copy()
        
        print(f"   {len(passing):,} passing plays")
        
        # Group by team, week, QB
        for (team, week, qb_name), plays in passing.groupby(['posteam', 'week', 'passer_player_name']):
            
            # Only process if QB had at least 5 attempts
            n_attempts = len(plays)
            if n_attempts < 5:
                continue
            
            # Overall stats
            completions = plays['complete_pass'].sum()
            comp_pct = completions / n_attempts if n_attempts > 0 else 0
            yards = plays['passing_yards'].sum()
            ypa = yards / n_attempts if n_attempts > 0 else 0
            tds = plays['pass_touchdown'].sum()
            ints = plays['interception'].sum()
            epa = plays['epa'].mean()
            cpoe = plays['cpoe'].mean()
            
            # Pressure splits
            pressure_plays = plays[plays['qb_hit'] == 1]
            clean_plays = plays[plays['qb_hit'] == 0]
            
            # Under pressure
            if len(pressure_plays) > 0:
                pressure_comp_pct = pressure_plays['complete_pass'].sum() / len(pressure_plays)
                pressure_ypa = pressure_plays['passing_yards'].sum() / len(pressure_plays)
                pressure_epa = pressure_plays['epa'].mean()
            else:
                pressure_comp_pct = 0
                pressure_ypa = 0
                pressure_epa = 0
            
            # Clean pocket
            if len(clean_plays) > 0:
                clean_comp_pct = clean_plays['complete_pass'].sum() / len(clean_plays)
                clean_ypa = clean_plays['passing_yards'].sum() / len(clean_plays)
                clean_epa = clean_plays['epa'].mean()
            else:
                clean_comp_pct = comp_pct
                clean_ypa = ypa
                clean_epa = epa
            
            all_qb_stats.append({
                'season': season,
                'week': week,
                'team': team,
                'qb_name': qb_name,
                'attempts': n_attempts,
                'completions': completions,
                'comp_pct': comp_pct,
                'yards': yards,
                'ypa': ypa,
                'tds': tds,
                'ints': ints,
                'epa': epa,
                'cpoe': cpoe,
                # Pressure splits
                'pressure_comp_pct': pressure_comp_pct,
                'pressure_ypa': pressure_ypa,
                'pressure_epa': pressure_epa,
                'clean_comp_pct': clean_comp_pct,
                'clean_ypa': clean_ypa,
                'clean_epa': clean_epa,
            })
    
    # Convert to DataFrame
    qb_df = pd.DataFrame(all_qb_stats)
    
    # For each team/week, identify the primary QB (most attempts)
    qb_df = qb_df.sort_values(['season', 'week', 'team', 'attempts'], ascending=[True, True, True, False])
    primary_qbs = qb_df.groupby(['season', 'week', 'team']).first().reset_index()
    
    # Save
    output_file = output_dir / 'qb_stats_weekly.csv'
    primary_qbs.to_csv(output_file, index=False)
    
    print(f"\n✅ Saved {len(primary_qbs)} team/week QB records to: {output_file}")
    print(f"\n📊 Sample QBs:")
    print(primary_qbs[['season', 'week', 'team', 'qb_name', 'attempts', 'comp_pct', 'ypa', 'epa']].head(20))
    
    # Check for backups (e.g., SF)
    print(f"\n🔍 Checking for backup QB situations...")
    for team in ['SF', 'DAL', 'CIN']:
        team_qbs = primary_qbs[primary_qbs['team'] == team].sort_values('week')
        if len(team_qbs) > 0:
            print(f"\n{team} QBs by week:")
            print(team_qbs[['week', 'qb_name', 'attempts', 'comp_pct', 'epa']].to_string(index=False))
    
    return primary_qbs


if __name__ == '__main__':
    qb_stats = extract_weekly_qb_stats(seasons=[2024, 2025])
    print("\n✅ QB extraction complete!")

