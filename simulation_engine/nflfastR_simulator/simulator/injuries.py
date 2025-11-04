"""
Weekly Injuries Module: Apply injury multipliers to team performance.

Loads weekly injury data and applies multipliers to:
- QB downgrade (completion %, INT rate, sack rate)
- WR room depth (completion %, explosive plays)
- OL starters out (pressure rate, sack rate, run yards)
- CB room attrition (completion %, INT rate)
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional


class InjuryLoader:
    """Load and apply weekly injury data."""

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize injury loader.
        
        Args:
            data_dir: Path to data directory (default: data/nflfastR)
        """
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
        else:
            self.data_dir = Path(data_dir)

        self._cache = {}

    def load_weekly_injuries(self, season: int, week: int) -> pd.DataFrame:
        """
        Load weekly injury data.
        
        Expected CSV format:
        - team: Team abbreviation
        - season: Season year
        - week: Week number
        - qb_downgrade: 0.0-1.0 (1.0 = starter, 0.5 = backup, 0.0 = 3rd string)
        - wr_depth_loss: 0.0-1.0 (1.0 = full depth, 0.5 = key WR out)
        - ol_starters_out: 0-5 (number of OL starters out)
        - cb_starters_out: 0-4 (number of CB starters out)
        
        Returns:
            DataFrame with injury data
        """
        injury_file = self.data_dir / "weekly_injuries.csv"

        if not injury_file.exists():
            # Return empty DataFrame with defaults
            return pd.DataFrame(columns=['team', 'season', 'week', 'qb_downgrade',
                                         'wr_depth_loss', 'ol_starters_out', 'cb_starters_out'])

        df = pd.read_csv(injury_file)
        weekly = df[
            (df['season'] == season) &
            (df['week'] == week)
        ].copy()

        return weekly

    def get_team_multipliers(self, team: str, season: int, week: int) -> Dict[str, float]:
        """
        Get injury multipliers for a team.
        
        Returns:
            Dict with multipliers:
            - qb_completion_mult: Multiplier for completion %
            - qb_int_mult: Multiplier for INT rate
            - qb_sack_mult: Multiplier for sack rate
            - wr_completion_mult: Multiplier for completion %
            - wr_explosive_mult: Multiplier for explosive play rate
            - ol_pressure_mult: Multiplier for pressure rate
            - ol_run_mult: Multiplier for run yards
            - cb_completion_allow_mult: Multiplier for completion % allowed
            - cb_int_mult: Multiplier for INT rate
        """
        injuries = self.load_weekly_injuries(season, week)
        team_inj = injuries[injuries['team'] == team]

        if len(team_inj) == 0:
            # No injuries: all multipliers = 1.0
            return {
                'qb_completion_mult': 1.0,
                'qb_int_mult': 1.0,
                'qb_sack_mult': 1.0,
                'wr_completion_mult': 1.0,
                'wr_explosive_mult': 1.0,
                'ol_pressure_mult': 1.0,
                'ol_run_mult': 1.0,
                'cb_completion_allow_mult': 1.0,
                'cb_int_mult': 1.0,
            }

        row = team_inj.iloc[0]

        # QB downgrade: affects completion, INT, sack rates
        qb_downgrade = float(row.get('qb_downgrade', 1.0))
        qb_completion_mult = 0.90 + (qb_downgrade * 0.10)  # 0.90-1.0
        qb_int_mult = 2.0 - qb_downgrade  # 1.0-2.0 (more INTs for backups)
        qb_sack_mult = 1.5 - (qb_downgrade * 0.5)  # 1.0-1.5 (more sacks)

        # WR depth loss: affects completion and explosive plays
        wr_depth_loss = float(row.get('wr_depth_loss', 1.0))
        wr_completion_mult = 0.95 + (wr_depth_loss * 0.05)  # 0.95-1.0
        wr_explosive_mult = 0.90 + (wr_depth_loss * 0.10)  # 0.90-1.0

        # OL starters out: affects pressure and run yards
        ol_starters_out = int(row.get('ol_starters_out', 0))
        ol_pressure_mult = 1.0 + (ol_starters_out * 0.15)  # +15% per starter out
        ol_run_mult = 1.0 - (ol_starters_out * 0.08)  # -8% per starter out

        # CB starters out: affects completion allowed and INT rate
        cb_starters_out = int(row.get('cb_starters_out', 0))
        cb_completion_allow_mult = 1.0 + (cb_starters_out * 0.10)  # +10% completion allowed
        cb_int_mult = 1.0 - (cb_starters_out * 0.15)  # -15% INT rate

        return {
            'qb_completion_mult': float(qb_completion_mult),
            'qb_int_mult': float(qb_int_mult),
            'qb_sack_mult': float(qb_sack_mult),
            'wr_completion_mult': float(wr_completion_mult),
            'wr_explosive_mult': float(wr_explosive_mult),
            'ol_pressure_mult': float(ol_pressure_mult),
            'ol_run_mult': float(ol_run_mult),
            'cb_completion_allow_mult': float(cb_completion_allow_mult),
            'cb_int_mult': float(cb_int_mult),
        }


# Singleton instance
_injury_loader = None

def get_injury_loader() -> InjuryLoader:
    """Get singleton injury loader instance."""
    global _injury_loader
    if _injury_loader is None:
        _injury_loader = InjuryLoader()
    return _injury_loader

