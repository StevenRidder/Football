"""
Complete workflow to refit isotonic calibrators on 2022-2024 only (no 2025 leakage).

Steps:
1. Run backtest on 2022-2024 data
2. Fit isotonic calibrators on that data
3. Save as main calibrator file (used by backtest_all_games_conviction.py)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import time

def run_backtest_2022_2024():
    """Run backtest on 2022-2024 data."""
    print("="*70)
    print("STEP 1: Running backtest on 2022-2024 data")
    print("="*70)
    
    script_path = Path(__file__).parent.parent / "backtest_2023_2024.py"
    
    print(f"\n📊 Running: {script_path}")
    print("   This will generate artifacts/backtest_2022_2024.csv")
    print("   (Note: script name still says 2023_2024 but it loads 2022-2024)\n")
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(script_path.parent),
        capture_output=False
    )
    
    if result.returncode != 0:
        print("❌ Backtest failed!")
        return False
    
    # Check if file was created
    output_file = Path(__file__).parent.parent / "artifacts" / "backtest_2022_2024.csv"
    if not output_file.exists():
        print("❌ Backtest output file not found!")
        return False
    
    print(f"\n✅ Backtest complete: {output_file}")
    print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
    return True

def fit_calibrators():
    """Fit isotonic calibrators on 2022-2024 data."""
    print("\n" + "="*70)
    print("STEP 2: Fitting isotonic calibrators on 2022-2024 data")
    print("="*70)
    
    script_path = Path(__file__).parent / "fit_isotonic_on_2022_2024_only.py"
    
    print(f"\n🔧 Running: {script_path}")
    print("   This will fit calibrators on 2022-2024 ONLY\n")
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(script_path.parent),
        capture_output=False
    )
    
    if result.returncode != 0:
        print("❌ Calibrator fitting failed!")
        return False
    
    # Check if file was created
    calibrator_file = Path(__file__).parent.parent / "artifacts" / "isotonic_calibrators.pkl"
    if not calibrator_file.exists():
        print("❌ Calibrator file not found!")
        return False
    
    print(f"\n✅ Calibrators fitted and saved: {calibrator_file}")
    return True

if __name__ == "__main__":
    print("\n" + "="*70)
    print("REFIT CALIBRATORS - NO LEAKAGE WORKFLOW")
    print("="*70)
    print("\nThis script will:")
    print("  1. Run backtest on 2022-2024 data")
    print("  2. Fit isotonic calibrators on that data ONLY")
    print("  3. Save calibrators (will be used by backtest_all_games_conviction.py)")
    print("\n⚠️  This ensures no 2025 data leakage in calibration")
    print("="*70)
    
    input("\nPress Enter to continue...")
    
    # Step 1: Run backtest
    if not run_backtest_2022_2024():
        print("\n❌ Workflow failed at Step 1")
        sys.exit(1)
    
    # Step 2: Fit calibrators
    if not fit_calibrators():
        print("\n❌ Workflow failed at Step 2")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETE")
    print("="*70)
    print("\nCalibrators are now fitted on 2022-2024 ONLY:")
    print("  • No 2025 data in training set ✅")
    print("  • 2025 weeks 1-8 will be truly out-of-sample ✅")
    print("\nNext: Run backtest_all_games_conviction.py to test on 2025 data")
    print("="*70)

