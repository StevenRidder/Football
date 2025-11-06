"""
Validate Pressure Calibration: Compare simulated vs actual pressure rates.

This script:
1. Runs simulations for a specific week
2. Extracts simulated pressure rates from traces
3. Compares to nflfastR actual pressure rates
4. Reports gaps and improvements

Usage:
    python3 scripts/validate_pressure_calibration.py --season 2025 --week 9
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import nfl_data_py as nfl
except ImportError:
    print("❌ nfl-data-py not installed")
    sys.exit(1)

from simulator.pressure_calibration import PressureCalibrator, PressureConfig


def load_actual_pressure_rates(season: int, week: int) -> pd.DataFrame:
    """Load actual pressure rates from nflfastR for validation."""
    print(f"📥 Loading actual pressure rates from nflfastR for {season} week {week}...")
    
    # Load play-by-play
    pbp = nfl.import_pbp_data([season], downcast=True)
    pbp = pbp[pbp['week'] == week].copy()
    
    # Filter to dropbacks
    dropbacks = pbp[
        (pbp['qb_dropback'] == 1) | 
        (pbp['pass'] == 1)
    ].copy()
    
    # Define pressure
    dropbacks['is_pressure'] = (
        (dropbacks['sack'] == 1) | 
        (dropbacks['qb_hit'] == 1)
    ).astype(int)
    
    # Get schedule for game context
    sched = nfl.import_schedules([season])
    sched = sched[sched['week'] == week].copy()
    
    results = []
    
    for _, game in sched.iterrows():
        game_id = game['game_id']
        home_team = game['home_team']
        away_team = game['away_team']
        
        game_pbp = dropbacks[dropbacks['game_id'] == game_id].copy()
        
        if len(game_pbp) == 0:
            continue
        
        # Home team pressure rates
        home_off = game_pbp[game_pbp['posteam'] == home_team]
        home_def = game_pbp[game_pbp['defteam'] == home_team]
        
        home_off_dropbacks = len(home_off)
        home_off_pressures = home_off['is_pressure'].sum()
        home_off_rate = home_off_pressures / home_off_dropbacks if home_off_dropbacks > 0 else 0
        
        home_def_dropbacks = len(home_def)
        home_def_pressures = home_def['is_pressure'].sum()
        home_def_rate = home_def_pressures / home_def_dropbacks if home_def_dropbacks > 0 else 0
        
        # Away team pressure rates
        away_off = game_pbp[game_pbp['posteam'] == away_team]
        away_def = game_pbp[game_pbp['defteam'] == away_team]
        
        away_off_dropbacks = len(away_off)
        away_off_pressures = away_off['is_pressure'].sum()
        away_off_rate = away_off_pressures / away_off_dropbacks if away_off_dropbacks > 0 else 0
        
        away_def_dropbacks = len(away_def)
        away_def_pressures = away_def['is_pressure'].sum()
        away_def_rate = away_def_pressures / away_def_dropbacks if away_def_dropbacks > 0 else 0
        
        results.append({
            'game_id': game_id,
            'season': season,
            'week': week,
            'home_team': home_team,
            'away_team': away_team,
            'home_off_pr_actual': home_off_rate,
            'home_def_pr_actual': home_def_rate,
            'away_off_pr_actual': away_off_rate,
            'away_def_pr_actual': away_def_rate,
            'home_off_dropbacks': home_off_dropbacks,
            'away_off_dropbacks': away_off_dropbacks,
        })
    
    return pd.DataFrame(results)


def load_simulated_pressure_rates(season: int, week: int) -> pd.DataFrame:
    """Load simulated pressure rates from trace files."""
    print(f"📥 Loading simulated pressure rates from traces for {season} week {week}...")
    
    traces_dir = Path(__file__).parent.parent / "artifacts" / "traces"
    
    if not traces_dir.exists():
        print(f"❌ Traces directory not found: {traces_dir}")
        return pd.DataFrame()
    
    results = []
    
    # Find trace files for this week
    for trace_file in traces_dir.glob(f"*_{week}_{season}.jsonl"):
        # Parse filename: AWAY_HOME_week_season.jsonl
        parts = trace_file.stem.split('_')
        if len(parts) >= 4:
            week_num = int(parts[-2])
            season_num = int(parts[-1])
            
            if week_num == week and season_num == season:
                away_team = parts[0]
                home_team = parts[1]
                
                # Load trace and extract pressure events
                import json
                pressure_events = []
                dropback_events = []
                
                with trace_file.open() as f:
                    for line in f:
                        if line.strip():
                            event = json.loads(line)
                            if event.get('kind') == 'pass.pressure':
                                pressure_events.append(event)
                            elif event.get('kind') == 'call.pass_run' and event.get('choice') == 'pass':
                                dropback_events.append(event)
                
                # Calculate pressure rates
                total_dropbacks = len(dropback_events)
                total_pressures = sum(1 for e in pressure_events if e.get('is_pressure', False))
                pressure_rate = total_pressures / total_dropbacks if total_dropbacks > 0 else 0
                
                # For now, use same rate for both teams (can refine with drive attribution)
                results.append({
                    'season': season,
                    'week': week,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_off_pr_sim': pressure_rate,
                    'away_off_pr_sim': pressure_rate,
                    'sim_dropbacks': total_dropbacks,
                })
    
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Validate pressure calibration")
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--week', type=int, required=True)
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PRESSURE CALIBRATION VALIDATION")
    print("=" * 80)
    
    # Load actual rates
    actual_df = load_actual_pressure_rates(args.season, args.week)
    
    if len(actual_df) == 0:
        print("❌ No actual data found")
        return
    
    print(f"✅ Loaded {len(actual_df)} actual games")
    
    # Load simulated rates
    sim_df = load_simulated_pressure_rates(args.season, args.week)
    
    if len(sim_df) == 0:
        print("⚠️  No simulated traces found. Run simulations first.")
        return
    
    print(f"✅ Loaded {len(sim_df)} simulated games")
    
    # Merge and compare
    merged = actual_df.merge(
        sim_df,
        on=['season', 'week', 'home_team', 'away_team'],
        how='inner'
    )
    
    if len(merged) == 0:
        print("❌ No matching games found")
        return
    
    print(f"\n📊 VALIDATION RESULTS ({len(merged)} games)")
    print("=" * 80)
    
    # Calculate gaps
    merged['home_off_gap'] = merged['home_off_pr_sim'] - merged['home_off_pr_actual']
    merged['away_off_gap'] = merged['away_off_pr_sim'] - merged['away_off_pr_actual']
    
    # Overall metrics
    print(f"\n🎯 Overall Pressure Rate Comparison:")
    print(f"   Actual avg: {(merged['home_off_pr_actual'].mean() + merged['away_off_pr_actual'].mean()) / 2:.3f}")
    print(f"   Simulated avg: {(merged['home_off_pr_sim'].mean() + merged['away_off_pr_sim'].mean()) / 2:.3f}")
    print(f"   Average gap: {(merged['home_off_gap'].abs().mean() + merged['away_off_gap'].abs().mean()) / 2:.3f}")
    
    # Per-team gaps
    print(f"\n📈 Top 10 Teams by Pressure Gap (absolute):")
    team_gaps = []
    for _, row in merged.iterrows():
        team_gaps.append({
            'team': row['home_team'],
            'gap': row['home_off_gap'],
            'actual': row['home_off_pr_actual'],
            'sim': row['home_off_pr_sim']
        })
        team_gaps.append({
            'team': row['away_team'],
            'gap': row['away_off_gap'],
            'actual': row['away_off_pr_actual'],
            'sim': row['away_off_pr_sim']
        })
    
    team_df = pd.DataFrame(team_gaps)
    team_summary = team_df.groupby('team').agg({
        'gap': 'mean',
        'actual': 'mean',
        'sim': 'mean'
    }).reset_index()
    team_summary['abs_gap'] = team_summary['gap'].abs()
    team_summary = team_summary.sort_values('abs_gap', ascending=False)
    
    print(team_summary.head(10).to_string(index=False))
    
    # Save results
    output_dir = Path(__file__).parent.parent / "artifacts" / "pressure_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    merged.to_csv(output_dir / f"pressure_validation_week{args.week}.csv", index=False)
    team_summary.to_csv(output_dir / f"pressure_team_gaps_week{args.week}.csv", index=False)
    
    print(f"\n💾 Results saved to: {output_dir}/")


if __name__ == "__main__":
    main()

