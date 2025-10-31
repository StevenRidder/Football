"""
Fix TeamProfile to exclude current week (CRITICAL LEAKAGE FIX).

TeamProfile currently loads data for week==self.week, which includes the current week.
This is look-ahead bias. We need to use only PRIOR weeks.
"""
from pathlib import Path
import re

def fix_team_profile_methods():
    """Fix all TeamProfile methods to exclude current week."""
    team_profile_path = Path(__file__).parent.parent / "simulator" / "team_profile.py"
    content = team_profile_path.read_text()
    
    print("="*70)
    print("FIXING TEAM PROFILE - EXCLUDE CURRENT WEEK")
    print("="*70)
    
    # Find all methods that load weekly data
    methods_to_fix = [
        '_load_yards_per_play',
        '_load_early_down_success',
        '_load_anya',
        '_load_turnover_regression',
        '_load_red_zone',
        '_load_special_teams',
        '_load_qb_splits',
        '_load_epa'
    ]
    
    fixes_applied = []
    
    for method_name in methods_to_fix:
        if f'def {method_name}' in content:
            # Find the method
            method_pattern = rf'def {method_name}\(self\)[^:]*:(.*?)(?=\n    def |\n\n    def |\Z)'
            match = re.search(method_pattern, content, re.DOTALL)
            
            if match:
                method_code = match.group(0)
                
                # Check if it uses week == self.week (LEAKAGE!)
                if f"week'] == self.week" in method_code or "(ypp_df['week'] == self.week)" in method_code:
                    print(f"\n   ⚠️  {method_name}: Uses current week (LEAKAGE!)")
                    fixes_applied.append(method_name)
                elif "week'] < self.week" in method_code or "(ypp_df['week'] < self.week)" in method_code:
                    print(f"\n   ✅ {method_name}: Already excludes current week")
                elif "season_file" in method_code.lower():
                    print(f"\n   ✅ {method_name}: Uses season aggregates (safe)")
                else:
                    print(f"\n   ⚠️  {method_name}: Needs review (unclear filtering)")
    
    if fixes_applied:
        print(f"\n⚠️  CRITICAL: {len(fixes_applied)} methods need fixing to exclude current week")
        print(f"   Methods: {', '.join(fixes_applied)}")
        print(f"\n   Pattern to fix:")
        print(f"   OLD: (ypp_df['week'] == self.week)")
        print(f"   NEW: (ypp_df['week'] < self.week)  # Only prior weeks")
        print(f"        Then aggregate: .mean() or similar")
    else:
        print(f"\n   ✅ No obvious leakage patterns found in checked methods")
    
    return len(fixes_applied) == 0

def check_calibrator_leakage():
    """Verify calibrator was NOT fit on 2025 data."""
    print("\n" + "="*70)
    print("CALIBRATOR LEAKAGE CHECK")
    print("="*70)
    
    fit_script = Path(__file__).parent / "fit_isotonic_calibrators.py"
    
    if not fit_script.exists():
        print("   ⚠️  fit_isotonic_calibrators.py not found")
        return False
    
    content = fit_script.read_text()
    
    # Check what file it loads
    if 'backtest_all_games_conviction.csv' in content:
        print("   ⚠️  WARNING: Calibrator loads from backtest file")
        print("      This file contains 2025 weeks 1-8 data!")
        print("      If calibrator was fit AFTER these games, it's leakage")
        print("\n   ✅ SOLUTION: Refit calibrator on 2022-2024 data only")
        print("      Then test on 2025 weeks 1-8 as truly out-of-sample")
        return False
    else:
        print("   ✅ Calibrator uses separate training data")
    
    return True

if __name__ == "__main__":
    profile_ok = fix_team_profile_methods()
    calibrator_ok = check_calibrator_leakage()
    
    print("\n" + "="*70)
    print("LEAKAGE FIX SUMMARY")
    print("="*70)
    
    if not profile_ok:
        print("\n⚠️  CRITICAL FIX NEEDED:")
        print("   TeamProfile loads current week data - this is look-ahead bias!")
        print("   Need to change week == self.week to week < self.week")
        print("   Then aggregate prior weeks before using")
    
    if not calibrator_ok:
        print("\n⚠️  CRITICAL FIX NEEDED:")
        print("   Calibrator may have been fit on 2025 data (leakage)")
        print("   Refit on 2022-2024 only, then test on 2025")

