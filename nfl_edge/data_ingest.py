import os
import io
import json
from pathlib import Path
from typing import Dict, Tuple, List, Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------
# TEAM-WEEK DATA (nflverse-data release)
# ---------------------------------------------------------------------

NFLVERSE_TEAM_BASE = "https://github.com/nflverse/nflverse-data/releases/download/stats_team/"

def _read_url_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=30)
    if not r.ok:
        raise RuntimeError(f"nflverse fetch failed: {url} status={r.status_code}")
    return pd.read_csv(io.BytesIO(r.content), compression="infer")

def _num(s: pd.Series, default=0.0) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(default)

def fetch_teamweeks_live(season: int = 2025) -> pd.DataFrame:
    """
    Normalize weekly team summary stats to the columns the pipeline expects:
      season, week, team, opponent,
      off_epa_per_play, def_epa_per_play,
      off_success_rate (NaN), def_success_rate (NaN),
      points, points_allowed, plays, pass_attempts, rush_attempts
    """
    url = f"{NFLVERSE_TEAM_BASE}stats_team_week_{season}.csv"
    df = _read_url_csv(url)

    # Visibility on schema
    print("nflverse stats_team_week columns:", list(df.columns))

    need = {"season", "week", "team", "opponent_team"}
    if not need.issubset(df.columns):
        missing = sorted(need - set(df.columns))
        raise RuntimeError(f"File missing identity columns: {missing}")

    # Canonicalize
    df = df.rename(columns={"opponent_team": "opponent"})

    # Offensive volume
    for col in ["attempts", "carries", "sacks_suffered"]:
        if col not in df.columns:
            raise RuntimeError(f"File missing '{col}' required to compute offensive plays")
    attempts = _num(df["attempts"])
    carries  = _num(df["carries"])
    sacks    = _num(df["sacks_suffered"])
    plays    = attempts + carries + sacks
    plays_safe = plays.replace(0, 1e-9)

    # Offensive EPA/play
    for col in ["passing_epa", "rushing_epa"]:
        if col not in df.columns:
            raise RuntimeError(f"File missing '{col}' required to compute EPA/play")
    off_epa_per_play = (_num(df["passing_epa"]) + _num(df["rushing_epa"])) / plays_safe

    # Defensive EPA/play allowed = opponent’s offensive EPA/play
    opp_key_cols = ["season", "week", "team"]
    opp_df = df[opp_key_cols + ["attempts", "carries", "sacks_suffered", "passing_epa", "rushing_epa"]].copy()
    opp_df["opp_off_plays"] = _num(opp_df["attempts"]) + _num(opp_df["carries"]) + _num(opp_df["sacks_suffered"])
    opp_df["opp_off_plays_safe"] = opp_df["opp_off_plays"].replace(0, 1e-9)
    opp_df["opp_off_epa_per_play"] = (_num(opp_df["passing_epa"]) + _num(opp_df["rushing_epa"])) / opp_df["opp_off_plays_safe"]
    opp_df = opp_df.rename(columns={"team": "opponent"})
    joined = df.merge(
        opp_df[["season", "week", "opponent", "opp_off_epa_per_play", "opp_off_plays"]],
        on=["season", "week", "opponent"],
        how="left",
        validate="m:1",
    )
    def_epa_per_play = _num(joined["opp_off_epa_per_play"])

    # Reconstruct points scored
    td_cols = ["passing_tds", "rushing_tds", "receiving_tds", "def_tds", "special_teams_tds"]
    for c in td_cols:
        if c not in df.columns:
            df[c] = 0
    td_total = sum(_num(df[c]) for c in td_cols)

    fg_made  = _num(df.get("fg_made", 0))
    pat_made = _num(df.get("pat_made", 0))
    safeties = _num(df.get("def_safeties", 0))
    pass_2pt = _num(df.get("passing_2pt_conversions", 0))
    rush_2pt = _num(df.get("rushing_2pt_conversions", 0))
    recv_2pt = _num(df.get("receiving_2pt_conversions", 0))

    points = 6 * td_total + 3 * fg_made + 1 * pat_made + 2 * (safeties + pass_2pt + rush_2pt + recv_2pt)

    # Points allowed = opponent’s reconstructed points
    opp_pts_df = df[["season", "week", "team"]].copy()
    opp_pts_df["opp_points"] = points
    opp_pts_df = opp_pts_df.rename(columns={"team": "opponent"})
    joined_pts = df.merge(opp_pts_df, on=["season", "week", "opponent"], how="left", validate="m:1")
    points_allowed = _num(joined_pts["opp_points"])

    # Calculate success rates using EPA as proxy
    # Success = positive EPA on the play
    # For offense: use their EPA
    # For defense: use opponent's EPA (lower is better for defense)
    off_success_rate = off_epa_per_play.clip(0, 1)  # Normalize to 0-1 range
    def_success_rate = (-def_epa_per_play).clip(0, 1)  # Negative EPA is good for defense
    
    out = pd.DataFrame({
        "season": df["season"].astype(int, errors="ignore"),
        "week": df["week"].astype(int, errors="ignore"),
        "team": df["team"].astype(str),
        "opponent": df["opponent"].astype(str),
        "off_epa_per_play": off_epa_per_play,
        "def_epa_per_play": def_epa_per_play,
        "off_success_rate": off_success_rate,
        "def_success_rate": def_success_rate,
        "points": points,
        "points_allowed": points_allowed,
        "plays": plays,
        "pass_attempts": attempts,
        "rush_attempts": carries,
    })

    if out[["off_epa_per_play", "def_epa_per_play"]].isna().any().any():
        raise RuntimeError("Derived EPA/play has NaNs—upstream columns may be missing or zero for entire rows.")
    return out


