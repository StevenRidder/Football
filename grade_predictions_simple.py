#!/usr/bin/env python3
"""
Simple, clean grading script - ALL calculations in backend.
Based on the template provided.
"""

import pandas as pd
import nfl_data_py as nfl
import json
from datetime import datetime
from pathlib import Path


def load_predictions_and_results():
    """Load predictions - actual results are already in the CSV!"""
    import glob
    ridge_files = glob.glob('predictions_ridge_stress_calibrated_*.csv')
    if not ridge_files:
        ridge_files = glob.glob('predictions_ridge_stress_*.csv')
    if not ridge_files:
        raise FileNotFoundError("No prediction files found")
    
    latest_file = sorted(ridge_files)[-1]
    print(f"✅ Loading predictions from {latest_file}")
    
    df = pd.read_csv(latest_file)
    
    # Standardize column names
    if 'away' in df.columns:
        df = df.rename(columns={
            'away': 'away_team',
            'home': 'home_team',
            'away_score': 'predicted_away_score',
            'home_score': 'predicted_home_score',
            'closing_spread': 'market_spread',
            'closing_total': 'market_total'
        })
    
    return df


def grade_bets(df):
    """Grade all bets - returns list of results (includes future games)"""
    results = []
    
    for _, row in df.iterrows():
        game_id = f"{row['away_team']}@{row['home_team']}_W{row['week']}"
        
        # Check if game is completed
        is_completed = False
        try:
            aa_check = float(row['actual_away_score'])
            ah_check = float(row['actual_home_score'])
            if not pd.isna(aa_check) and not pd.isna(ah_check):
                is_completed = True
        except (ValueError, TypeError, KeyError):
            pass
        
        # Predicted
        ph = float(row["predicted_home_score"])
        pa = float(row["predicted_away_score"])
        pred_total = ph + pa
        pred_spread_home = ph - pa  # Positive = home favored
        
        # Market (home-based: negative = away favored, positive = home favored)
        market_spread = float(row["market_spread"])
        market_total = float(row["market_total"])
        
        # Actual (only if completed)
        if is_completed:
            ah = float(row["actual_home_score"])
            aa = float(row["actual_away_score"])
            actual_total = ah + aa
            actual_spread_home = ah - aa
        else:
            ah = None
            aa = None
            actual_total = None
            actual_spread_home = None
        
        # Calculate edges
        spread_edge = abs(pred_spread_home - market_spread)
        total_edge = abs(pred_total - market_total)
        
        # Determine bets (1.5 point threshold)
        spread_bet = None
        spread_bet_side = None
        if spread_edge >= 1.5:
            if pred_spread_home > market_spread:
                # We think home is better than market
                spread_bet = "spread"
                spread_bet_side = row["home_team"]
            else:
                # We think away is better than market
                spread_bet = "spread"
                spread_bet_side = row["away_team"]
        
        total_bet = None
        total_bet_side = None
        if total_edge >= 1.5:
            if pred_total > market_total:
                total_bet = "total"
                total_bet_side = "Over"
            else:
                total_bet = "total"
                total_bet_side = "Under"
        
        # GRADE SPREAD BET (only if completed)
        spread_win = None
        if is_completed and spread_bet == "spread":
            if spread_bet_side == row["home_team"]:
                # Bet home to cover
                spread_win = int(actual_spread_home > market_spread)
            else:
                # Bet away to cover
                spread_win = int(actual_spread_home < market_spread)
        
        # GRADE TOTAL BET (only if completed)
        total_win = None
        if is_completed and total_bet == "total":
            if total_bet_side == "Over":
                total_win = int(actual_total > market_total)
            else:
                total_win = int(actual_total < market_total)
        
        # GRADE MONEYLINE (only if completed, based on spread bet)
        moneyline_win = None
        if is_completed and spread_bet == "spread":
            if spread_bet_side == row["home_team"]:
                moneyline_win = int(ah > aa)
            else:
                moneyline_win = int(aa > ah)
        
        results.append({
            "game_id": game_id,
            "season": int(row.get("season", 2025)),
            "week": int(row["week"]),
            "gameday": row.get("gameday"),
            "gametime": row.get("gametime"),
            "away_team": row["away_team"],
            "home_team": row["home_team"],
            "predicted_away_score": round(pa, 1),
            "predicted_home_score": round(ph, 1),
            "actual_away_score": int(aa) if is_completed else None,
            "actual_home_score": int(ah) if is_completed else None,
            "market_spread": market_spread,
            "market_total": market_total,
            "our_spread": round(pred_spread_home, 1),  # Add this
            "our_total": round(pred_total, 1),  # Add this
            "home_cover_prob": row.get("home_cover_prob"),
            "over_prob": row.get("over_prob"),
            "home_win_prob": row.get("home_win_prob"),
            "spread_bet": spread_bet,
            "spread_bet_side": spread_bet_side,
            "spread_win": spread_win,
            "total_bet": total_bet,
            "total_bet_side": total_bet_side,
            "total_win": total_win,
            "moneyline_win": moneyline_win,
            "spread_edge": round(spread_edge, 1),
            "total_edge": round(total_edge, 1),
            "spread_error": round(abs(pred_spread_home - actual_spread_home), 1) if is_completed else None,
            "total_error": round(abs(pred_total - actual_total), 1) if is_completed else None,
            "score_error_home": round(abs(ph - ah), 1) if is_completed else None,
            "score_error_away": round(abs(pa - aa), 1) if is_completed else None,
        })
    
    return pd.DataFrame(results)


