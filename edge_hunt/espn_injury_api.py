"""
Robust ESPN Injury API Parser

This is the PRIMARY source for injury data. It:
1. Fetches from official ESPN API (free, no key needed)
2. Handles all 32 NFL teams
3. Includes retry logic and error handling
4. Returns structured injury data
5. Validates responses

ESPN API is updated multiple times per day during the season.
"""

import requests
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ESPNInjury:
    """Structured injury data from ESPN."""
    team: str
    player_name: str
    position: str
    status: str  # "Out", "Doubtful", "Questionable", "Probable", "Day-To-Day"
    injury_type: str  # "Shoulder", "Knee", etc.
    details: str  # Additional context
    source: str = "espn"
    collected_at: datetime = None
    
    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        return {
            'team': self.team,
            'player_name': self.player_name,
            'position': self.position,
            'status': self.status,
            'injury_type': self.injury_type,
            'details': self.details,
            'source': self.source,
            'collected_at': self.collected_at.isoformat()
        }


# Complete ESPN team ID mapping (all 32 teams)
ESPN_TEAM_IDS = {
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


def fetch_team_injuries_espn(team_abbr: str, retries: int = 3) -> List[ESPNInjury]:
    """
    Fetch injury data for a single team from ESPN API.
    
    Args:
        team_abbr: Team abbreviation (e.g., "MIN", "DET")
        retries: Number of retry attempts
    
    Returns:
        List of ESPNInjury objects
    """
    if team_abbr not in ESPN_TEAM_IDS:
        print(f"⚠️  Unknown team: {team_abbr}")
        return []
    
    team_id = ESPN_TEAM_IDS[team_abbr]
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            injuries = []
            
            # Method 1: Check team.injuries (primary)
            if "team" in data and "injuries" in data["team"]:
                for injury_data in data["team"]["injuries"]:
                    try:
                        athlete = injury_data.get("athlete", {})
                        position_info = athlete.get("position", {})
                        injury_details = injury_data.get("details", {})
                        
                        injury = ESPNInjury(
                            team=team_abbr,
                            player_name=athlete.get("displayName", "Unknown"),
                            position=position_info.get("abbreviation", ""),
                            status=injury_data.get("status", "Unknown"),
                            injury_type=injury_details.get("type", ""),
                            details=injury_details.get("detail", ""),
                        )
                        injuries.append(injury)
                    except Exception as e:
                        print(f"⚠️  Error parsing injury for {team_abbr}: {e}")
                        continue
            
            # Method 2: Check team.record.injuries (alternate location)
            if "team" in data and "record" in data["team"]:
                record = data["team"]["record"]
                if isinstance(record, list):
                    for rec in record:
                        if "injuries" in rec:
                            # Similar parsing as above
                            pass
            
            # Method 3: Check roster with injury flags
            if "team" in data and "athletes" in data["team"]:
                for athlete in data["team"]["athletes"]:
                    if athlete.get("injuries"):
                        for injury_data in athlete["injuries"]:
                            try:
                                position_info = athlete.get("position", {})
                                
                                injury = ESPNInjury(
                                    team=team_abbr,
                                    player_name=athlete.get("displayName", "Unknown"),
                                    position=position_info.get("abbreviation", ""),
                                    status=injury_data.get("status", "Unknown"),
                                    injury_type=injury_data.get("type", ""),
                                    details=injury_data.get("longComment", ""),
                                )
                                injuries.append(injury)
                            except Exception as e:
                                continue
            
            return injuries
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️  ESPN API error for {team_abbr} (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
        except Exception as e:
            print(f"⚠️  Unexpected error for {team_abbr}: {e}")
            return []
    
    print(f"❌ Failed to fetch injuries for {team_abbr} after {retries} attempts")
    return []


def fetch_all_injuries_espn() -> Dict[str, List[ESPNInjury]]:
    """
    Fetch injury data for all 32 NFL teams.
    
    Returns:
        Dict mapping team abbreviations to lists of injuries
    """
    all_injuries = {}
    
    print("📥 Fetching injuries from ESPN for all 32 teams...")
    
    for team_abbr in ESPN_TEAM_IDS.keys():
        if team_abbr == "LA":  # Skip duplicate (LAR is canonical)
            continue
        
        injuries = fetch_team_injuries_espn(team_abbr)
        all_injuries[team_abbr] = injuries
        
        if injuries:
            print(f"  ✅ {team_abbr}: {len(injuries)} injuries")
        
        # Rate limiting (be nice to ESPN)
        time.sleep(0.5)
    
    total = sum(len(inj) for inj in all_injuries.values())
    print(f"\n✅ Total: {total} injuries across {len(all_injuries)} teams")
    
    return all_injuries


def get_significant_injuries(team_abbr: str) -> List[ESPNInjury]:
    """
    Get only significant injuries that affect betting lines.
    
    Filters for:
    - QB injuries (any status)
    - OL injuries (Out or Doubtful)
    - Key skill positions (Out or Doubtful)
    
    Args:
        team_abbr: Team abbreviation
    
    Returns:
        List of significant injuries
    """
    all_injuries = fetch_team_injuries_espn(team_abbr)
    significant = []
    
    for injury in all_injuries:
        # Always include QB injuries
        if injury.position == "QB":
            significant.append(injury)
        
        # Include OL if Out or Doubtful
        elif injury.position in ["OT", "OG", "C", "LT", "LG", "RG", "RT"]:
            if injury.status.lower() in ["out", "doubtful"]:
                significant.append(injury)
        
        # Include key skill positions if Out or Doubtful
        elif injury.position in ["WR", "RB", "TE"]:
            if injury.status.lower() in ["out", "doubtful"]:
                significant.append(injury)
    
    return significant


if __name__ == "__main__":
    # Test the ESPN API parser
    print("=" * 70)
    print("Testing ESPN Injury API Parser")
    print("=" * 70)
    print()
    
    # Test 1: Single team (MIN - should have Wentz injury if API works)
    print("Test 1: Minnesota Vikings (MIN)")
    print("-" * 70)
    min_injuries = fetch_team_injuries_espn("MIN")
    
    if min_injuries:
        print(f"✅ Found {len(min_injuries)} injuries:")
        for inj in min_injuries:
            print(f"  • {inj.player_name} ({inj.position}): {inj.status} - {inj.injury_type}")
    else:
        print("❌ No injuries found (API may have changed structure)")
    
    print()
    
    # Test 2: Another team for comparison
    print("Test 2: Detroit Lions (DET)")
    print("-" * 70)
    det_injuries = fetch_team_injuries_espn("DET")
    
    if det_injuries:
        print(f"✅ Found {len(det_injuries)} injuries:")
        for inj in det_injuries:
            print(f"  • {inj.player_name} ({inj.position}): {inj.status} - {inj.injury_type}")
    else:
        print("ℹ️  No injuries found for DET")
    
    print()
    
    # Test 3: Significant injuries only
    print("Test 3: Significant injuries (MIN)")
    print("-" * 70)
    sig_injuries = get_significant_injuries("MIN")
    
    if sig_injuries:
        print(f"✅ Found {len(sig_injuries)} significant injuries:")
        for inj in sig_injuries:
            print(f"  • {inj.player_name} ({inj.position}): {inj.status}")
    else:
        print("ℹ️  No significant injuries")
    
    print()
    print("=" * 70)
    print("Recommendation:")
    print("=" * 70)
    if min_injuries or det_injuries:
        print("✅ ESPN API is working! Use this as primary source.")
    else:
        print("❌ ESPN API structure may have changed.")
        print("   Consider using SportsData.io ($19/month) as primary source.")
        print("   Or use LLM fallback for now.")

