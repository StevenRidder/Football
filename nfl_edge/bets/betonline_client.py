"""
BetOnline client for fetching bet data

This module handles authentication and data fetching from BetOnline's
internal endpoints using session cookies and headers.
"""

from __future__ import annotations
import time
import json
from typing import Dict, Any, List, Optional
import requests
import pandas as pd
from pathlib import Path

BETONLINE_BASE = "https://www.betonline.ag"

# Minimal schema we normalize to
LEDGER_COLUMNS = [
    "ticket_id", "placed_utc", "sport", "league", "event_date_utc",
    "rotation", "home", "away", "market", "submarket",
    "odds_american", "line", "stake", "book",
    "settlement", "result", "profit"
]


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


def _get_json(path: str, headers: Dict[str, str], params: Dict[str, Any] = None) -> Any:
    """Make authenticated request to BetOnline endpoint"""
    url = f"{BETONLINE_BASE}/{path.lstrip('/')}"
    r = requests.get(url, headers=headers, params=params, timeout=30)
    
    if r.status_code == 429:
        time.sleep(1.5)
        r = requests.get(url, headers=headers, params=params, timeout=30)
    
    r.raise_for_status()
    return r.json()


def fetch_all_bets(headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Fetch all bet data from BetOnline endpoints
    
    Returns:
        Dict with keys: pending, graded, history
        Each value is the raw JSON array from BetOnline
    """
    data = {}
    endpoints = {
        "pending": "report/get-pending-wagers",
        "graded": "report/get-graded-wagers", 
        "history": "report/get-bet-history",
    }
    
    for key, ep in endpoints.items():
        try:
            data[key] = _get_json(ep, headers=headers)
        except Exception as e:
            data[key] = {"error": str(e)}
    
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
