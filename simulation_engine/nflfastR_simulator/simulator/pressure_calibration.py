"""
Pressure Calibration Module: Team-specific pressure baselines with situational adjustments.

This module provides:
1. Rolling team-specific pressure baselines from nflfastR
2. OL vs DL mismatch adjustments
3. Situational multipliers (3rd & long, two-minute drill, etc.)
4. Injury adjustments

Integration:
    - Weekly: Run prep_pressure_rates.py to compute baselines
    - Per-snap: Call pressure_prob() in play_simulator.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import math
import pandas as pd
import numpy as np


@dataclass
class PressureConfig:
    """Configuration for pressure calibration."""
    # Rolling windows
    weeks_lookback: int = 5                 # team form window
    ema_alpha: float = 0.45                 # recency weight for baselines
    
    # Mismatch scaling (tuneable)
    ol_dl_beta: float = 0.018               # strength of OL vs DL effect on pressure prob
    injury_ol_per_starter_out: float = 0.05 # +5% pressure prob per missing OL starter
    injury_dl_per_starter_out: float = -0.05 # -5% pressure prob per missing DL starter
    
    # Situation multipliers (tuneable, applied multiplicatively)
    third_long_mult: float = 1.25           # 3rd & 7+
    two_minute_trailing_mult: float = 1.20  # Q2/Q4 last 2 min and trailing
    pass_commit_trail_10p_mult: float = 1.10 # trailing by 10+ in 2H
    play_action_discount: float = 0.90       # PA reduces pressure rate slightly
    shotgun_uptick: float = 1.05            # shotgun raises pressure rate slightly
    
    # Clamps
    min_pressure: float = 0.05
    max_pressure: float = 0.70


class PressureCalibrator:
    """
    Builds rolling team-specific pressure baselines and provides a per-snap
    adjusted pressure probability.
    
    Inputs expected from weekly preprocess (nflfastR-derived):
      - offense_team, defense_team, week, season
      - off_pr_allowed: offense pressure allowed rate (dropback-based)
      - def_pr_created: defense pressure created rate (dropback-based)
    """
    
    def __init__(self, config: Optional[PressureConfig] = None):
        self.cfg = config or PressureConfig()
        
        # Latest rolling for quick access: team -> float
        self.off_current: Dict[str, float] = {}
        self.def_current: Dict[str, float] = {}
    
    def fit_from_weekly(self, df_weekly: pd.DataFrame, season: int, week: int) -> None:
        """
        df_weekly columns (minimum):
          team, season, week, off_pr_allowed, def_pr_created
        
        Builds rolling EMA baselines through the given (season, week).
        """
        req = {"team", "season", "week", "off_pr_allowed", "def_pr_created"}
        missing = req - set(df_weekly.columns)
        if missing:
            raise ValueError(f"df_weekly missing columns: {missing}")
        
        # Only up to target week
        d = df_weekly[
            (df_weekly["season"] == season) & 
            (df_weekly["week"] <= week)
        ].copy()
        
        if len(d) == 0:
            raise ValueError(f"No data found for season {season}, week {week}")
        
        # Build rolling with EMA, last N weeks
        def _ema(series: pd.Series, alpha: float) -> float:
            if series.empty:
                return float("nan")
            val = series.iloc[0]
            for x in series.iloc[1:]:
                val = alpha * x + (1 - alpha) * val
            return float(val)
        
        for tm, g in d.groupby("team"):
            g = g.sort_values(["season", "week"])
            
            # Use last K weeks window up to 'week'
            g_tail = g.tail(self.cfg.weeks_lookback)
            
            off = _ema(g_tail["off_pr_allowed"], self.cfg.ema_alpha)
            de = _ema(g_tail["def_pr_created"], self.cfg.ema_alpha)
            
            # Fallback to mean if EMA returns NaN
            if math.isnan(off):
                off = g["off_pr_allowed"].mean()
            if math.isnan(de):
                de = g["def_pr_created"].mean()
            
            # Safety defaults
            off = float(off) if not math.isnan(off) else 0.21
            de = float(de) if not math.isnan(de) else 0.21
            
            self.off_current[tm] = max(0.05, min(0.55, off))
            self.def_current[tm] = max(0.05, min(0.55, de))
    
    def pressure_prob(
        self,
        offense_team: str,
        defense_team: str,
        *,
        down: int,
        ydstogo: int,
        quarter: int,
        sec_left_in_quarter: int,
        offense_trailing_by: int,
        half: int,
        play_action: bool = False,
        shotgun: bool = False,
        injuries: Optional[Dict[str, Dict[str, int]]] = None,
        ol_rank: Optional[int] = None,
        dl_rank: Optional[int] = None,
    ) -> float:
        """
        Returns adjusted pressure probability for the snap.
        
        injuries: {
          'OL': {'starters_out': int},
          'DL': {'starters_out': int}
        }
        
        Rankings: lower is better line (e.g., 1 = best unit). If provided, used for mismatch.
        """
        # 1) Base from blended offense + defense
        off_base = self.off_current.get(offense_team, 0.21)
        def_base = self.def_current.get(defense_team, 0.21)
        base = (off_base + def_base) / 2.0
        
        # 2) OL vs DL mismatch
        # If ranks provided, convert rank delta to multiplier around 1
        mismatch_mult = 1.0
        if ol_rank is not None and dl_rank is not None:
            # Positive means DL better than OL
            rank_delta = (dl_rank - ol_rank)
            mismatch_mult *= (1.0 + self.cfg.ol_dl_beta * rank_delta)
        
        # 3) Injuries: missing OL raises pressure; missing DL lowers pressure
        if injuries:
            ol_out = injuries.get("OL", {}).get("starters_out", 0)
            dl_out = injuries.get("DL", {}).get("starters_out", 0)
            mismatch_mult *= (1.0 + self.cfg.injury_ol_per_starter_out * ol_out)
            mismatch_mult *= (1.0 + self.cfg.injury_dl_per_starter_out * dl_out)
        
        p = base * mismatch_mult
        
        # 4) Situation multipliers
        # Third and long
        if down == 3 and ydstogo >= 7:
            p *= self.cfg.third_long_mult
        
        # Trailing late in half (two-minute)
        if sec_left_in_quarter <= 120 and quarter in (2, 4) and offense_trailing_by > 0:
            p *= self.cfg.two_minute_trailing_mult
        
        # Trailing big after halftime
        if half == 2 and offense_trailing_by >= 10:
            p *= self.cfg.pass_commit_trail_10p_mult
        
        # Formation effects
        if play_action:
            p *= self.cfg.play_action_discount
        
        if shotgun:
            p *= self.cfg.shotgun_uptick
        
        # Clamp
        p = max(self.cfg.min_pressure, min(self.cfg.max_pressure, p))
        
        return float(p)
    
    def snapshot(self) -> pd.DataFrame:
        """Return current team baselines for quick inspection."""
        rows = []
        all_teams = sorted(set(list(self.off_current.keys()) + list(self.def_current.keys())))
        
        for tm in all_teams:
            rows.append({
                "team": tm,
                "off_pr_allowed": self.off_current.get(tm, float("nan")),
                "def_pr_created": self.def_current.get(tm, float("nan")),
            })
        
        return pd.DataFrame(rows)