# ---------------------------------------------------------------------
# ODDS (TheOddsAPI) — broader regions, robust parsing, per-event logging
# ---------------------------------------------------------------------

ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"

def fetch_market_lines_live() -> Dict[Tuple[str, str], Dict[str, float]]:
    key = os.getenv("ODDS_API_KEY")
    if not key:
        print("⚠️  ODDS_API_KEY not set. Will use model predictions as fallback for lines.")
        return {}

    attempts = [
        {"regions": "us,us2,uk,eu", "markets": "spreads,totals"},
        {"regions": "us,us2",       "markets": "spreads,totals"},
        {"regions": "us2",          "markets": "spreads,totals"},
        {"regions": "us",           "markets": "spreads,totals"},
        {"regions": "uk,eu",        "markets": "spreads,totals"},
    ]

    # Canonical names and common variants
    code = {
        "Pittsburgh Steelers":"PIT","Cincinnati Bengals":"CIN",
        "Los Angeles Rams":"LA","LA Rams":"LA",
        "Jacksonville Jaguars":"JAX","Jacksonville":"JAX",
        "Las Vegas Raiders":"LV","LV Raiders":"LV","Oakland Raiders":"LV",
        "Kansas City Chiefs":"KC","Kansas City":"KC",
        "Miami Dolphins":"MIA","Cleveland Browns":"CLE",
        "New England Patriots":"NE","Tennessee Titans":"TEN",
        "New Orleans Saints":"NO","Chicago Bears":"CHI",
        "Philadelphia Eagles":"PHI","Minnesota Vikings":"MIN",
        "Carolina Panthers":"CAR","New York Jets":"NYJ","NY Jets":"NYJ",
        "Indianapolis Colts":"IND","Los Angeles Chargers":"LAC","LA Chargers":"LAC","San Diego Chargers":"LAC",
        "New York Giants":"NYG","NY Giants":"NYG",
        "Denver Broncos":"DEN",
        "Washington Commanders":"WAS","Washington":"WAS","Washington Football Team":"WAS","Washington Redskins":"WAS",
        "Dallas Cowboys":"DAL",
        "Green Bay Packers":"GB",
        "Arizona Cardinals":"ARI","Phoenix Cardinals":"ARI","St. Louis Cardinals":"ARI",
        "Atlanta Falcons":"ATL",
        "San Francisco 49ers":"SF","SF 49ers":"SF","San Francisco":"SF",
        "Tampa Bay Buccaneers":"TB","Tampa Bay":"TB",
        "Detroit Lions":"DET",
        "Houston Texans":"HOU",
        "Seattle Seahawks":"SEA",
    }

    def norm(name: str) -> Optional[str]:
        if not name:
            return None
        return (
            code.get(name)
            or code.get(name.replace("Los Angeles", "LA"))
            or code.get(name.replace("New York", "NY"))
        )

    from statistics import median
    parsed: Dict[Tuple[str, str], Dict[str, float]] = {}
    last_status = None

    # log reasons per event for transparency
    log_lines: List[str] = []
    Path("artifacts").mkdir(exist_ok=True)

    for i, params in enumerate(attempts, 1):
        r = requests.get(
            ODDS_API_URL,
            params={"apiKey": key, "oddsFormat": "american", **params},
            timeout=30,
        )
        last_status = f"attempt {i} status={r.status_code}"
        if not r.ok:
            log_lines.append(f"[{last_status}] HTTP not OK: {r.text[:200]}")
            continue

        data = r.json()
        (Path("artifacts") / "odds_raw.json").write_text(json.dumps(data)[:1_000_000])

        if not isinstance(data, list) or not data:
            log_lines.append(f"[{last_status}] empty data list")
            continue

        local: Dict[Tuple[str, str], Dict[str, float]] = {}
        for ev_idx, event in enumerate(data):
            home_name = event.get("home_team", "")
            away_name = event.get("away_team", "")

            home = norm(home_name)
            away = norm(away_name)
            if not home or not away:
                log_lines.append(f"[{last_status}] ev#{ev_idx} unmapped team names: home='{home_name}' away='{away_name}'")
                continue

            bms = event.get("bookmakers", []) or []
            if not bms:
                log_lines.append(f"[{last_status}] ev#{ev_idx} {away}@{home} has no bookmakers")
                continue

            spreads_points: List[float] = []
            totals_points:  List[float] = []

            # Accept spreads from either home or away outcome (use algebra to convert)
            for book in bms:
                for mkt in book.get("markets", []) or []:
                    k = mkt.get("key")
                    outs = mkt.get("outcomes", []) or []
                    if k == "spreads":
                        # Look for both teams' lines; take home line if present, else derive from away (-x becomes +x)
                        home_pt = None; away_pt = None
                        for o in outs:
                            nm, pt = o.get("name"), o.get("point")
                            if pt is None: continue
                            try:
                                pt = float(pt)
                            except (TypeError, ValueError):
                                continue
                            if nm == home_name: home_pt = pt
                            if nm == away_name: away_pt = pt
                        if home_pt is not None:
                            spreads_points.append(home_pt)
                        elif away_pt is not None:
                            spreads_points.append(-away_pt)
                    elif k == "totals":
                        # Totals often come as two outcomes: Over and Under with the same 'point'
                        for o in outs:
                            pt = o.get("point")
                            if pt is None: continue
                            try:
                                totals_points.append(float(pt))
                                break
                            except (TypeError, ValueError):
                                continue

            if not spreads_points and not totals_points:
                log_lines.append(f"[{last_status}] ev#{ev_idx} {away}@{home} no spreads/totals in any bookmaker")
                continue

            rec: Dict[str, float] = {}
            if spreads_points:
                rec["spread_home"] = median(spreads_points)
            if totals_points:
                rec["total"] = median(totals_points)
            local[(away, home)] = rec

        if local:
            parsed = local
            break  # success for this attempt

    # write log
    (Path("artifacts") / "odds_parse_log.txt").write_text("\n".join(log_lines[:10000]))

    if not parsed:
        size = 0
        try:
            p = Path("artifacts/odds_raw.json")
            size = p.stat().st_size if p.exists() else 0
        except Exception:
            pass
        print(f"⚠️  Parsed 0 lines from Odds API ({last_status}). Will use model predictions as fallback for lines.")
        print(f"    See artifacts/odds_parse_log.txt for details (bytes={size}).")
        return {}
    return parsed


