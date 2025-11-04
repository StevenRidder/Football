"""
PFF Data Loader - Load and merge PFF team grades

Loads scraped PFF data for OL/DL grades, WR/CB grades, etc.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional


class PFFLoader:
    """Load PFF team grades for a given season."""

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize PFF loader.
        
        Args:
            data_dir: Path to PFF data directory (default: phase1_validation/pff_raw/)
        """
        if data_dir is None:
            # Default to phase1_validation/pff_raw/
            self.data_dir = Path(__file__).parent.parent.parent / "phase1_validation" / "pff_raw"
        else:
            self.data_dir = Path(data_dir)

        self._cache = {}

    def load_season(self, season: int) -> pd.DataFrame:
        """
        Load PFF grades for a season.
        
        Args:
            season: Year (e.g., 2024)
        
        Returns:
            DataFrame with columns:
                - team: Full team name
                - abbreviation: Team abbreviation
                - pass_block_grade: OL pass blocking (0-100)
                - pass_rush_grade: DL pass rushing (0-100)
                - run_block_grade: OL run blocking (0-100)
                - run_defense_grade: DL run defense (0-100)
                - coverage_grade: Secondary coverage (0-100)
                - pass_grade: QB/WR passing (0-100)
        """
        if season in self._cache:
            return self._cache[season].copy()

        filepath = self.data_dir / f"team_grades_{season}.csv"

        if not filepath.exists():
            raise FileNotFoundError(f"PFF data not found: {filepath}")

        df = pd.read_csv(filepath)

        # Select relevant columns
        cols = [
            'team', 'abbreviation',
            'pass_block_grade', 'pass_rush_grade',
            'run_block_grade', 'run_defense_grade',
            'coverage_grade', 'pass_grade'
        ]

        df = df[cols].copy()

        # Cache for reuse
        self._cache[season] = df.copy()

        return df

    def get_team_grades(self, team: str, season: int) -> Dict[str, float]:
        """
        Get PFF grades for a specific team.
        
        Args:
            team: Team abbreviation (e.g., 'KC', 'BUF')
            season: Year
        
        Returns:
            Dict with keys:
                - ol_pass_block: OL pass blocking grade
                - ol_run_block: OL run blocking grade
                - dl_pass_rush: DL pass rush grade
                - dl_run_defense: DL run defense grade
                - secondary_coverage: Coverage grade
                - passing_offense: Pass offense grade
        """
        df = self.load_season(season)

        # FIXED: Expanded abbreviation mapping with comprehensive NFL team variations
        # PFF uses some different abbreviations across years
        abbrev_map = {
            'BAL': ['BLT', 'BAL'],  # Baltimore
            'ARI': ['ARZ', 'ARI'],  # Arizona
            'CLE': ['CLV', 'CLE'],  # Cleveland
            'HOU': ['HST', 'HOU'],  # Houston
            'LAR': ['LA', 'LAR', 'STL'],   # Los Angeles Rams (was St. Louis) - LA maps to LAR
            'LAC': ['SD', 'LAC'],   # Los Angeles Chargers (was San Diego) - stays as LAC
            'LV': ['OAK', 'LV', 'RAI'],    # Las Vegas Raiders (was Oakland)
            'WAS': ['WSH', 'WAS', 'WFT'],  # Washington (various names)
            'TB': ['TB', 'TAM'],    # Tampa Bay
            'KC': ['KC', 'KAN'],    # Kansas City
            'GB': ['GB', 'GNB'],    # Green Bay
            'NO': ['NO', 'NOR'],    # New Orleans
            'SF': ['SF', 'SFO'],    # San Francisco
            'NE': ['NE', 'NWE'],    # New England
            'NYG': ['NYG', 'NYN'],   # New York Giants
            'NYJ': ['NYJ', 'NYA'],   # New York Jets
        }

        # Try direct match first
        team_row = df[df['abbreviation'] == team]

        # If not found, try mapped abbreviations
        if team_row.empty and team in abbrev_map:
            for alt_abbrev in abbrev_map[team]:
                team_row = df[df['abbreviation'] == alt_abbrev]
                if not team_row.empty:
                    break

        # FIXED: Soft fallback with league averages and warning
        if team_row.empty:
            import warnings
            warnings.warn(
                f"PFF data not found for team {team} in season {season}. "
                f"Using league averages with reduced confidence. "
                f"Available teams: {df['abbreviation'].unique().tolist()}"
            )
            # Return league-average defaults (50th percentile grades)
            return {
                'ol_pass_block': 50.0,
                'ol_run_block': 50.0,
                'dl_pass_rush': 50.0,
                'dl_run_defense': 50.0,
                'secondary_coverage': 50.0,
                'passing_offense': 50.0,
                '_fallback_used': True,  # Flag for confidence downgrade
            }

        row = team_row.iloc[0]

        return {
            'ol_pass_block': float(row['pass_block_grade']),
            'ol_run_block': float(row['run_block_grade']),
            'dl_pass_rush': float(row['pass_rush_grade']),
            'dl_run_defense': float(row['run_defense_grade']),
            'secondary_coverage': float(row['coverage_grade']),
            'passing_offense': float(row['pass_grade']),
        }

    def get_matchup_adjustment(self,
                               offense_team: str,
                               defense_team: str,
                               season: int) -> Dict[str, float]:
        """
        Calculate matchup adjustments for OL vs DL.
        
        Args:
            offense_team: Offensive team abbreviation
            defense_team: Defensive team abbreviation
            season: Year
        
        Returns:
            Dict with keys:
                - pressure_adjustment: Expected change in pressure rate (-0.1 to +0.1)
                - run_adjustment: Expected change in run success rate
        """
        off_grades = self.get_team_grades(offense_team, season)
        def_grades = self.get_team_grades(defense_team, season)

        # Pressure adjustment: OL pass block vs DL pass rush
        # Each 10-point difference = 5% pressure change
        ol_grade = off_grades['ol_pass_block']
        dl_grade = def_grades['dl_pass_rush']
        pressure_adjustment = (dl_grade - ol_grade) * 0.005
        pressure_adjustment = max(-0.10, min(0.10, pressure_adjustment))

        # Run adjustment: OL run block vs DL run defense
        # Each 10-point difference = 0.05 yards per carry
        ol_run = off_grades['ol_run_block']
        dl_run = def_grades['dl_run_defense']
        run_adjustment = (ol_run - dl_run) * 0.005
        run_adjustment = max(-0.5, min(0.5, run_adjustment))

        return {
            'pressure_adjustment': pressure_adjustment,
            'run_adjustment': run_adjustment,
        }


# Singleton instance
_pff_loader = None

def get_pff_loader() -> PFFLoader:
    """Get singleton PFF loader instance."""
    global _pff_loader
    if _pff_loader is None:
        _pff_loader = PFFLoader()
    return _pff_loader


if __name__ == '__main__':
    # Test
    loader = PFFLoader()

    # Load 2024 data
    df = loader.load_season(2024)
    print(f"Loaded {len(df)} teams for 2024")
    print(f"\nColumns: {df.columns.tolist()}")

    # Get KC grades
    kc_grades = loader.get_team_grades('KC', 2024)
    print("\nKC 2024 grades:")
    for key, val in kc_grades.items():
        print(f"  {key}: {val:.1f}")

    # Get KC vs BUF matchup
    matchup = loader.get_matchup_adjustment('KC', 'BUF', 2024)
    print("\nKC @ BUF matchup:")
    print(f"  Pressure adjustment: {matchup['pressure_adjustment']:+.3f}")
    print(f"  Run adjustment: {matchup['run_adjustment']:+.3f}")

