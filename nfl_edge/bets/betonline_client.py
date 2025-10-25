"""
BetOnline client for fetching bet data

This module handles authentication and data fetching from BetOnline's
internal endpoints using session cookies and headers.
"""

from __future__ import annotations
import time
import json
import shlex
import re
from typing import Dict, Any, List, Optional
import requests
import pandas as pd
from pathlib import Path

BETONLINE_BASE = "https://api.betonline.ag/report/api/report"

# Minimal schema we normalize to
LEDGER_COLUMNS = [
    "ticket_id", "placed_utc", "sport", "league", "event_date_utc",
    "rotation", "home", "away", "market", "submarket",
    "odds_american", "line", "stake", "book",
    "settlement", "result", "profit"
]


def parse_curl_to_headers(curl_cmd: str) -> Dict[str, str]:
    """
    Parse 'Copy as cURL (bash)' from Chrome/Firefox DevTools.
    Extracts headers and cookies for BetOnline API calls.
    """
    if not curl_cmd.strip().startswith("curl "):
        raise ValueError("This doesn't look like a cURL command. Use DevTools → Copy as cURL (bash).")

    # Tokenize safely
    tokens = shlex.split(curl_cmd)
    headers: Dict[str, str] = {}
    url = None
    method = "GET"

    it = iter(range(len(tokens)))
    for i in it:
        t = tokens[i]
        if t in ["-X", "--request"] and i+1 < len(tokens):
            method = tokens[i+1].upper()
            next(it, None)
        elif t in ["-H", "--header"] and i+1 < len(tokens):
            hv = tokens[i+1]
            next(it, None)
            if ":" in hv:
                k, v = hv.split(":", 1)
                headers[k.strip()] = v.strip()
        elif not t.startswith("-") and (t.startswith("http://") or t.startswith("https://")):
            url = t

    if not url:
        # Some Chrome exports put the URL at the end without a flag; try regex fallback
        m = re.search(r"(https?://[^\s\"']+)", curl_cmd)
        url = m.group(1) if m else None

    # Normalize common keys
    if "user-agent" in headers and "User-Agent" not in headers:
        headers["User-Agent"] = headers.pop("user-agent")
    if "cookie" in headers and "Cookie" not in headers:
        headers["Cookie"] = headers.pop("cookie")
    
    # Drop headers that can break replay
    for bad in ["Content-Length", "content-length"]:
        headers.pop(bad, None)
    
    # Ensure we have authorization
    if not any(k.lower() == "authorization" for k in headers.keys()):
        raise ValueError("No Authorization header found in cURL. Make sure you copied the full request.")

    return {"__url__": url or "", "__method__": method, **headers}

def _headers_from_config(headers_dict: Dict[str, Any]) -> Dict[str, str]:
    """Convert headers dict to requests format"""
    required = ["cookie", "user-agent", "origin", "referer"]
    missing = [k for k in required if k not in headers_dict or not headers_dict[k].strip()]
    if missing:
        raise RuntimeError(f"BetOnline headers missing: {missing}. Provide them in the UI.")
    
    # Allow pass-through of any other header fields
    hdrs = {k: v for k, v in headers_dict.items() if isinstance(v, str) and v.strip()}
    
    # Requests wants 'User-Agent' canonicalized
    if "user-agent" in hdrs and "User-Agent" not in hdrs:
        hdrs["User-Agent"] = hdrs.pop("user-agent")
    
    return hdrs


def _post_json(path: str, headers: Dict[str, str], data: Dict[str, Any] = None) -> Any:
    """Make authenticated POST request to BetOnline endpoint"""
    url = f"{BETONLINE_BASE}/{path.lstrip('/')}"
    r = requests.post(url, headers=headers, json=data, timeout=30)
    
    if r.status_code == 429:
        time.sleep(1.5)
        r = requests.post(url, headers=headers, json=data, timeout=30)
    
    r.raise_for_status()
    return r.json()


