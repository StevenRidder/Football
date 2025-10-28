"""
QB and Offensive Line Features for NFL Betting

Tracks quarterback status and offensive line continuity changes that occur
during the week (Wed-Fri injury reports). These have documented, measurable
effects on scoring and spreads:

1. QB Drop-Off: Backup QB = -6 to -10 points, -3 to -5 ATS
2. OL Injuries: Loss of 2+ starters = -2 to -4 points
3. Key Skill Position: Loss of WR1/RB1 = -1 to -3 points

These signals often appear in injury reports before the market fully prices them,
creating CLV opportunities.

Data Sources:
- ESPN Depth Charts API (free)
- ESPN Injuries API (free)
- nflfastR roster data (free)
"""

from __future__ import annotations
import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import pandas as pd


@dataclass
class QBStatus:
    """QB status for a team."""
    team: str
    starter_name: str
    starter_status: str  # "active", "questionable", "doubtful", "out"
    backup_name: str
    is_backup_starting: bool
    qb_drop_off_pts: float  # Expected point reduction if backup plays


@dataclass
class OLStatus:
    """Offensive line status for a team."""
    team: str
    starters_out: int  # Number of starting OL out
    ol_penalty_pts: float  # Expected point reduction


@dataclass
class TeamInjuryStatus:
    """Complete injury status for a team."""
    team: str
    collected_at_utc: datetime
    qb_status: QBStatus
    ol_status: OLStatus
    total_impact_pts: float  # Combined QB + OL impact


# QB quality tiers (approximate EPA per play)
QB_TIERS = {
    # Elite QBs (top 5)
    "elite": ["P.Mahomes", "J.Allen", "L.Jackson", "J.Burrow", "J.Herbert"],
    # Good QBs (top 15)
    "good": ["D.Prescott", "T.Tagovailoa", "B.Purdy", "C.Stroud", "J.Hurts",
             "M.Stafford", "K.Cousins", "G.Smith", "J.Goff", "D.Carr"],
    # Average QBs
    "average": ["B.Mayfield", "D.Jones", "J.Love", "T.Lawrence", "A.Richardson",
                "C.Williams", "J.Daniels", "B.Nix", "D.Prescott"],
    # Below average / backups
    "below_average": []  # Everyone else
}


def get_qb_tier(qb_name: str) -> str:
    """Get QB tier for quality assessment."""
    for tier, qbs in QB_TIERS.items():
        if any(qb in qb_name for qb in qbs):
            return tier
    return "below_average"


def estimate_qb_drop_off(starter_tier: str, backup_tier: str) -> float:
    """
    Estimate point drop-off when backup QB plays.
    
    Research shows:
    - Elite → Backup: -8 to -10 points
    - Good → Backup: -6 to -8 points
    - Average → Backup: -4 to -6 points
    - Below Average → Backup: -2 to -3 points
    
    Args:
        starter_tier: Starter QB tier
        backup_tier: Backup QB tier
    
    Returns:
        Expected point reduction (negative)
    """
    drop_offs = {
        ("elite", "below_average"): -9.0,
        ("elite", "average"): -5.0,
        ("good", "below_average"): -7.0,
        ("good", "average"): -4.0,
        ("average", "below_average"): -5.0,
        ("average", "average"): -2.0,
        ("below_average", "below_average"): -2.5,
    }
    
    return drop_offs.get((starter_tier, backup_tier), -5.0)


def fetch_espn_injuries(team_abbr: str) -> Optional[List[Dict]]:
    """
    Fetch injury report from ESPN API.
    
    Args:
        team_abbr: Team abbreviation (e.g., "BUF")
    
    Returns:
        List of injured players or None if error
    """
    # ESPN team ID mapping (partial - add more as needed)
    TEAM_IDS = {
        "ARI": "22", "ATL": "1", "BAL": "33", "BUF": "2",
        "CAR": "29", "CHI": "3", "CIN": "4", "CLE": "5",
        "DAL": "6", "DEN": "7", "DET": "8", "GB": "9",
        "HOU": "34", "IND": "11", "JAX": "30", "KC": "12",
        "LAC": "24", "LAR": "14", "LA": "14", "LV": "13",
        "MIA": "15", "MIN": "16", "NE": "17", "NO": "18",
        "NYG": "19", "NYJ": "20", "PHI": "21", "PIT": "23",
        "SEA": "26", "SF": "25", "TB": "27", "TEN": "10",
        "WAS": "28"
    }
    
    if team_abbr not in TEAM_IDS:
        return None
    
    team_id = TEAM_IDS[team_abbr]
    
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract injuries from roster
        injuries = []
        if "team" in data and "injuries" in data["team"]:
            for injury in data["team"]["injuries"]:
                injuries.append({
                    "name": injury.get("athlete", {}).get("displayName", ""),
                    "position": injury.get("athlete", {}).get("position", {}).get("abbreviation", ""),
                    "status": injury.get("status", ""),
                    "details": injury.get("details", {}).get("type", "")
                })
        
        return injuries
    
    except Exception as e:
        print(f"⚠️  ESPN injuries API error for {team_abbr}: {e}")
        return None


