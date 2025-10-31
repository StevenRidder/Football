"""
CRITICAL FIX: Replace all week == self.week with week < self.week

This is look-ahead bias - we're using current week data that wouldn't be available.
"""
from pathlib import Path
import re

def fix_weekly_data_loading():
    """Fix all methods in team_profile.py to exclude current week."""
    team_profile_path = Path(__file__).parent.parent / "simulator" / "team_profile.py"
    content = team_profile_path.read_text()
    
    print("="*70)
    print("CRITICAL LEAKAGE FIX - EXCLUDE CURRENT WEEK")
    print("="*70)
    
    # Patterns to find and replace
    replacements = [
        # Pattern 1: week'] == self.week
        (
            r"(\w+_df\['week'\] == self\.week)",
            r"(\1_df['week'] < self.week)  # FIXED: Only prior weeks"
        ),
        # Pattern 2: Direct week comparison in filter
        (
            r"(\(.*?week.*?==.*?self\.week.*?\))",
            lambda m: m.group(1).replace("== self.week", "< self.week") + "  # FIXED: Only prior weeks"
        )
    ]
    
    # Count occurrences
    matches = re.findall(r"week.*==.*self\.week", content)
    print(f"\n⚠️  Found {len(matches)} instances of 'week == self.week' (LEAKAGE!)")
    
    # Show which methods need fixing
    methods_needing_fix = []
    for method in ['_load_epa', '_load_pace', '_load_early_down_success', '_load_anya', 
                   '_load_turnover_regression', '_load_red_zone', '_load_special_teams']:
        method_start = content.find(f'def {method}')
        if method_start != -1:
            method_end = content.find('\n    def ', method_start + 1)
            if method_end == -1:
                method_end = len(content)
            method_code = content[method_start:method_end]
            if "week'] == self.week" in method_code:
                methods_needing_fix.append(method)
    
    print(f"\n📋 Methods needing fix: {', '.join(methods_needing_fix)}")
    
    # Create a helper function pattern that we can use
    helper_function = '''
    def _get_prior_weeks_data(self, df, team_col='posteam'):
        """
        Get aggregated data from prior weeks only (excludes current week).
        
        For week N, aggregates weeks 1 through N-1.
        For week 1, falls back to season average.
        """
        if self.week == 1:
            return pd.DataFrame()  # Will fall back to season average
        
        prior = df[
            (df[team_col] == self.team) &
            (df['season'] == self.season) &
            (df['week'] < self.week)  # KEY: Only prior weeks
        ]
        
        if len(prior) == 0:
            return pd.DataFrame()
        
        # Return mean of all prior weeks
        return prior.groupby([team_col, 'season']).mean().reset_index()
'''
    
    print(f"\n💡 Fix Strategy:")
    print(f"   1. Replace all 'week == self.week' with 'week < self.week'")
    print(f"   2. Aggregate prior weeks: .groupby().mean() or similar")
    print(f"   3. For week 1, fall back to season average")
    
    print(f"\n⚠️  This is a MANUAL fix - patterns are too complex for automatic replacement")
    print(f"   See team_profile.py lines with 'week == self.week'")

if __name__ == "__main__":
    fix_weekly_data_loading()