def fetch_all_bets(headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Fetch all bet data from BetOnline endpoints
    
    Returns:
        Dict with keys: pending, graded, history, debug
        Each value is the raw JSON array from BetOnline
    """
    import datetime
    data = {}
    
    # Date range for last 30 days
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    
    # Request body format from BetOnline
    request_body = {
        "Id": None,
        "EndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "StartDate": start_date.strftime("%Y-%m-%dT00:00:00.000Z"),
        "Status": None,
        "Product": None,
        "WagerType": None,
        "FreePlayFlag": None,
        "StartPosition": 0,
        "TotalPerPage": 100,
        "IsDailyFigureReport": False
    }
    
    # Try the actual BetOnline API endpoints from their config
    endpoint_variations = [
        # Actual endpoints from BetOnline's API config (POST with body)
        ("pending", "get-pending-wagers", request_body),
        ("graded", "get-graded-wagers", request_body), 
        ("history", "get-bet-history", request_body),
    ]
    
    debug_info = []
    
    for key, ep, body in endpoint_variations:
        try:
            result = _post_json(ep, headers=headers, data=body)
            data[key] = result
            debug_info.append(f"✅ {key} ({ep}): {len(result) if isinstance(result, list) else 'dict'} items")
        except Exception as e:
            data[key] = {"error": str(e)}
            debug_info.append(f"❌ {key} ({ep}): {str(e)[:100]}")
    
    data["debug"] = debug_info
    return data


def _normalize_ticket(x: Dict[str, Any], book: str = "BetOnline") -> Dict[str, Any]:
    """Map one BetOnline ticket JSON into our flat schema"""
    return {
        "ticket_id": str(x.get("TicketNumber") or x.get("TicketId") or x.get("WagerId") or ""),
        "placed_utc": x.get("PlacedUTC") or x.get("PlacedDateUTC") or x.get("PlacedDate") or "",
        "sport": x.get("Sport") or "NFL",
        "league": x.get("League") or "NFL", 
        "event_date_utc": x.get("EventDateUTC") or x.get("GameDateUTC") or "",
        "rotation": x.get("RotationNumber") or x.get("Rotation") or "",
        "home": x.get("HomeTeam") or "",
        "away": x.get("AwayTeam") or "",
        "market": x.get("Market") or x.get("WagerType") or "",
        "submarket": x.get("SubMarket") or x.get("BetType") or "",
        "odds_american": x.get("OddsAmerican") or x.get("PriceAmerican") or x.get("Moneyline") or "",
        "line": x.get("Line") or x.get("PointSpread") or x.get("Total") or "",
        "stake": float(x.get("Risk") or x.get("Stake") or 0.0),
        "book": book,
        "settlement": x.get("Settlement") or x.get("Status") or "",
        "result": x.get("Result") or x.get("Outcome") or "",
        "profit": float(x.get("Win") or x.get("Net") or 0.0)
    }


def normalize_to_ledger(raw: Dict[str, Any]) -> pd.DataFrame:
    """Convert raw BetOnline data to standardized ledger format"""
    rows: List[Dict[str, Any]] = []
    
    for key in ["pending", "graded", "history"]:
        payload = raw.get(key, [])
        if isinstance(payload, dict) and "error" in payload:
            continue
        if not isinstance(payload, list):
            continue
            
        for ticket in payload:
            try:
                rows.append(_normalize_ticket(ticket))
            except Exception:
                continue
    
    df = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    
    # Clean numeric columns
    for col in ["stake", "profit"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    
    return df


def save_ledger(df: pd.DataFrame, path: str) -> None:
    """Save ledger to parquet file"""
    path_parquet = path.replace(".csv", ".parquet") if path.endswith(".csv") else path
    Path(path_parquet).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path_parquet, index=False)


def load_ledger(path: str) -> Optional[pd.DataFrame]:
    """Load ledger from parquet file"""
    path_parquet = path.replace(".csv", ".parquet") if path.endswith(".csv") else path
    if Path(path_parquet).exists():
        return pd.read_parquet(path_parquet)
    return None


def get_weekly_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate weekly P&L summary"""
    if df.empty:
        return {"weeks": [], "profits": [], "total_profit": 0.0, "total_games": 0}
    
    # Convert to datetime and extract week
    df["placed_date"] = pd.to_datetime(df["placed_utc"], errors="coerce")
    df["week"] = df["placed_date"].dt.isocalendar().week
    
    weekly = df.groupby("week").agg({
        "profit": "sum",
        "stake": "sum", 
        "ticket_id": "count"
    }).reset_index()
    
    weekly.columns = ["week", "profit", "total_stake", "bets"]
    
    return {
        "weeks": weekly["week"].tolist(),
        "profits": weekly["profit"].tolist(),
        "total_profit": df["profit"].sum(),
        "total_games": len(df),
        "win_rate": len(df[df["profit"] > 0]) / len(df) if len(df) > 0 else 0
    }
