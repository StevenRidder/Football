"""
Complete backtesting implementation.
Tests model predictions against actual historical results.
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import List, Tuple

from nfl_edge.data_ingest import NFLVERSE_TEAM_BASE, _read_url_csv, _num
from nfl_edge.features import build_features, join_matchups
from nfl_edge.model import fit_expected_points_model, predict_expected_points
from nfl_edge.simulate import monte_carlo


def get_historical_teamweeks(season: int, max_week: int) -> pd.DataFrame:
    """
    Fetch team-week data through specified week (same format as data_ingest.py).
    
    Args:
        season: Season year
        max_week: Last week to include (for training)
    
    Returns:
        DataFrame in teamweeks format
    """
    url = f"{NFLVERSE_TEAM_BASE}stats_team_week_{season}.csv"
    df = _read_url_csv(url)
    
    # Filter to regular season through max_week
    df = df[(df['season_type'] == 'REG') & (df['week'] <= max_week)].copy()
    
    # Same transformation as fetch_teamweeks_live
    df = df.rename(columns={"opponent_team": "opponent"})
    
    attempts = _num(df["attempts"])
    carries = _num(df["carries"])
    sacks = _num(df["sacks_suffered"])
    plays = attempts + carries + sacks
    plays_safe = plays.replace(0, 1e-9)
    
    off_epa_per_play = (_num(df["passing_epa"]) + _num(df["rushing_epa"])) / plays_safe
    
    # Defensive EPA
    opp_key_cols = ["season", "week", "team"]
    opp_df = df[opp_key_cols + ["attempts", "carries", "sacks_suffered", "passing_epa", "rushing_epa"]].copy()
    opp_df["opp_off_plays"] = _num(opp_df["attempts"]) + _num(opp_df["carries"]) + _num(opp_df["sacks_suffered"])
    opp_df["opp_off_plays_safe"] = opp_df["opp_off_plays"].replace(0, 1e-9)
    opp_df["opp_off_epa_per_play"] = (_num(opp_df["passing_epa"]) + _num(opp_df["rushing_epa"])) / opp_df["opp_off_plays_safe"]
    opp_df = opp_df.rename(columns={"team": "opponent"})
    joined = df.merge(opp_df[["season", "week", "opponent", "opp_off_epa_per_play", "opp_off_plays"]], 
                     on=["season", "week", "opponent"], how="left", validate="m:1")
    def_epa_per_play = _num(joined["opp_off_epa_per_play"])
    
    # Points
    td_cols = ["passing_tds", "rushing_tds", "receiving_tds", "def_tds", "special_teams_tds"]
    for c in td_cols:
        if c not in df.columns:
            df[c] = 0
    td_total = sum(_num(df[c]) for c in td_cols)
    
    fg_made = _num(df.get("fg_made", 0))
    pat_made = _num(df.get("pat_made", 0))
    safeties = _num(df.get("def_safeties", 0))
    pass_2pt = _num(df.get("passing_2pt_conversions", 0))
    rush_2pt = _num(df.get("rushing_2pt_conversions", 0))
    recv_2pt = _num(df.get("receiving_2pt_conversions", 0))
    
    points = 6 * td_total + 3 * fg_made + 1 * pat_made + 2 * (safeties + pass_2pt + rush_2pt + recv_2pt)
    
    # Points allowed
    opp_pts_df = df[["season", "week", "team"]].copy()
    opp_pts_df["opp_points"] = points
    opp_pts_df = opp_pts_df.rename(columns={"team": "opponent"})
    joined_pts = df.merge(opp_pts_df, on=["season", "week", "opponent"], how="left", validate="m:1")
    points_allowed = _num(joined_pts["opp_points"])
    
    out = pd.DataFrame({
        "season": df["season"].astype(int, errors="ignore"),
        "week": df["week"].astype(int, errors="ignore"),
        "team": df["team"].astype(str),
        "opponent": df["opponent"].astype(str),
        "off_epa_per_play": off_epa_per_play,
        "def_epa_per_play": def_epa_per_play,
        "off_success_rate": pd.Series([float("nan")] * len(df)),
        "def_success_rate": pd.Series([float("nan")] * len(df)),
        "points": points,
        "points_allowed": points_allowed,
        "plays": plays,
        "pass_attempts": attempts,
        "rush_attempts": carries,
    })
    
    return out


def get_actual_results(season: int, week: int) -> pd.DataFrame:
    """
    Get actual scores for a specific week.
    
    Args:
        season: Season year
        week: Week number
    
    Returns:
        DataFrame with away_team, home_team, away_score, home_score
    """
    url = f"{NFLVERSE_TEAM_BASE}stats_team_week_{season}.csv"
    df = _read_url_csv(url)
    df = df[(df['season_type'] == 'REG') & (df['week'] == week)].copy()
    
    # Calculate scores
    def calc_points(row):
        td_cols = ['passing_tds', 'rushing_tds', 'receiving_tds', 'def_tds', 'special_teams_tds']
        td_total = sum(row.get(c, 0) for c in td_cols)
        fg_made = row.get('fg_made', 0)
        pat_made = row.get('pat_made', 0)
        safeties = row.get('def_safeties', 0)
        pass_2pt = row.get('passing_2pt_conversions', 0)
        rush_2pt = row.get('rushing_2pt_conversions', 0)
        recv_2pt = row.get('receiving_2pt_conversions', 0)
        return 6*td_total + 3*fg_made + 1*pat_made + 2*(safeties + pass_2pt + rush_2pt + recv_2pt)
    
    df['score'] = df.apply(calc_points, axis=1)
    
    # Build games (one row per game)
    games = []
    processed = set()
    
    for _, row in df.iterrows():
        team = row['team']
        opp = row['opponent_team']
        
        game_key = tuple(sorted([team, opp]))
        if game_key in processed:
            continue
        processed.add(game_key)
        
        opp_rows = df[(df['team'] == opp) & (df['opponent_team'] == team)]
        if opp_rows.empty:
            continue
        opp_row = opp_rows.iloc[0]
        
        # Determine home/away (alphabetically for consistency)
        if team < opp:
            away_team, away_score = team, row['score']
            home_team, home_score = opp, opp_row['score']
        else:
            away_team, away_score = opp, opp_row['score']
            home_team, home_score = team, row['score']
        
        games.append({
            'away_team': away_team,
            'home_team': home_team,
            'away_score': away_score,
            'home_score': home_score,
            'total': away_score + home_score,
            'margin': home_score - away_score
        })
    
    return pd.DataFrame(games)


def backtest_single_week(season: int, week: int, config: dict) -> pd.DataFrame:
    """
    Backtest a single week.
    
    Args:
        season: Season year
        week: Week to predict
        config: Config dict
    
    Returns:
        DataFrame with predictions and actuals
    """
    print(f"  Week {week}...", end=" ", flush=True)
    
    # Get training data
    # For early weeks (1-4), use previous season's last 8 weeks
    # For later weeks (5+), use current season through previous week
    if week <= 4:
        # Train on prior season (weeks 10-18 for relevance)
        train_data = get_historical_teamweeks(season - 1, 18)
        # Filter to last 8 weeks for recency
        train_data = train_data[train_data['week'] >= 10].copy()
    else:
        # Train on current season through previous week
        train_data = get_historical_teamweeks(season, week - 1)
    
    # Get actual games for this week
    actuals = get_actual_results(season, week)
    
    if actuals.empty:
        print("no games found")
        return pd.DataFrame()
    
    # Build features from training data
    feats = build_features(train_data, recent_weight=config["recent_weight"])
    
    # Create matchups for this week
    matchups = [(row['away_team'], row['home_team']) for _, row in actuals.iterrows()]
    
    try:
        base = join_matchups(feats, matchups)
    except RuntimeError as e:
        print(f"error: {e}")
        return pd.DataFrame()
    
    # Simplified weather/injury (no data for historical)
    base['wind_kph'] = 0.0
    base['is_dome'] = 0
    base['away_injury'] = 0.0
    base['home_injury'] = 0.0
    base['away_PF_adj'] = base['away_PF']
    base['home_PF_adj'] = base['home_PF']
    
    # Train model and predict
    models = fit_expected_points_model(base)
    calibration = config.get("score_calibration_factor", 1.0)
    muA, muH = predict_expected_points(models, base, config["home_field_pts"], calibration)
    
    # Run Monte Carlo
    spread_dummy = np.zeros(len(muA))  # We don't have historical betting lines
    total_dummy = (muA + muH)
    
    out = monte_carlo(muA, muH, team_sd=config["team_sd"], n_sims=config["n_sims"],
                     spread_home=spread_dummy, total_line=total_dummy)
    
    # Build results dataframe
    results = pd.DataFrame({
        'season': season,
        'week': week,
        'away_team': base['away'],
        'home_team': base['home'],
        'away_pred': muA,
        'home_pred': muH,
        'total_pred': muA + muH,
        'margin_pred': muH - muA,
        'home_win_prob': out['home_win_prob']
    })
    
    # Merge with actuals
    results = results.merge(actuals, on=['away_team', 'home_team'], how='inner')
    
    print(f"{len(results)} games")
    return results


def run_full_backtest(season: int = 2025, 
                     start_week: int = 1, 
                     end_week: int = 6,
                     config_path: str = "config.yaml") -> pd.DataFrame:
    """
    Run full backtest across multiple weeks.
    
    Args:
        season: Season to test
        start_week: First week (uses prior season for training if < 5)
        end_week: Last week
        config_path: Path to config
    
    Returns:
        DataFrame with all predictions and actuals
    """
    config = yaml.safe_load(open(config_path))
    
    print("=" * 80)
    print(f"BACKTESTING SEASON {season}, WEEKS {start_week}-{end_week}")
    print("=" * 80)
    print()
    
    all_results = []
    
    for week in range(start_week, end_week + 1):
        result = backtest_single_week(season, week, config)
        if not result.empty:
            all_results.append(result)
    
    if not all_results:
        print("\n❌ No results generated")
        return pd.DataFrame()
    
    combined = pd.concat(all_results, ignore_index=True)
    
    print(f"\n✅ Total games backtested: {len(combined)}")
    return combined


def calculate_backtest_metrics(results: pd.DataFrame) -> dict:
    """Calculate comprehensive metrics from backtest results."""
    if results.empty:
        return {}
    
    # Prediction errors
    total_error = results['total_pred'] - results['total']
    margin_error = results['margin_pred'] - results['margin']
    
    # Win probability accuracy (Brier score)
    actual_home_win = (results['margin'] > 0).astype(int)
    brier_score = ((results['home_win_prob'] - actual_home_win) ** 2).mean()
    
    # Spread accuracy (did we pick the right side?)
    correct_side = ((results['margin'] > 0) == (results['margin_pred'] > 0)).sum()
    spread_accuracy = correct_side / len(results)
    
    # Over/Under accuracy
    correct_over = ((results['total'] > results['total_pred']) == 
                   (results['total_pred'] > results['total_pred'].median())).sum()
    
    metrics = {
        'n_games': len(results),
        'total_mae': total_error.abs().mean(),
        'total_rmse': np.sqrt((total_error ** 2).mean()),
        'total_bias': total_error.mean(),
        'margin_mae': margin_error.abs().mean(),
        'margin_rmse': np.sqrt((margin_error ** 2).mean()),
        'margin_bias': margin_error.mean(),
        'spread_accuracy': spread_accuracy,
        'brier_score': brier_score,
    }
    
    return metrics


def generate_backtest_report(results: pd.DataFrame) -> str:
    """Generate detailed backtest report."""
    if results.empty:
        return "No backtest results available."
    
    metrics = calculate_backtest_metrics(results)
    
    lines = []
    lines.append("=" * 80)
    lines.append("BACKTEST RESULTS REPORT")
    lines.append("=" * 80)
    lines.append(f"\nGames Analyzed: {metrics['n_games']}")
    
    lines.append("\n" + "─" * 80)
    lines.append("TOTAL POINTS PREDICTION")
    lines.append("─" * 80)
    lines.append(f"  MAE (Mean Absolute Error):  {metrics['total_mae']:.2f} points")
    lines.append(f"  RMSE (Root Mean Squared):   {metrics['total_rmse']:.2f} points")
    lines.append(f"  Bias (Model - Actual):      {metrics['total_bias']:+.2f} points")
    
    if abs(metrics['total_bias']) < 3:
        lines.append(f"  ✅ Well calibrated (bias < 3 pts)")
    else:
        lines.append(f"  ⚠️  Systematic bias detected")
    
    lines.append("\n" + "─" * 80)
    lines.append("MARGIN/SPREAD PREDICTION")
    lines.append("─" * 80)
    lines.append(f"  MAE:                        {metrics['margin_mae']:.2f} points")
    lines.append(f"  RMSE:                       {metrics['margin_rmse']:.2f} points")
    lines.append(f"  Bias:                       {metrics['margin_bias']:+.2f} points")
    lines.append(f"  Spread Accuracy:            {metrics['spread_accuracy']*100:.1f}%")
    
    breakeven = 52.38  # Need to beat -110 juice
    if metrics['spread_accuracy'] * 100 > breakeven:
        edge = metrics['spread_accuracy'] * 100 - breakeven
        lines.append(f"  ✅ PROFITABLE ({edge:+.1f}% above breakeven)")
    else:
        edge = breakeven - metrics['spread_accuracy'] * 100
        lines.append(f"  ❌ Not profitable ({edge:.1f}% below breakeven)")
    
    lines.append("\n" + "─" * 80)
    lines.append("PROBABILITY CALIBRATION")
    lines.append("─" * 80)
    lines.append(f"  Brier Score:                {metrics['brier_score']:.4f}")
    lines.append(f"  (Lower is better, perfect = 0.000)")
    
    if metrics['brier_score'] < 0.15:
        lines.append(f"  ✅ Well calibrated probabilities")
    elif metrics['brier_score'] < 0.25:
        lines.append(f"  ⚠️  Moderate calibration")
    else:
        lines.append(f"  ❌ Poor calibration")
    
    lines.append("\n" + "─" * 80)
    lines.append("GAME-BY-GAME RESULTS (Sample)")
    lines.append("─" * 80)
    
    for _, row in results.head(10).iterrows():
        total_err = row['total_pred'] - row['total']
        margin_err = row['margin_pred'] - row['margin']
        lines.append(f"  Week {int(row['week'])}: {row['away_team']}@{row['home_team']}")
        lines.append(f"    Predicted: {row['away_pred']:.1f}-{row['home_pred']:.1f} " +
                    f"(Total: {row['total_pred']:.1f})")
        lines.append(f"    Actual:    {row['away_score']:.0f}-{row['home_score']:.0f} " +
                    f"(Total: {row['total']:.0f})")
        lines.append(f"    Error:     Total {total_err:+.1f}, Margin {margin_err:+.1f}")
    
    lines.append("\n" + "=" * 80)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Run backtest on all available 2025 games
    results = run_full_backtest(season=2025, start_week=1, end_week=6)
    
    if not results.empty:
        # Save results
        Path("artifacts").mkdir(exist_ok=True)
        results.to_csv("artifacts/backtest_results.csv", index=False)
        
        # Generate and save report
        report = generate_backtest_report(results)
        Path("artifacts/backtest_report.txt").write_text(report)
        
        print("\n" + report)
        print(f"\n📁 Saved: artifacts/backtest_results.csv")
        print(f"📁 Saved: artifacts/backtest_report.txt")
    else:
        print("\n❌ Backtest failed - no results generated")

