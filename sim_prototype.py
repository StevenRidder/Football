#!/usr/bin/env python3
"""
Quick Prototype: Monte Carlo Game Simulator
Uses nflfastR EPA data + our OL/DL stress features to simulate games.
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl
from pathlib import Path
from nfl_edge.team_mapping import normalize_team

def load_historical_epa():
    """Load historical EPA per play data from nflfastR."""
    
    print("📂 Loading nflfastR play-by-play data...")
    
    # Load recent seasons for EPA baselines
    pbp = nfl.import_pbp_data([2022, 2023, 2024])
    
    # Filter to regular plays (pass/run)
    plays = pbp[pbp['play_type'].isin(['pass', 'run'])].copy()
    
    print(f"  ✅ Loaded {len(plays):,} plays")
    
    return plays

def calculate_team_epa_baselines(pbp):
    """Calculate each team's offensive and defensive EPA per play."""
    
    print("\n🔧 Calculating team EPA baselines...")
    
    team_stats = []
    
    for season in pbp['season'].unique():
        season_pbp = pbp[pbp['season'] == season]
        
        for week in range(1, 19):
            week_pbp = season_pbp[season_pbp['week'] < week]  # Historical only
            
            if len(week_pbp) == 0:
                continue
            
            teams = set(week_pbp['posteam'].dropna().unique())
            
            for team in teams:
                team_norm = normalize_team(team)
                
                # Offensive EPA
                off_plays = week_pbp[week_pbp['posteam'] == team]
                off_epa = off_plays['epa'].mean() if len(off_plays) > 0 else 0.0
                
                # Defensive EPA (lower is better)
                def_plays = week_pbp[week_pbp['defteam'] == team]
                def_epa = def_plays['epa'].mean() if len(def_plays) > 0 else 0.0
                
                # Pass/Run splits
                off_pass = off_plays[off_plays['play_type'] == 'pass']['epa'].mean() if len(off_plays[off_plays['play_type'] == 'pass']) > 0 else 0.0
                off_run = off_plays[off_plays['play_type'] == 'run']['epa'].mean() if len(off_plays[off_plays['play_type'] == 'run']) > 0 else 0.0
                
                team_stats.append({
                    'season': season,
                    'week': week,
                    'team': team_norm,
                    'off_epa_per_play': off_epa,
                    'def_epa_per_play': def_epa,
                    'off_pass_epa': off_pass,
                    'off_run_epa': off_run,
                    'plays_run': len(off_plays),
                })
    
    df = pd.DataFrame(team_stats)
    print(f"  ✅ Calculated EPA for {len(df)} team-weeks")
    
    return df

def simulate_drive(off_epa, def_epa, stress_factor, field_position=75):
    """
    Simulate a single drive outcome.
    
    Args:
        off_epa: Offensive EPA per play (higher = better offense)
        def_epa: Defensive EPA per play ALLOWED (higher = worse defense)
        stress_factor: OL/DL matchup factor
        field_position: Starting yards from own goal line
    
    Returns: (points_scored, plays_run, time_elapsed)
    """
    
    # Adjust EPA for matchup
    # off_epa: positive = good offense
    # def_epa: positive = bad defense (allows high EPA)
    # So we ADD def_epa (bad defense helps offense)
    adjusted_epa = (off_epa * stress_factor) + (def_epa * 0.5)  # Defense has 50% weight
    
    # Add some randomness (real games have variance)
    adjusted_epa += np.random.normal(0, 0.10)  # ~0.10 EPA std dev per play
    
    # Simplified drive simulation based on EPA
    # Higher EPA = more likely to score
    
    # Base scoring probability from EPA
    # 0.0 EPA = ~30% chance to score
    # 0.1 EPA = ~45% chance
    # 0.2 EPA = ~60% chance
    score_prob = 0.30 + (adjusted_epa * 1.5)
    score_prob = max(0.05, min(0.75, score_prob))  # Clamp between 5% and 75%
    
    # Determine if drive scores
    if np.random.random() < score_prob:
        # TD vs FG (higher EPA = more TDs)
        td_prob = 0.50 + (adjusted_epa * 2.0)
        td_prob = max(0.20, min(0.80, td_prob))
        
        if np.random.random() < td_prob:
            points = 7  # Touchdown
        else:
            points = 3  # Field goal
    else:
        points = 0  # Punt/turnover
    
    # Estimate plays and time
    plays = int(np.random.normal(6, 2))  # Average drive is ~6 plays
    plays = max(3, min(15, plays))
    time_elapsed = plays * 40  # ~40 seconds per play
    
    return (points, plays, time_elapsed)

