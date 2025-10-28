"""
Run weather-adjusted totals betting for a single week.

This script:
1. Reads week matchups and opening totals
2. Pulls weather for each game at current timestamp
3. Emits proposed $5 bets with edge and reason
4. Writes CSV for later grading with closing totals

Usage:
    python edge_hunt/run_weather_totals.py --week 9 --pass wednesday
    python edge_hunt/run_weather_totals.py --week 9 --pass friday
    python edge_hunt/run_weather_totals.py --week 9 --pass sunday
"""

import argparse
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from edge_hunt.apply_weather_adjustment import adjusted_total
from edge_hunt.bet_rules import should_bet_total


def estimate_kickoff_utc(week: int, season: int = 2025) -> datetime:
    """
    Estimate Sunday 1pm ET kickoff for a given week.
    
    Args:
        week: NFL week number
        season: NFL season year
    
    Returns:
        Datetime (UTC) for typical Sunday 1pm ET game
    """
    # NFL season starts ~Sept 5, find first Sunday
    season_start = datetime(season, 9, 5)
    while season_start.weekday() != 6:  # 6 = Sunday
        season_start += timedelta(days=1)
    
    # Add weeks
    game_date = season_start + timedelta(weeks=week - 1)
    
    # 1pm ET = 18:00 UTC (during DST) or 17:00 UTC (standard time)
    # For simplicity, use 18:00 UTC
    kickoff = game_date.replace(hour=18, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    
    return kickoff


def load_matchups_with_totals(week: int, season: int = 2025) -> pd.DataFrame:
    """
    Load matchups with opening totals for a given week.
    
    For now, this is a placeholder. In production, you'd:
    1. Read from your predictions CSV
    2. Or fetch from Odds API
    3. Or load from database
    
    Args:
        week: NFL week number
        season: NFL season year
    
    Returns:
        DataFrame with columns: away, home, open_total, kickoff_utc
    """
    # Try to load from predictions file
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    pred_files = list(artifacts_dir.glob(f"predictions_{season}_week{week}_*.csv"))
    
    if pred_files:
        # Load most recent prediction file
        pred_file = sorted(pred_files)[-1]
        df = pd.read_csv(pred_file)
        
        # Extract relevant columns
        if 'Total used' in df.columns:
            matchups = df[['away', 'home', 'Total used']].copy()
            matchups = matchups.rename(columns={'Total used': 'open_total'})
        else:
            print(f"⚠️  No 'Total used' column in {pred_file}")
            return pd.DataFrame()
        
        # Estimate kickoff times (all Sunday 1pm ET for simplicity)
        kickoff = estimate_kickoff_utc(week, season)
        matchups['kickoff_utc'] = kickoff
        
        return matchups
    
    else:
        print(f"⚠️  No prediction file found for Week {week}")
        return pd.DataFrame()


def run_weather_totals(
    week: int,
    pass_name: str,
    season: int = 2025,
    min_edge: float = 2.0,
    output_dir: Path = None,
) -> pd.DataFrame:
    """
    Run weather-adjusted totals betting for a week.
    
    Args:
        week: NFL week number
        pass_name: "wednesday", "friday", or "sunday"
        season: NFL season year
        min_edge: Minimum edge (points) to place bet
        output_dir: Directory to save bet tickets
    
    Returns:
        DataFrame with bet tickets
    """
    print("=" * 80)
    print(f"WEATHER TOTALS - WEEK {week} - {pass_name.upper()} PASS")
    print("=" * 80)
    
    # Load matchups
    matchups = load_matchups_with_totals(week, season)
    
    if matchups.empty:
        print("❌ No matchups found")
        return pd.DataFrame()
    
    print(f"\n📥 Loaded {len(matchups)} games")
    
    # Process each game
    bet_tickets = []
    
    for idx, row in matchups.iterrows():
        home = row['home']
        away = row['away']
        open_total = row['open_total']
        kickoff_utc = row['kickoff_utc']
        
        print(f"\n{away} @ {home}")
        print(f"  Opening total: {open_total}")
        
        # Get weather adjustment
        adj_result = adjusted_total(open_total, home, away, kickoff_utc)
        
        if not adj_result["ok"]:
            print(f"  ⚠️  {adj_result['reason']}")
            continue
        
        adj_total = adj_result["adj_total"]
        wf = adj_result["weather_features"]
        
        print(f"  Adjusted total: {adj_total} ({adj_total - open_total:+.1f} pts)")
        print(f"    Wind: {wf['wind_mph']:.1f} mph → {wf['wind_penalty_pts']:+.1f} pts")
        print(f"    Precip: {wf['precip_mmph']:.2f} mm/hr → {wf['precip_penalty_pts']:+.1f} pts")
        
        # Check if we should bet
        bet = should_bet_total(open_total, adj_total, min_edge_pts=min_edge)
        
        if bet:
            print(f"  ✅ BET {bet['side'].upper()} {open_total} @ ${bet['stake']:.2f}")
            print(f"     Edge: {bet['edge_pts']:.1f} pts")
            
            # Create bet ticket
            ticket = {
                "week": week,
                "pass": pass_name,
                "game": f"{away}@{home}",
                "away": away,
                "home": home,
                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "kickoff_utc": kickoff_utc.isoformat(),
                "open_total": open_total,
                "adj_total": adj_total,
                "bet_side": bet["side"],
                "stake": bet["stake"],
                "edge_pts": bet["edge_pts"],
                "wind_mph": wf["wind_mph"],
                "precip_mmph": wf["precip_mmph"],
                "temp_f": wf["temp_f"],
                "roof_flag": wf["roof_flag"],
                # To be filled in later when grading:
                "close_total": None,
                "actual_total": None,
                "clv_points": None,
                "result": None,
                "profit": None,
            }
            bet_tickets.append(ticket)
        else:
            print(f"  ⏸️  No bet (edge < {min_edge} pts)")
    
    # Convert to DataFrame
    if not bet_tickets:
        print("\n❌ No bets placed")
        return pd.DataFrame()
    
    df = pd.DataFrame(bet_tickets)
    
    # Save to CSV
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "artifacts"
    
    output_dir.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"weather_bets_week{week}_{pass_name}_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✅ {len(df)} bets placed")
    print(f"📊 Total stake: ${df['stake'].sum():.2f}")
    print(f"📊 Average edge: {df['edge_pts'].mean():.2f} pts")
    print(f"\n💾 Saved to: {output_file}")
    
    return df


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run weather-adjusted totals betting"
    )
    parser.add_argument(
        "--week", type=int, required=True, help="NFL week number"
    )
    parser.add_argument(
        "--pass-name",
        type=str,
        required=True,
        choices=["wednesday", "friday", "sunday"],
        help="Collection pass (wednesday/friday/sunday)",
        dest="pass_name",
    )
    parser.add_argument(
        "--season", type=int, default=2025, help="NFL season year"
    )
    parser.add_argument(
        "--min-edge",
        type=float,
        default=2.0,
        help="Minimum edge (points) to place bet",
    )
    
    args = parser.parse_args()
    
    run_weather_totals(
        week=args.week,
        pass_name=args.pass_name,
        season=args.season,
        min_edge=args.min_edge,
    )


if __name__ == "__main__":
    main()

