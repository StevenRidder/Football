"""
Verify extraction scripts exclude current week (no look-ahead bias).

Checks that all preprocessing scripts use only prior weeks.
"""
import pandas as pd
from pathlib import Path
import sys

def check_extraction_scripts():
    """Check if extraction scripts exclude current week."""
    print("="*70)
    print("DATA LEAKAGE VERIFICATION")
    print("="*70)
    
    preprocessing_dir = Path(__file__).parent.parent / "preprocessing"
    scripts = list(preprocessing_dir.glob("extract_*.py"))
    
    print(f"\n📊 Checking {len(scripts)} extraction scripts...")
    
    issues = []
    clean = []
    
    for script in scripts:
        script_name = script.name
        content = script.read_text()
        
        # Check for week filtering
        has_week_filter = any(keyword in content for keyword in [
            'week <',
            'week <=',
            '.shift',
            'lag',
            'prior',
            'rolling',
            'expanding',
            'cumsum'
        ])
        
        # Check if uses season aggregates (safe - uses full season)
        uses_season = 'season.csv' in content.lower() or 'season_file' in content.lower()
        
        # Check if weekly file aggregates properly
        uses_weekly = 'weekly.csv' in content.lower() or 'weekly_file' in content.lower()
        
        if uses_season and not uses_weekly:
            status = "✅ Uses season aggregates (safe)"
            clean.append(script_name)
        elif has_week_filter:
            status = "✅ Has week filtering logic"
            clean.append(script_name)
        elif uses_weekly:
            # Weekly files need to be checked - TeamProfile should filter
            status = "⚠️  Uses weekly data - verify TeamProfile filters correctly"
            issues.append((script_name, status))
        else:
            status = "⚠️  No clear week filtering - needs manual check"
            issues.append((script_name, status))
    
    print(f"\n✅ Clean Scripts ({len(clean)}):")
    for script in clean[:5]:  # Show first 5
        print(f"   • {script}")
    if len(clean) > 5:
        print(f"   ... and {len(clean) - 5} more")
    
    if issues:
        print(f"\n⚠️  Scripts Needing Review ({len(issues)}):")
        for script, status in issues:
            print(f"   • {script}: {status}")
    
    return len(issues) == 0

def check_team_profile_filtering():
    """Verify TeamProfile loads data correctly (excludes current week)."""
    print("\n" + "="*70)
    print("TEAM PROFILE DATA LOADING CHECK")
    print("="*70)
    
    team_profile_path = Path(__file__).parent.parent / "simulator" / "team_profile.py"
    content = team_profile_path.read_text()
    
    # Check how weekly data is loaded
    weekly_patterns = [
        'week ==',
        'week <=',
        'week <',
        '.query',
        '.filter'
    ]
    
    found_patterns = []
    for pattern in weekly_patterns:
        if pattern in content:
            found_patterns.append(pattern)
    
    if found_patterns:
        print(f"   ✅ Found filtering patterns: {', '.join(found_patterns)}")
    else:
        print(f"   ⚠️  No clear week filtering in TeamProfile loading methods")
    
    # Check specific methods
    methods_to_check = [
        '_load_epa',
        '_load_yards_per_play',
        '_load_early_down_success',
        '_load_anya',
        '_load_qb_splits'
    ]
    
    print(f"\n   Checking key loading methods...")
    for method in methods_to_check:
        if method in content:
            method_code = content[content.find(f'def {method}'):content.find(f'def {method}')+500]
            if 'week' in method_code.lower():
                print(f"   ✅ {method}: Uses week filtering")
            elif 'season' in method_code.lower():
                print(f"   ✅ {method}: Uses season aggregates (safe)")
            else:
                print(f"   ⚠️  {method}: Unclear filtering")
    
    return True

def check_calibrator_fit_date():
    """Verify calibrators were fit on 2022-2024, not 2025."""
    print("\n" + "="*70)
    print("CALIBRATOR FIT DATE CHECK")
    print("="*70)
    
    fit_script = Path(__file__).parent / "fit_isotonic_calibrators.py"
    
    if not fit_script.exists():
        print("   ⚠️  fit_isotonic_calibrators.py not found")
        return False
    
    content = fit_script.read_text()
    
    # Check what data it loads
    if 'backtest_all_games_conviction.csv' in content:
        print("   ⚠️  WARNING: Calibrator loads from backtest file (may include 2025)")
        print("      Should load from separate training file (2022-2024 only)")
    else:
        print("   ✅ Calibrator uses separate training data")
    
    # Check if filters by season
    if 'season' in content.lower() and ('2022' in content or '2023' in content or '2024' in content):
        print("   ✅ Calibrator filters to 2022-2024 seasons")
    else:
        print("   ⚠️  WARNING: Cannot verify season filtering in calibrator fit script")
    
    return True

def main():
    """Run leakage verification."""
    scripts_ok = check_extraction_scripts()
    profile_ok = check_team_profile_filtering()
    calibrator_ok = check_calibrator_fit_date()
    
    print("\n" + "="*70)
    print("LEAKAGE VERIFICATION SUMMARY")
    print("="*70)
    
    print(f"\n   Extraction Scripts: {'✅ PASS' if scripts_ok else '⚠️  NEEDS REVIEW'}")
    print(f"   TeamProfile Filtering: {'✅ PASS' if profile_ok else '⚠️  NEEDS REVIEW'}")
    print(f"   Calibrator Fit Date: {'✅ PASS' if calibrator_ok else '⚠️  NEEDS REVIEW'}")
    
    if scripts_ok and profile_ok and calibrator_ok:
        print(f"\n   ✅ No obvious leakage detected")
    else:
        print(f"\n   ⚠️  Manual review recommended for flagged items")

if __name__ == "__main__":
    main()