def simulate_game(away_off_epa, away_def_epa, home_off_epa, home_def_epa, 
                  away_stress, home_stress, n_sims=1000):
    """
    Simulate a full game n_sims times.
    
    Returns: DataFrame with simulation results
    """
    
    results = []
    
    for sim in range(n_sims):
        away_score = 0
        home_score = 0
        time_remaining = 3600  # 60 minutes in seconds
        possession = 'away' if np.random.random() < 0.5 else 'home'
        
        # Simulate possessions until time runs out
        while time_remaining > 0:
            if possession == 'away':
                points, plays, time = simulate_drive(
                    away_off_epa, home_def_epa, away_stress
                )
                away_score += points
                possession = 'home'
            else:
                points, plays, time = simulate_drive(
                    home_off_epa, away_def_epa, home_stress
                )
                home_score += points
                possession = 'away'
            
            time_remaining -= time
        
        results.append({
            'away_score': away_score,
            'home_score': home_score,
            'total': away_score + home_score,
            'spread': away_score - home_score,
        })
    
    return pd.DataFrame(results)

def main():
    print("=" * 70)
    print("🎲 QUICK PROTOTYPE: MONTE CARLO GAME SIMULATOR")
    print("=" * 70)
    
    # Load data
    pbp = load_historical_epa()
    team_epa = calculate_team_epa_baselines(pbp)
    
    # Load stress features
    print("\n📂 Loading OL/DL stress features...")
    stress = pd.read_csv('data/features/matchup_stress_2022_2025.csv')
    print(f"  ✅ Loaded {len(stress)} games")
    
    # Load team features for context
    print("\n📂 Loading team features...")
    team_features = pd.read_csv('data/features/team_features_2022_2025.csv')
    print(f"  ✅ Loaded {len(team_features)} team-weeks")
    
    # Load 2025 schedule
    print("\n📂 Loading 2025 schedule...")
    sched = nfl.import_schedules([2025])
    sched_reg = sched[sched['game_type'] == 'REG'].copy()
    sched_reg['away'] = sched_reg['away_team'].apply(normalize_team)
    sched_reg['home'] = sched_reg['home_team'].apply(normalize_team)
    
    # Focus on Week 9 (upcoming)
    week9 = sched_reg[sched_reg['week'] == 9].copy()
    print(f"  ✅ Found {len(week9)} Week 9 games")
    
    # Merge all features
    print("\n🔧 Merging features...")
    
    # Merge stress
    week9 = pd.merge(
        week9,
        stress[stress['season'] == 2025],
        left_on=['away', 'home', 'week'],
        right_on=['away', 'home', 'week'],
        how='left'
    )
    
    # For 2025, use 2024 end-of-season EPA as baseline (no 2025 PBP data yet)
    # Get latest EPA for each team from 2024
    team_epa_2024 = team_epa[team_epa['season'] == 2024].copy()
    latest_epa = team_epa_2024.groupby('team').last().reset_index()
    
    # Merge EPA for away team
    week9 = pd.merge(
        week9,
        latest_epa[['team', 'off_epa_per_play', 'def_epa_per_play', 'off_pass_epa', 'off_run_epa']],
        left_on='away',
        right_on='team',
        how='left',
        suffixes=('', '_away')
    )
    
    # Merge EPA for home team
    week9 = pd.merge(
        week9,
        latest_epa[['team', 'off_epa_per_play', 'def_epa_per_play', 'off_pass_epa', 'off_run_epa']],
        left_on='home',
        right_on='team',
        how='left',
        suffixes=('_away', '_home')
    )
    
    print(f"  ✅ Merged features for {len(week9)} games")
    
    # Run simulations for each game
    print("\n🎲 Running simulations...")
    print("=" * 70)
    
    predictions = []
    
    for idx, game in week9.iterrows():
        away = game['away']
        home = game['home']
        
        # Get EPA baselines (with _away and _home suffixes from merge)
        away_off_epa = game.get('off_epa_per_play_away', 0.0)
        away_def_epa = game.get('def_epa_per_play_away', 0.0)
        home_off_epa = game.get('off_epa_per_play_home', 0.0)
        home_def_epa = game.get('def_epa_per_play_home', 0.0)
        
        # Handle NaN EPA values
        if pd.isna(away_off_epa):
            away_off_epa = 0.0
        if pd.isna(away_def_epa):
            away_def_epa = 0.0
        if pd.isna(home_off_epa):
            home_off_epa = 0.0
        if pd.isna(home_def_epa):
            home_def_epa = 0.0
        
        # Calculate stress factors (OL vs DL matchup)
        # Positive stress_diff means away OL has advantage
        stress_diff = game.get('stress_diff', 0.0)
        
        # Handle NaN stress (Week 9 doesn't have stress data yet)
        if pd.isna(stress_diff):
            stress_diff = 0.0
        
        # Convert to multiplicative factors
        # stress_diff of +1 std dev = 10% EPA boost
        away_stress = 1.0 + (stress_diff * 0.1)
        home_stress = 1.0 - (stress_diff * 0.1)
        
        print(f"\n{away} @ {home}")
        print(f"  Away: {away_off_epa:.3f} EPA/play (stress: {away_stress:.2f}x)")
        print(f"  Home: {home_off_epa:.3f} EPA/play (stress: {home_stress:.2f}x)")
        
        # Run simulation
        sims = simulate_game(
            away_off_epa, away_def_epa,
            home_off_epa, home_def_epa,
            away_stress, home_stress,
            n_sims=10000
        )
        
        # Calculate predictions
        pred_spread = sims['spread'].mean()
        pred_total = sims['total'].mean()
        
        # Get market lines
        market_spread = game.get('spread_line', 0.0)
        market_total = game.get('total_line', 0.0)
        
        # Calculate edge
        spread_edge = pred_spread - market_spread
        total_edge = pred_total - market_total
        
        print(f"  Simulated: {away} {sims['away_score'].mean():.1f}, {home} {sims['home_score'].mean():.1f}")
        print(f"  Spread: {pred_spread:+.1f} (Market: {market_spread:+.1f}, Edge: {spread_edge:+.1f})")
        print(f"  Total: {pred_total:.1f} (Market: {market_total:.1f}, Edge: {total_edge:+.1f})")
        
        # Determine if this is a bet
        bet = None
        if abs(spread_edge) >= 2.0:
            if spread_edge > 0:
                bet = f"{away} covers"
            else:
                bet = f"{home} covers"
            print(f"  🎯 BET: {bet} (Edge: {abs(spread_edge):.1f} pts)")
        
        if abs(total_edge) >= 2.0:
            if total_edge > 0:
                bet_total = f"Over {market_total:.1f}"
            else:
                bet_total = f"Under {market_total:.1f}"
            print(f"  🎯 BET: {bet_total} (Edge: {abs(total_edge):.1f} pts)")
        
        predictions.append({
            'away': away,
            'home': home,
            'pred_spread': pred_spread,
            'market_spread': market_spread,
            'spread_edge': spread_edge,
            'pred_total': pred_total,
            'market_total': market_total,
            'total_edge': total_edge,
            'bet': bet,
        })
    
    # Save predictions
    pred_df = pd.DataFrame(predictions)
    pred_df.to_csv('sim_predictions_week9.csv', index=False)
    
    print("\n" + "=" * 70)
    print("✅ SIMULATION COMPLETE")
    print("=" * 70)
    print(f"\nSaved predictions to: sim_predictions_week9.csv")
    
    # Summary
    bets = pred_df[pred_df['bet'].notna()]
    print(f"\nBets found: {len(bets)}")
    if len(bets) > 0:
        print("\nRecommended bets:")
        for _, bet in bets.iterrows():
            print(f"  {bet['away']} @ {bet['home']}: {bet['bet']} (Edge: {abs(bet['spread_edge']):.1f} pts)")

if __name__ == "__main__":
    main()

