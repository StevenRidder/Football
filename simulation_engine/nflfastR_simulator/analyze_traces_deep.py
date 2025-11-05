"""
Deep Trace Analysis: Compare simulator traces to NFLfastR actuals with pattern detection.

This script performs deep analysis of trace files to identify:
1. Per-team, per-week patterns (pressure rates, EPA, completion rates)
2. Systematic biases (defensive variance, pressure calibration)
3. Play-by-play realism (completion rates, explosive plays, drive outcomes)
4. Comparison to NFLfastR actuals with actionable calibration insights

Usage:
  python3 analyze_traces_deep.py --season 2025 --weeks 1-8
  python3 analyze_traces_deep.py --season 2025 --weeks 1-8 --team DAL
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import numpy as np
import pandas as pd

try:
    from nfl_data_py import import_pbp_data, import_schedules
except ImportError:
    print("⚠️  nfl-data-py not installed. Install with: pip install nfl-data-py")
    import_schedules = None
    import_pbp_data = None


def _parse_weeks(arg: str) -> List[int]:
    """Parse week argument."""
    arg = arg.strip()
    if "-" in arg:
        a, b = arg.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in arg.split(",") if x.strip()]


def _load_trace_file(trace_path: Path) -> Optional[Dict]:
    """Load trace file and extract all relevant metrics."""
    try:
        events = []
        with trace_path.open() as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        if not events:
            return None
        
        # Parse game metadata
        inputs_audit = None
        game_summary = None
        game_id = None
        
        for event in events:
            if event.get('kind') == 'inputs.audit':
                inputs_audit = event
                game_id = event.get('game_id', '')
            elif event.get('kind') == 'game.summary':
                game_summary = event
        
        if not inputs_audit or not game_summary:
            return None
        
        # Parse game_id
        parts = game_id.split('_')
        if len(parts) < 4:
            return None
        
        season = int(parts[0])
        week = int(parts[1])
        away_team = parts[2].upper()
        home_team = parts[3].upper()
        
        # Extract team profiles
        home_profile = inputs_audit.get('home', {})
        away_profile = inputs_audit.get('away', {})
        
        # Extract scores
        home_score = game_summary.get('home_score', 0)
        away_score = game_summary.get('away_score', 0)
        
        # Extract drive summaries
        drive_summaries = [e for e in events if e.get('kind') == 'drive.summary']
        
        # Extract play events
        call_events = [e for e in events if e.get('kind') == 'call.pass_run']
        play_events = [e for e in events if e.get('kind') == 'play.result']
        pressure_events = [e for e in events if e.get('kind') == 'pass.pressure']
        completion_events = [e for e in events if e.get('kind') == 'pass.completion_model']
        
        # Extract anchor slices (per-drive metrics)
        anchor_slices = [e for e in events if e.get('kind') == 'anchor_slice']
        
        # Build drive-to-team mapping from drive summaries
        # drive.summary events mark the END of a drive, so events before it belong to that team
        drive_to_team = {}
        for drive in drive_summaries:
            drive_num = drive.get('drive_no', 0)
            team_side = drive.get('team', '')  # 'home' or 'away'
            drive_to_team[drive_num] = team_side
        
        # Track which team is on offense for each event
        home_plays = []
        away_plays = []
        home_pressures = []
        away_pressures = []
        home_completions = []
        away_completions = []
        home_play_results = []
        away_play_results = []
        
        # Simple approach: events before drive.summary #N belong to team in that summary
        # After a drive.summary, the OTHER team gets the ball (alternating)
        current_team = None
        last_drive_team = None
        
        for i, event in enumerate(events):
            if event.get('kind') == 'drive.summary':
                # This drive just finished - events before it belonged to this team
                team_side = event.get('team', '')
                last_drive_team = team_side
                # After this, the other team gets the ball
                current_team = 'home' if team_side == 'away' else 'away'
            else:
                # Determine which team is on offense
                # Look backwards for the most recent drive.summary
                if current_team is None:
                    # Before any drive.summary, use the first drive's team
                    # Find the first drive.summary
                    for j in range(i, len(events)):
                        if events[j].get('kind') == 'drive.summary':
                            first_team = events[j].get('team', '')
                            current_team = first_team
                            break
                    if current_team is None:
                        continue  # Skip if we can't determine
                else:
                    # If we just saw a drive.summary, we already set current_team
                    # Otherwise, keep using the current team
                    pass
                
                # Categorize event by current_team
                if current_team == 'home':
                    if event.get('kind') == 'call.pass_run':
                        home_plays.append(event)
                    elif event.get('kind') == 'pass.pressure':
                        home_pressures.append(event)
                    elif event.get('kind') == 'pass.completion_model':
                        home_completions.append(event)
                    elif event.get('kind') == 'play.result':
                        home_play_results.append(event)
                elif current_team == 'away':
                    if event.get('kind') == 'call.pass_run':
                        away_plays.append(event)
                    elif event.get('kind') == 'pass.pressure':
                        away_pressures.append(event)
                    elif event.get('kind') == 'pass.completion_model':
                        away_completions.append(event)
                    elif event.get('kind') == 'play.result':
                        away_play_results.append(event)
        
        # Calculate metrics per team
        def calc_team_metrics(team_side: str, plays: List, pressures: List, completions: List, 
                             play_results: List, drives: List):
            """Calculate metrics for one team."""
            # Pass/run split
            pass_plays = [p for p in plays if p.get('choice') == 'pass']
            run_plays = [p for p in plays if p.get('choice') == 'run']
            total_plays = len(plays)
            pass_rate = len(pass_plays) / total_plays if total_plays > 0 else 0
            
            # Pressure metrics
            total_dropbacks = len(pass_plays)
            pressures_faced = [p for p in pressures if p.get('is_pressure', False)]
            pressure_rate = len(pressures_faced) / total_dropbacks if total_dropbacks > 0 else 0
            avg_base_pressure = np.mean([p.get('base', 0) for p in pressures]) if pressures else 0
            avg_final_pressure = np.mean([p.get('final', 0) for p in pressures]) if pressures else 0
            
            # Completion rates (from completion model events)
            clean_completions = [c for c in completions if c.get('split') == 'clean']
            pressure_completions = [c for c in completions if c.get('split') == 'pressure']
            
            clean_comp_rate = np.mean([c.get('final_completion_pct', 0) for c in clean_completions]) if clean_completions else 0
            pressure_comp_rate = np.mean([c.get('final_completion_pct', 0) for c in pressure_completions]) if pressure_completions else 0
            
            # Actual play results
            completions_actual = len([p for p in play_results if p.get('type') == 'completion'])
            incompletions = len([p for p in play_results if p.get('type') == 'incomplete'])
            explosive_plays = len([p for p in play_results if p.get('explosive', False)])
            explosive_rate = explosive_plays / len(play_results) if play_results else 0
            
            # Drive metrics
            drive_points = [d.get('points', 0) for d in drives]
            drive_plays = [d.get('plays', 0) for d in drives]
            total_points = sum(drive_points)
            avg_plays_per_drive = np.mean(drive_plays) if drive_plays else 0
            td_rate = len([d for d in drives if d.get('result') == 'TD']) / len(drives) if drives else 0
            
            # EPA (from inputs - this is what team was given, not simulated)
            profile = home_profile if team_side == 'home' else away_profile
            input_epa = profile.get('off_epa', 0)
            
            return {
                'total_plays': total_plays,
                'pass_rate': pass_rate,
                'pressure_rate': pressure_rate,
                'avg_base_pressure': avg_base_pressure,
                'avg_final_pressure': avg_final_pressure,
                'clean_comp_rate': clean_comp_rate,
                'pressure_comp_rate': pressure_comp_rate,
                'explosive_rate': explosive_plays / total_plays if total_plays > 0 else 0,
                'total_points': total_points,
                'avg_plays_per_drive': avg_plays_per_drive,
                'td_rate': td_rate,
                'input_epa': input_epa,
            }
        
        home_metrics = calc_team_metrics('home', home_plays, home_pressures, home_completions,
                                        home_play_results, [d for d in drive_summaries if d.get('team') == 'home'])
        away_metrics = calc_team_metrics('away', away_plays, away_pressures, away_completions,
                                        away_play_results, [d for d in drive_summaries if d.get('team') == 'away'])
        
        return {
            'season': season,
            'week': week,
            'home_team': home_team,
            'away_team': away_team,
            'home_score_sim': home_score,
            'away_score_sim': away_score,
            # Home metrics
            'home_pass_rate': home_metrics['pass_rate'],
            'home_pressure_rate': home_metrics['pressure_rate'],
            'home_avg_base_pressure': home_metrics['avg_base_pressure'],
            'home_avg_final_pressure': home_metrics['avg_final_pressure'],
            'home_clean_comp_rate': home_metrics['clean_comp_rate'],
            'home_pressure_comp_rate': home_metrics['pressure_comp_rate'],
            'home_explosive_rate': home_metrics['explosive_rate'],
            'home_avg_plays_per_drive': home_metrics['avg_plays_per_drive'],
            'home_td_rate': home_metrics['td_rate'],
            'home_input_epa': home_metrics['input_epa'],
            # Away metrics
            'away_pass_rate': away_metrics['pass_rate'],
            'away_pressure_rate': away_metrics['pressure_rate'],
            'away_avg_base_pressure': away_metrics['avg_base_pressure'],
            'away_avg_final_pressure': away_metrics['avg_final_pressure'],
            'away_clean_comp_rate': away_metrics['clean_comp_rate'],
            'away_pressure_comp_rate': away_metrics['pressure_comp_rate'],
            'away_explosive_rate': away_metrics['explosive_rate'],
            'away_avg_plays_per_drive': away_metrics['avg_plays_per_drive'],
            'away_td_rate': away_metrics['td_rate'],
            'away_input_epa': away_metrics['input_epa'],
        }
    except Exception as e:
        print(f"⚠️  Error loading trace {trace_path}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _load_actuals_deep(season: int, weeks: List[int]) -> pd.DataFrame:
    """Load detailed actual metrics from NFLfastR."""
    if import_pbp_data is None or import_schedules is None:
        raise ImportError("nfl-data-py not installed")
    
    # Get schedule
    sched = import_schedules([season])
    sched = sched[sched["week"].isin(weeks)].copy()
    
    # Get play-by-play
    pbp = import_pbp_data([season], downcast=True)
    pbp = pbp[pbp["week"].isin(weeks)].copy()
    
    # Per-game, per-team metrics
    results = []
    
    for game_id in sched['game_id'].unique():
        game_pbp = pbp[pbp['game_id'] == game_id].copy()
        game_sched = sched[sched['game_id'] == game_id].iloc[0]
        
        for team_role in ['home', 'away']:
            team = game_sched[f'{team_role}_team']
            
            # Offensive plays
            off_plays = game_pbp[game_pbp['posteam'] == team].copy()
            
            if len(off_plays) == 0:
                continue
            
            # Basic metrics
            total_plays = len(off_plays)
            pass_plays = off_plays[off_plays['pass'] == 1]
            run_plays = off_plays[off_plays['rush'] == 1]
            pass_rate = len(pass_plays) / total_plays if total_plays > 0 else 0
            
            # EPA
            epa_mean = pass_plays['epa'].mean() if len(pass_plays) > 0 else 0
            
            # Pressure (sacks + QB hits per dropback)
            dropbacks = pass_plays[pass_plays['pass'] == 1]
            if len(dropbacks) > 0:
                sacks = dropbacks['sack'].sum()
                qb_hits = dropbacks['qb_hit'].sum()
                pressure_rate = (sacks + qb_hits) / len(dropbacks)
            else:
                pressure_rate = 0
            
            # Completion rates
            pass_attempts = pass_plays[pass_plays['pass'] == 1]
            completions = pass_attempts[pass_attempts['complete_pass'] == 1]
            comp_rate = len(completions) / len(pass_attempts) if len(pass_attempts) > 0 else 0
            
            # Explosive plays (>15 yards)
            explosive = off_plays[off_plays['yards_gained'] > 15]
            explosive_rate = len(explosive) / total_plays if total_plays > 0 else 0
            
            # Drive metrics (simplified - count drives by possession changes)
            drives = off_plays.groupby(off_plays['drive'].notna().cumsum())
            n_drives = len(drives)
            td_drives = drives.apply(lambda x: (x['touchdown'] == 1).any()).sum()
            td_rate = td_drives / n_drives if n_drives > 0 else 0
            avg_plays_per_drive = total_plays / n_drives if n_drives > 0 else 0
            
            # Score
            score = game_sched[f'{team_role}_score']
            
            results.append({
                'game_id': game_id,
                'season': season,
                'week': game_sched['week'],
                'team': team.upper(),
                'team_role': team_role,
                'score': score,
                'pass_rate': pass_rate,
                'epa_mean': epa_mean,
                'pressure_rate': pressure_rate,
                'comp_rate': comp_rate,
                'explosive_rate': explosive_rate,
                'td_rate': td_rate,
                'avg_plays_per_drive': avg_plays_per_drive,
            })
    
    df = pd.DataFrame(results)
    
    # Pivot to home/away format
    home_df = df[df['team_role'] == 'home'].copy()
    away_df = df[df['team_role'] == 'away'].copy()
    
    # Merge on game_id
    merged = home_df.merge(away_df, on=['game_id', 'season', 'week'], suffixes=('_home', '_away'))
    
    # Rename columns to match sim format
    result = pd.DataFrame({
        'game_id': merged['game_id'],
        'season': merged['season'],
        'week': merged['week'],
        'home_team': merged['team_home'],
        'away_team': merged['team_away'],
        'home_score': merged['score_home'],
        'away_score': merged['score_away'],
        'home_pass_rate_real': merged['pass_rate_home'],
        'home_epa_real': merged['epa_mean_home'],
        'home_pressure_rate_real': merged['pressure_rate_home'],
        'home_comp_rate_real': merged['comp_rate_home'],
        'home_explosive_rate_real': merged['explosive_rate_home'],
        'home_td_rate_real': merged['td_rate_home'],
        'home_avg_plays_per_drive_real': merged['avg_plays_per_drive_home'],
        'away_pass_rate_real': merged['pass_rate_away'],
        'away_epa_real': merged['epa_mean_away'],
        'away_pressure_rate_real': merged['pressure_rate_away'],
        'away_comp_rate_real': merged['comp_rate_away'],
        'away_explosive_rate_real': merged['explosive_rate_away'],
        'away_td_rate_real': merged['td_rate_away'],
        'away_avg_plays_per_drive_real': merged['avg_plays_per_drive_away'],
    })
    
    return result


def _detect_patterns(sim_df: pd.DataFrame, actual_df: pd.DataFrame) -> Dict:
    """Detect patterns and calibration issues."""
    merged = sim_df.merge(actual_df, on=['season', 'week', 'home_team', 'away_team'], how='inner')
    
    patterns = {
        'pressure_underestimated': False,
        'epa_inflated': False,
        'completion_too_high': False,
        'defensive_variance_low': False,
        'totals_too_high': False,
    }
    
    # Check pressure rates
    if 'home_pressure_rate_real' in merged.columns:
        sim_pressure = merged[['home_pressure_rate', 'away_pressure_rate']].mean().mean()
        real_pressure = merged[['home_pressure_rate_real', 'away_pressure_rate_real']].mean().mean()
        if sim_pressure < real_pressure * 0.8:  # Sim is >20% low
            patterns['pressure_underestimated'] = True
            patterns['pressure_gap'] = real_pressure - sim_pressure
    
    # Check EPA inflation
    if 'home_epa_real' in merged.columns:
        sim_epa = merged[['home_input_epa', 'away_input_epa']].mean().mean()
        real_epa = merged[['home_epa_real', 'away_epa_real']].mean().mean()
        if sim_epa > real_epa + 0.1:  # Sim is >0.1 EPA higher
            patterns['epa_inflated'] = True
            patterns['epa_gap'] = sim_epa - real_epa
    
    # Check completion rates
    if 'home_comp_rate_real' in merged.columns:
        sim_comp = merged[['home_clean_comp_rate', 'away_clean_comp_rate']].mean().mean()
        real_comp = merged[['home_comp_rate_real', 'away_comp_rate_real']].mean().mean()
        if sim_comp > real_comp + 0.05:  # Sim is >5% higher
            patterns['completion_too_high'] = True
        elif sim_comp < real_comp - 0.05:  # Sim is >5% lower
            patterns['completion_too_low'] = True
    
    # Check totals
    if 'home_score' in merged.columns:
        sim_total = (merged['home_score_sim'] + merged['away_score_sim']).mean()
        real_total = (merged['home_score'] + merged['away_score']).mean()
        if sim_total > real_total + 3:  # Sim is >3 points higher
            patterns['totals_too_high'] = True
            patterns['total_gap'] = sim_total - real_total
    
    return patterns


def _per_team_analysis(sim_df: pd.DataFrame, actual_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze per-team patterns."""
    merged = sim_df.merge(actual_df, on=['season', 'week', 'home_team', 'away_team'], how='inner')
    
    # Stack home and away
    home_rows = merged[['home_team', 'home_pressure_rate', 'home_pressure_rate_real',
                       'home_epa_real', 'home_input_epa', 'home_score_sim', 'home_score']].copy()
    home_rows.columns = ['team', 'pressure_sim', 'pressure_real', 'epa_real', 'epa_input', 'score_sim', 'score_real']
    
    away_rows = merged[['away_team', 'away_pressure_rate', 'away_pressure_rate_real',
                        'away_epa_real', 'away_input_epa', 'away_score_sim', 'away_score']].copy()
    away_rows.columns = ['team', 'pressure_sim', 'pressure_real', 'epa_real', 'epa_input', 'score_sim', 'score_real']
    
    stacked = pd.concat([home_rows, away_rows], ignore_index=True)
    
    # Aggregate per team
    team_agg = stacked.groupby('team').agg({
        'pressure_sim': 'mean',
        'pressure_real': 'mean',
        'epa_real': 'mean',
        'epa_input': 'mean',
        'score_sim': 'mean',
        'score_real': 'mean',
    }).reset_index()
    
    team_agg['pressure_bias'] = team_agg['pressure_sim'] - team_agg['pressure_real']
    team_agg['epa_bias'] = team_agg['epa_input'] - team_agg['epa_real']
    team_agg['score_bias'] = team_agg['score_sim'] - team_agg['score_real']
    
    return team_agg.sort_values('epa_bias', ascending=False)


