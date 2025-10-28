"""
Run combined weather + QB/OL betting for a single week.

This script combines:
1. Weather signals (wind, precipitation) → Totals bets
2. QB/OL injury signals → Spread and Total bets

Usage:
    python edge_hunt/run_combined_signals.py --week 9 --pass wednesday
    python edge_hunt/run_combined_signals.py --week 9 --pass friday
    python edge_hunt/run_combined_signals.py --week 9 --pass sunday
"""

import argparse
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from edge_hunt.apply_weather_adjustment import adjusted_total
from edge_hunt.qb_ol_features import calculate_game_injury_adjustment
from edge_hunt.bet_rules import should_bet_total


def estimate_kickoff_utc(week: int, season: int = 2025) -> datetime:
    """Estimate Sunday 1pm ET kickoff for a given week."""
    season_start = datetime(season, 9, 5)
    while season_start.weekday() != 6:  # 6 = Sunday
        season_start += timedelta(days=1)
    
    game_date = season_start + timedelta(weeks=week - 1)
    kickoff = game_date.replace(hour=18, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    
    return kickoff


def load_matchups_with_lines(week: int, season: int = 2025) -> pd.DataFrame:
    """Load matchups with opening lines for a given week."""
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    pred_files = list(artifacts_dir.glob(f"predictions_{season}_week{week}_*.csv"))
    
    if pred_files:
        pred_file = sorted(pred_files)[-1]
        df = pd.read_csv(pred_file)
        
        if 'Total used' in df.columns and 'Spread used (home-)' in df.columns:
            matchups = df[['away', 'home', 'Total used', 'Spread used (home-)']].copy()
            matchups = matchups.rename(columns={
                'Total used': 'open_total',
                'Spread used (home-)': 'open_spread'
            })
        else:
            print(f"⚠️  Missing columns in {pred_file}")
            return pd.DataFrame()
        
        kickoff = estimate_kickoff_utc(week, season)
        matchups['kickoff_utc'] = kickoff
        
        return matchups
    else:
        print(f"⚠️  No prediction file found for Week {week}")
        return pd.DataFrame()


def should_bet_spread(
    open_spread: float, adj_spread: float, min_edge_pts: float = 3.0
) -> Optional[Dict]:
    """
    Determine if we should bet the spread based on injury adjustment.
    
    Args:
        open_spread: Opening spread (home perspective, negative = home favored)
        adj_spread: Injury-adjusted spread
        min_edge_pts: Minimum edge required to bet (default: 3.0)
    
    Returns:
        Bet recommendation or None
    """
    edge = abs(adj_spread - open_spread)
    
    if edge < min_edge_pts:
        return None
    
    # If adj_spread is more negative than open, home got stronger → bet home
    # If adj_spread is more positive than open, away got stronger → bet away
    if adj_spread < open_spread:
        side = "home"
    else:
        side = "away"
    
    return {"side": side, "edge_pts": edge, "stake": 5.0}


def run_combined_signals(
    week: int,
    pass_name: str,
    season: int = 2025,
    min_total_edge: float = 2.0,
    min_spread_edge: float = 3.0,
    output_dir: Path = None,
) -> pd.DataFrame:
    """
    Run combined weather + QB/OL betting for a week.
    
    Args:
        week: NFL week number
        pass_name: "wednesday", "friday", or "sunday"
        season: NFL season year
        min_total_edge: Minimum edge (points) for total bets
        min_spread_edge: Minimum edge (points) for spread bets
        output_dir: Directory to save bet tickets
    
    Returns:
        DataFrame with bet tickets
    """
    print("=" * 80)
    print(f"COMBINED SIGNALS - WEEK {week} - {pass_name.upper()} PASS")
    print("=" * 80)
    
    # Load matchups
    matchups = load_matchups_with_lines(week, season)
    
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
        open_spread = row['open_spread']
        kickoff_utc = row['kickoff_utc']
        
        print(f"\n{'='*80}")
        print(f"{away} @ {home}")
        print(f"  Opening spread: {home} {open_spread:+.1f}")
        print(f"  Opening total: {open_total}")
        print("="*80)
        
        # 1. Get weather adjustment for total
        weather_adj = adjusted_total(open_total, home, away, kickoff_utc)
        
        weather_total_adj = 0.0
        if weather_adj["ok"]:
            weather_total_adj = weather_adj["adj_total"] - open_total
            wf = weather_adj["weather_features"]
            print(f"\n📊 WEATHER:")
            print(f"  Wind: {wf['wind_mph']:.1f} mph → {wf['wind_penalty_pts']:+.1f} pts")
            print(f"  Precip: {wf['precip_mmph']:.2f} mm/hr → {wf['precip_penalty_pts']:+.1f} pts")
            print(f"  Total adjustment: {weather_total_adj:+.1f} pts")
        
        # 2. Get QB/OL injury adjustment
        print(f"\n📊 INJURIES:")
        spread_adj, injury_total_adj, injury_details = calculate_game_injury_adjustment(away, home)
        
        print(f"  Away ({away}):")
        print(f"    QB: {injury_details['away_qb_drop_off']:+.1f} pts")
        print(f"    OL: {injury_details['away_ol_penalty']:+.1f} pts")
        print(f"  Home ({home}):")
        print(f"    QB: {injury_details['home_qb_drop_off']:+.1f} pts")
        print(f"    OL: {injury_details['home_ol_penalty']:+.1f} pts")
        print(f"  Spread adjustment: {spread_adj:+.1f} pts")
        print(f"  Total adjustment: {injury_total_adj:+.1f} pts")
        
        # 3. Combine adjustments
        combined_total_adj = weather_total_adj + injury_total_adj
        adj_total = open_total + combined_total_adj
        adj_spread = open_spread + spread_adj
        
        print(f"\n📊 COMBINED:")
        print(f"  Adjusted spread: {home} {adj_spread:+.1f} (change: {spread_adj:+.1f})")
        print(f"  Adjusted total: {adj_total:.1f} (change: {combined_total_adj:+.1f})")
        
        # 4. Check for spread bet
        spread_bet = should_bet_spread(open_spread, adj_spread, min_spread_edge)
        
        if spread_bet:
            print(f"\n✅ BET SPREAD: {spread_bet['side'].upper()} @ ${spread_bet['stake']:.2f}")
            print(f"   Edge: {spread_bet['edge_pts']:.1f} pts")
            
            bet_tickets.append({
                "week": week,
                "pass": pass_name,
                "game": f"{away}@{home}",
                "away": away,
                "home": home,
                "bet_type": "spread",
                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "kickoff_utc": kickoff_utc.isoformat(),
                "open_line": open_spread,
                "adj_line": adj_spread,
                "bet_side": spread_bet["side"],
                "stake": spread_bet["stake"],
                "edge_pts": spread_bet["edge_pts"],
                "weather_adj": 0.0,  # Weather doesn't affect spread
                "injury_adj": spread_adj,
                "close_line": None,
                "actual_result": None,
                "clv_points": None,
                "result": None,
                "profit": None,
            })
        
        # 5. Check for total bet
        total_bet = should_bet_total(open_total, adj_total, min_total_edge)
        
        if total_bet:
            print(f"\n✅ BET TOTAL: {total_bet['side'].upper()} {open_total} @ ${total_bet['stake']:.2f}")
            print(f"   Edge: {total_bet['edge_pts']:.1f} pts")
            
            bet_tickets.append({
                "week": week,
                "pass": pass_name,
                "game": f"{away}@{home}",
                "away": away,
                "home": home,
                "bet_type": "total",
                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "kickoff_utc": kickoff_utc.isoformat(),
                "open_line": open_total,
                "adj_line": adj_total,
                "bet_side": total_bet["side"],
                "stake": total_bet["stake"],
                "edge_pts": total_bet["edge_pts"],
                "weather_adj": weather_total_adj,
                "injury_adj": injury_total_adj,
                "close_line": None,
                "actual_result": None,
                "clv_points": None,
                "result": None,
                "profit": None,
            })
        
        if not spread_bet and not total_bet:
            print(f"\n⏸️  No bets (edges too small)")
    
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
    output_file = output_dir / f"combined_bets_week{week}_{pass_name}_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    spread_bets = df[df['bet_type'] == 'spread']
    total_bets = df[df['bet_type'] == 'total']
    
    print(f"\n✅ {len(df)} total bets placed:")
    print(f"   Spread bets: {len(spread_bets)}")
    print(f"   Total bets: {len(total_bets)}")
    print(f"\n📊 Total stake: ${df['stake'].sum():.2f}")
    print(f"📊 Average edge: {df['edge_pts'].mean():.2f} pts")
    
    if len(spread_bets) > 0:
        print(f"\n📊 Spread bets:")
        print(f"   Average edge: {spread_bets['edge_pts'].mean():.2f} pts")
        print(f"   Driven by injuries: 100%")
    
    if len(total_bets) > 0:
        print(f"\n📊 Total bets:")
        print(f"   Average edge: {total_bets['edge_pts'].mean():.2f} pts")
        weather_driven = (total_bets['weather_adj'].abs() > total_bets['injury_adj'].abs()).sum()
        print(f"   Weather-driven: {weather_driven}/{len(total_bets)}")
        print(f"   Injury-driven: {len(total_bets) - weather_driven}/{len(total_bets)}")
    
    print(f"\n💾 Saved to: {output_file}")
    
    return df


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run combined weather + QB/OL betting"
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
        "--min-total-edge",
        type=float,
        default=2.0,
        help="Minimum edge (points) for total bets",
    )
    parser.add_argument(
        "--min-spread-edge",
        type=float,
        default=3.0,
        help="Minimum edge (points) for spread bets",
    )
    
    args = parser.parse_args()
    
    run_combined_signals(
        week=args.week,
        pass_name=args.pass_name,
        season=args.season,
        min_total_edge=args.min_total_edge,
        min_spread_edge=args.min_spread_edge,
    )


if __name__ == "__main__":
    main()

