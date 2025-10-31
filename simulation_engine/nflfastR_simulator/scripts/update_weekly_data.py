"""
Weekly Data Update Script

Runs all extraction scripts for the latest completed week and current week.
This should be run each week before making new predictions.

Usage:
    python scripts/update_weekly_data.py [--season YYYY] [--week N]
    
If season/week not specified, uses the most recent completed week from nflfastR.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import nfl_data_py as nfl

SCRIPT_DIR = Path(__file__).parent.parent
PREPROCESSING_DIR = SCRIPT_DIR / "preprocessing"


def get_latest_week(season: int = None) -> tuple[int, int]:
    """
    Get the latest completed week from nflfastR.
    
    Returns:
        (season, week)
    """
    if season is None:
        # Get current year
        season = datetime.now().year
        
        # If before September, look at previous season
        if datetime.now().month < 9:
            season -= 1
    
    # Load schedule to find latest completed week
    schedule = nfl.import_schedules([season])
    
    if len(schedule) == 0:
        # Fall back to previous season
        schedule = nfl.import_schedules([season - 1])
        season = season - 1
    
    if len(schedule) == 0:
        raise ValueError(f"No schedule data found for {season}")
    
    # Find latest week with completed games
    latest_week = schedule['week'].max()
    
    return season, int(latest_week)


def run_extraction_script(script_name: str, season: int, week: int = None) -> bool:
    """
    Run a single extraction script.
    
    Args:
        script_name: Name of script (e.g., 'extract_yards_per_play.py')
        season: Season year
        week: Optional week number (scripts will extract all data, not just this week)
    
    Returns:
        True if successful, False otherwise
    """
    script_path = PREPROCESSING_DIR / script_name
    
    if not script_path.exists():
        print(f"❌ Script not found: {script_name}")
        return False
    
    print(f"\n{'='*80}")
    print(f"Running: {script_name}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PREPROCESSING_DIR),
            check=True,
            capture_output=False
        )
        print(f"✅ {script_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ {script_name} failed with error: {e}")
        return False


def main():
    """Update all weekly data for latest completed week."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update weekly data for NFL betting model')
    parser.add_argument('--season', type=int, help='Season year (default: auto-detect)')
    parser.add_argument('--week', type=int, help='Week number (default: latest completed)')
    parser.add_argument('--all-weeks', action='store_true', help='Extract data for all weeks in season')
    
    args = parser.parse_args()
    
    print("="*80)
    print("WEEKLY DATA UPDATE")
    print("="*80)
    
    # Get season and week
    if args.season:
        season = args.season
    else:
        season, _ = get_latest_week()
    
    if args.week:
        week = args.week
    else:
        _, week = get_latest_week(season)
    
    print(f"\n📅 Season: {season}, Week: {week}")
    
    if args.all_weeks:
        print("📊 Extracting data for all weeks in season...")
    else:
        print(f"📊 Extracting data up to week {week}...")
    
    # List of extraction scripts
    extraction_scripts = [
        'extract_yards_per_play.py',
        'extract_early_down_success.py',
        'extract_anya.py',
        'extract_turnover_regression.py',
        'extract_red_zone.py',
        'extract_special_teams.py',
        'extract_situational_factors.py',
    ]
    
    # Run each script
    results = {}
    for script in extraction_scripts:
        success = run_extraction_script(script, season, week)
        results[script] = success
    
    # Summary
    print("\n" + "="*80)
    print("UPDATE SUMMARY")
    print("="*80)
    
    successful = [s for s, r in results.items() if r]
    failed = [s for s, r in results.items() if not r]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for script in successful:
        print(f"   - {script}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for script in failed:
            print(f"   - {script}")
    
    print("\n" + "="*80)
    print("✅ WEEKLY DATA UPDATE COMPLETE")
    print("="*80)
    print(f"\n💡 Next steps:")
    print(f"   1. Verify data files in data/nflfastR/")
    print(f"   2. Run backtest or prediction with updated data")
    print("="*80)


if __name__ == "__main__":
    main()

