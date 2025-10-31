"""
Master script to extract all missing metrics from nflfastR.

Runs all extraction scripts in sequence:
1. Yards Per Play / YPA
2. Early-Down Success Rate
3. ANY/A
4. Turnover Regression
5. Red Zone Stats
6. Special Teams
7. Situational Factors
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
EXTRACTION_SCRIPTS = [
    'extract_yards_per_play.py',
    'extract_early_down_success.py',
    'extract_anya.py',
    'extract_turnover_regression.py',
    'extract_red_zone.py',
    'extract_special_teams.py',
    'extract_situational_factors.py',
    'extract_drive_probs.py',  # Added drive probabilities extraction
]


def main():
    """Run all extraction scripts."""
    print("="*80)
    print("EXTRACT ALL METRICS FROM nflfastR")
    print("="*80)
    print()
    
    failed = []
    
    for script in EXTRACTION_SCRIPTS:
        script_path = SCRIPT_DIR / script
        if not script_path.exists():
            print(f"❌ {script} not found, skipping...")
            failed.append(script)
            continue
        
        print(f"\n{'='*80}")
        print(f"Running: {script}")
        print(f"{'='*80}")
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(SCRIPT_DIR),
                check=True,
                capture_output=False
            )
            print(f"✅ {script} completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ {script} failed with exit code {e.returncode}")
            failed.append(script)
        except Exception as e:
            print(f"❌ {script} failed with error: {e}")
            failed.append(script)
    
    print("\n" + "="*80)
    print("EXTRACTION SUMMARY")
    print("="*80)
    
    if not failed:
        print("✅ All extraction scripts completed successfully!")
    else:
        print(f"⚠️  {len(failed)} script(s) failed:")
        for script in failed:
            print(f"   - {script}")
    
    print("="*80)


if __name__ == "__main__":
    main()