def compute_summary(results_df):
    """Compute summary statistics"""
    # Filter to games with bets
    spread_bets = results_df[results_df["spread_win"].notna()]
    total_bets = results_df[results_df["total_win"].notna()]
    ml_bets = results_df[results_df["moneyline_win"].notna()]
    
    summary = {}
    
    # Spread stats
    if len(spread_bets) > 0:
        wins = spread_bets["spread_win"].sum()
        losses = len(spread_bets) - wins
        win_pct = wins / len(spread_bets) * 100
        roi = ((wins * 0.91 - losses) / len(spread_bets) * 100)  # -110 odds
        
        summary["spread_bets"] = len(spread_bets)
        summary["spread_wins"] = int(wins)
        summary["spread_losses"] = int(losses)
        summary["spread_win_pct"] = round(win_pct, 1)
        summary["spread_roi"] = round(roi, 1)
    
    # Total stats
    if len(total_bets) > 0:
        wins = total_bets["total_win"].sum()
        losses = len(total_bets) - wins
        win_pct = wins / len(total_bets) * 100
        roi = ((wins * 0.91 - losses) / len(total_bets) * 100)
        
        summary["total_bets"] = len(total_bets)
        summary["total_wins"] = int(wins)
        summary["total_losses"] = int(losses)
        summary["total_win_pct"] = round(win_pct, 1)
        summary["total_roi"] = round(roi, 1)
    
    # Moneyline stats
    if len(ml_bets) > 0:
        wins = ml_bets["moneyline_win"].sum()
        losses = len(ml_bets) - wins
        win_pct = wins / len(ml_bets) * 100
        
        summary["moneyline_bets"] = len(ml_bets)
        summary["moneyline_wins"] = int(wins)
        summary["moneyline_losses"] = int(losses)
        summary["moneyline_win_pct"] = round(win_pct, 1)
    
    # Accuracy stats
    summary["avg_spread_error"] = round(results_df["spread_error"].mean(), 1)
    summary["avg_total_error"] = round(results_df["total_error"].mean(), 1)
    summary["avg_score_error"] = round((results_df["score_error_home"] + results_df["score_error_away"]).mean() / 2, 1)
    
    return summary


def main():
    print("=" * 70)
    print("🏈 GRADING PREDICTIONS (Simple Backend Approach)")
    print("=" * 70)
    
    # Load data
    df = load_predictions_and_results()
    print(f"\n📊 Loaded {len(df)} games")
    
    # Grade bets
    print("✅ Grading bets...")
    graded = grade_bets(df)
    print(f"✅ Graded {len(graded)} completed games")
    
    # Save graded results
    output_dir = Path('artifacts/graded_results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    graded_file = output_dir / f'graded_bets_{timestamp}.csv'
    graded.to_csv(graded_file, index=False)
    print(f"\n💾 Saved: {graded_file}")
    
    # Compute weekly summaries
    print("\n📈 Computing weekly summaries...")
    weekly_stats = []
    
    for week in sorted(graded['week'].unique()):
        week_data = graded[graded['week'] == week]
        summary = compute_summary(week_data)
        summary['week'] = int(week)
        weekly_stats.append(summary)
    
    # Save weekly stats
    stats_file = output_dir / f'weekly_stats_{timestamp}.json'
    with open(stats_file, 'w') as f:
        json.dump(weekly_stats, f, indent=2)
    print(f"💾 Saved: {stats_file}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 OVERALL SUMMARY")
    print("=" * 70)
    
    overall = compute_summary(graded)
    
    if 'spread_bets' in overall:
        print(f"\n🎯 SPREAD BETS:")
        print(f"   Record: {overall['spread_wins']}-{overall['spread_losses']}")
        print(f"   Win Rate: {overall['spread_win_pct']:.1f}%")
        print(f"   ROI: {overall['spread_roi']:+.1f}%")
    
    if 'total_bets' in overall:
        print(f"\n🎯 TOTAL BETS:")
        print(f"   Record: {overall['total_wins']}-{overall['total_losses']}")
        print(f"   Win Rate: {overall['total_win_pct']:.1f}%")
        print(f"   ROI: {overall['total_roi']:+.1f}%")
    
    print(f"\n📏 ACCURACY:")
    print(f"   Avg Spread Error: {overall['avg_spread_error']:.1f} points")
    print(f"   Avg Total Error: {overall['avg_total_error']:.1f} points")
    print(f"   Avg Score Error: {overall['avg_score_error']:.1f} points per team")
    
    # Week-by-week
    print("\n" + "=" * 70)
    print("📅 WEEK-BY-WEEK (Spread Bets)")
    print("=" * 70)
    
    for stat in weekly_stats:
        if 'spread_bets' in stat:
            print(f"Week {stat['week']:2d}: {stat['spread_wins']:2d}-{stat['spread_losses']} "
                  f"({stat['spread_win_pct']:5.1f}% WR, {stat['spread_roi']:+6.1f}% ROI)")
    
    print("\n" + "=" * 70)
    print("✅ GRADING COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()