def get_qb_status(team: str) -> QBStatus:
    """
    Get QB status for a team.
    
    For now, this is a simplified version. In production, you'd:
    1. Fetch from ESPN depth chart API
    2. Parse injury report for QB status
    3. Look up QB quality from nflfastR data
    
    Args:
        team: Team abbreviation
    
    Returns:
        QBStatus
    """
    injuries = fetch_espn_injuries(team)
    
    # Default: assume starter is active
    # In production, you'd parse the actual depth chart and injury report
    qb_status = QBStatus(
        team=team,
        starter_name="Unknown",
        starter_status="active",
        backup_name="Unknown",
        is_backup_starting=False,
        qb_drop_off_pts=0.0
    )
    
    if injuries:
        # Check if QB is injured
        for injury in injuries:
            if injury["position"] == "QB":
                if injury["status"] in ["Out", "Doubtful"]:
                    # Backup is starting
                    qb_status.starter_status = injury["status"].lower()
                    qb_status.is_backup_starting = True
                    
                    # Estimate drop-off (conservative -6 points)
                    qb_status.qb_drop_off_pts = -6.0
                    
                    print(f"  ⚠️  {team} QB {injury['name']} is {injury['status']}")
                    break
    
    return qb_status


def get_ol_status(team: str) -> OLStatus:
    """
    Get offensive line status for a team.
    
    Tracks number of starting OL out due to injury.
    
    Args:
        team: Team abbreviation
    
    Returns:
        OLStatus
    """
    injuries = fetch_espn_injuries(team)
    
    ol_positions = ["C", "G", "T", "OL"]
    starters_out = 0
    
    if injuries:
        for injury in injuries:
            if injury["position"] in ol_positions:
                if injury["status"] in ["Out", "Doubtful"]:
                    starters_out += 1
    
    # Penalty: -2 points per OL starter out (conservative)
    penalty = starters_out * -2.0
    
    if starters_out > 0:
        print(f"  ⚠️  {team} has {starters_out} OL starters out")
    
    return OLStatus(
        team=team,
        starters_out=starters_out,
        ol_penalty_pts=penalty
    )


def get_team_injury_status(team: str) -> TeamInjuryStatus:
    """
    Get complete injury status for a team.
    
    Args:
        team: Team abbreviation
    
    Returns:
        TeamInjuryStatus
    """
    qb_status = get_qb_status(team)
    ol_status = get_ol_status(team)
    
    total_impact = qb_status.qb_drop_off_pts + ol_status.ol_penalty_pts
    
    return TeamInjuryStatus(
        team=team,
        collected_at_utc=datetime.now(timezone.utc),
        qb_status=qb_status,
        ol_status=ol_status,
        total_impact_pts=total_impact
    )


def calculate_game_injury_adjustment(
    away_team: str, home_team: str
) -> Tuple[float, float, Dict]:
    """
    Calculate injury-based adjustments for a game.
    
    Returns:
        (spread_adjustment, total_adjustment, details)
        
        spread_adjustment: Points to add to home spread (negative = away advantage)
        total_adjustment: Points to add to total (negative = lower scoring)
        details: Dictionary with injury details
    """
    away_status = get_team_injury_status(away_team)
    home_status = get_team_injury_status(home_team)
    
    # Spread adjustment: home impact - away impact
    # If home QB out (-6) and away healthy (0), spread moves -6 toward away
    spread_adj = home_status.total_impact_pts - away_status.total_impact_pts
    
    # Total adjustment: sum of both impacts
    total_adj = away_status.total_impact_pts + home_status.total_impact_pts
    
    details = {
        "away_team": away_team,
        "home_team": home_team,
        "away_qb_drop_off": away_status.qb_status.qb_drop_off_pts,
        "away_ol_penalty": away_status.ol_status.ol_penalty_pts,
        "away_total_impact": away_status.total_impact_pts,
        "home_qb_drop_off": home_status.qb_status.qb_drop_off_pts,
        "home_ol_penalty": home_status.ol_status.ol_penalty_pts,
        "home_total_impact": home_status.total_impact_pts,
        "spread_adjustment": spread_adj,
        "total_adjustment": total_adj,
    }
    
    return spread_adj, total_adj, details


if __name__ == "__main__":
    # Test the module
    print("Testing QB/OL injury features...")
    
    # Test game: BUF @ MIA
    print("\n" + "="*80)
    print("BUF @ MIA")
    print("="*80)
    
    spread_adj, total_adj, details = calculate_game_injury_adjustment("BUF", "MIA")
    
    print(f"\nAway (BUF):")
    print(f"  QB drop-off: {details['away_qb_drop_off']:+.1f} pts")
    print(f"  OL penalty: {details['away_ol_penalty']:+.1f} pts")
    print(f"  Total impact: {details['away_total_impact']:+.1f} pts")
    
    print(f"\nHome (MIA):")
    print(f"  QB drop-off: {details['home_qb_drop_off']:+.1f} pts")
    print(f"  OL penalty: {details['home_ol_penalty']:+.1f} pts")
    print(f"  Total impact: {details['home_total_impact']:+.1f} pts")
    
    print(f"\nAdjustments:")
    print(f"  Spread: {spread_adj:+.1f} pts (add to home spread)")
    print(f"  Total: {total_adj:+.1f} pts")
    
    if abs(spread_adj) >= 3.0:
        print(f"\n✅ Significant spread edge detected!")
    if abs(total_adj) >= 3.0:
        print(f"\n✅ Significant total edge detected!")