def main():
    parser = argparse.ArgumentParser(description="Deep trace analysis comparing to NFLfastR")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--weeks", type=str, required=True)
    parser.add_argument("--team", type=str, default=None, help="Filter to specific team")
    parser.add_argument("--traces-dir", type=str, default=None)
    args = parser.parse_args()
    
    weeks = _parse_weeks(args.weeks)
    
    # Load traces
    if args.traces_dir:
        traces_dir = Path(args.traces_dir)
    else:
        traces_dir = Path(__file__).parent / "artifacts" / "traces"
    
    print(f"📂 Loading traces from {traces_dir}...")
    trace_files = list(traces_dir.glob("*.jsonl"))
    print(f"   Found {len(trace_files)} trace files")
    
    sim_data = []
    for trace_file in trace_files:
        data = _load_trace_file(trace_file)
        if data and data['season'] == args.season and data['week'] in weeks:
            if args.team is None or data['home_team'] == args.team.upper() or data['away_team'] == args.team.upper():
                sim_data.append(data)
    
    if not sim_data:
        print("❌ No matching trace data found")
        return
    
    sim_df = pd.DataFrame(sim_data)
    print(f"✅ Loaded {len(sim_df)} simulated games")
    
    # Load actuals
    print(f"\n📥 Loading NFLfastR actuals...")
    try:
        actual_df = _load_actuals_deep(args.season, weeks)
        print(f"✅ Loaded {len(actual_df)} actual games")
    except Exception as e:
        print(f"❌ Error loading actuals: {e}")
        return
    
    # Merge and analyze
    print(f"\n🔍 Analyzing patterns...")
    patterns = _detect_patterns(sim_df, actual_df)
    team_analysis = _per_team_analysis(sim_df, actual_df)
    
    # Print findings
    print("\n" + "="*70)
    print("PATTERN DETECTION RESULTS")
    print("="*70)
    
    if patterns.get('pressure_underestimated'):
        gap = patterns.get('pressure_gap', 0)
        print(f"\n⚠️  PRESSURE UNDERESTIMATED")
        print(f"   Sim pressure rate is {gap:.3f} lower than actual")
        print(f"   Recommendation: Increase base pressure rate or OL/DL mismatch coefficient")
    
    if patterns.get('epa_inflated'):
        gap = patterns.get('epa_gap', 0)
        print(f"\n⚠️  EPA INFLATED")
        print(f"   Sim EPA is {gap:.3f} higher than actual")
        print(f"   Recommendation: Increase defensive variance damping or reduce offensive efficiency")
    
    if patterns.get('totals_too_high'):
        gap = patterns.get('total_gap', 0)
        print(f"\n⚠️  TOTALS TOO HIGH")
        print(f"   Sim total points is {gap:.1f} higher than actual")
        print(f"   Recommendation: Reduce drive efficiency or increase defensive stops")
    
    print(f"\n📊 Top 10 teams by EPA bias (simulated - actual):")
    print(team_analysis.head(10).to_string(index=False))
    
    # Save results
    output_dir = Path(__file__).parent / "artifacts" / "trace_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    team_analysis.to_csv(output_dir / "per_team_bias.csv", index=False)
    
    # Save merged comparison
    merged = sim_df.merge(actual_df, on=['season', 'week', 'home_team', 'away_team'], how='inner')
    merged.to_csv(output_dir / "full_comparison.csv", index=False)
    
    print(f"\n✅ Results saved to {output_dir}/")


if __name__ == "__main__":
    main()