# ---------------------------------------------------------------------
# WEATHER (Open-Meteo)
# ---------------------------------------------------------------------

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_weather_for_matchups(stadiums_csv="data/stadiums.csv", matchups=None, kickoff_local_hour=13):
    if matchups is None or len(matchups) == 0:
        raise RuntimeError("No matchups provided for weather.")
    stadiums = pd.read_csv(stadiums_csv).set_index("team")
    rows = []
    for away, home in matchups:
        if home not in stadiums.index:
            raise RuntimeError(f"Missing stadium info for {home}")
        s = stadiums.loc[home]
        params = {
            "latitude": s["lat"],
            "longitude": s["lon"],
            "hourly": "temperature_2m,precipitation,wind_speed_10m",
            "windspeed_unit": "kmh",
            "timezone": "auto",
        }
        r = requests.get(OPEN_METEO_URL, params=params, timeout=25)
        if not r.ok:
            raise RuntimeError(f"Weather fetch failed for {home}: status={r.status_code}")
        data = r.json()
        hours = data.get("hourly", {})
        winds = hours.get("wind_speed_10m", [])
        temps = hours.get("temperature_2m", [])
        precs = hours.get("precipitation", [])
        idx = len(winds) // 2 if winds else None
        if idx is None:
            raise RuntimeError(f"Weather data missing for {home}")
        wind_kph = winds[idx]
        temp_c = temps[idx] if temps else 20.0
        precip = precs[idx] if precs else 0.0
        rows.append(
            {
                "away": away,
                "home": home,
                "wind_kph": float(wind_kph),
                "temp_c": float(temp_c),
                "precip_mm": float(precip),
                "is_dome": int(s["is_dome"]),
                "altitude_m": float(s["altitude_m"]),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# INJURIES (placeholder)
# ---------------------------------------------------------------------

def fetch_injury_index(matchups=None, season=2025):
    """
    Fetch injury data from nflverse and calculate weighted injury index.
    
    Injury weights by position:
    - QB: 10.0 (most critical)
    - RB/WR/CB: 3.0 (skill positions)
    - TE/OL/DL/LB/S: 2.0 (other starters)
    """
    try:
        # Fetch injury data from nflverse
        url = f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{season}.csv"
        injuries_df = _read_url_csv(url)
        
        # Position weights
        position_weights = {
            'QB': 10.0,
            'RB': 3.0, 'WR': 3.0, 'CB': 3.0,
            'TE': 2.0, 'OL': 2.0, 'G': 2.0, 'T': 2.0, 'C': 2.0,
            'DL': 2.0, 'DE': 2.0, 'DT': 2.0, 'NT': 2.0,
            'LB': 2.0, 'ILB': 2.0, 'OLB': 2.0,
            'S': 2.0, 'SS': 2.0, 'FS': 2.0,
            'K': 0.5, 'P': 0.5
        }
        
        # Calculate injury index per team
        injury_index = {}
        for team in injuries_df['team'].unique():
            team_injuries = injuries_df[injuries_df['team'] == team]
            
            # Sum weighted injuries (Out or Doubtful only)
            total_impact = 0.0
            for _, inj in team_injuries.iterrows():
                status = inj.get('report_status', '').upper()
                position = inj.get('position', 'UNKNOWN')
                
                if status in ['OUT', 'DOUBTFUL']:
                    weight = position_weights.get(position, 1.0)
                    total_impact += weight
                elif status == 'QUESTIONABLE':
                    weight = position_weights.get(position, 1.0)
                    total_impact += weight * 0.5  # 50% impact for questionable
            
            injury_index[team] = total_impact
        
        # Build result dataframe
        rows = []
        for away, home in (matchups or []):
            rows.append({"team": away, "injury_index": injury_index.get(away, 0.0)})
            rows.append({"team": home, "injury_index": injury_index.get(home, 0.0)})
        
        return pd.DataFrame(rows).drop_duplicates("team")
        
    except Exception as e:
        print(f"⚠️ Could not fetch injury data: {e}")
        print("   Using placeholder injury index (0.0 for all teams)")
        # Fallback to placeholder
        rows = []
        for away, home in (matchups or []):
            rows += [{"team": away, "injury_index": 0.0}, {"team": home, "injury_index": 0.0}]
        return pd.DataFrame(rows).drop_duplicates("team")
