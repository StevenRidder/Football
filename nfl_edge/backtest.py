"""
Backtesting engine to validate model predictions against historical results.
Measures accuracy, calibration, and hypothetical P&L.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict
import yaml

from nfl_edge.data_ingest import _read_url_csv, NFLVERSE_TEAM_BASE
from nfl_edge.features import build_features, join_matchups, apply_weather_and_injuries
from nfl_edge.model import fit_expected_points_model, predict_expected_points
from nfl_edge.data_ingest import fetch_injury_index


def fetch_historical_games(season: int, weeks: list = None) -> pd.DataFrame:
    """
    Fetch actual game results from nflverse.
    
    Args:
        season: NFL season year (e.g., 2024)
        weeks: List of weeks to fetch (None = all weeks)
    
    Returns:
        DataFrame with columns: season, week, away_team, home_team, 
                                away_score, home_score, total, margin
    """
    # Get team stats (includes scores)
    url = f"{NFLVERSE_TEAM_BASE}stats_team_week_{season}.csv"
    df = _read_url_csv(url)
    
    # Filter to regular season
    df = df[df['season_type'] == 'REG'].copy()
    
    if weeks:
        df = df[df['week'].isin(weeks)]
    
    # Reconstruct scores (same logic as data_ingest.py)
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
    
    # Build games dataframe (one row per game, not per team)
    games = []
    processed = set()
    
    for _, row in df.iterrows():
        week = row['week']
        team = row['team']
        opp = row['opponent_team']
        
        # Skip if already processed this matchup
        game_key = tuple(sorted([team, opp])) + (week,)
        if game_key in processed:
            continue
        processed.add(game_key)
        
        # Get opponent's row
        opp_rows = df[(df['week'] == week) & (df['team'] == opp) & (df['opponent_team'] == team)]
        if opp_rows.empty:
            continue
        opp_row = opp_rows.iloc[0]
        
        # Determine home/away (nflverse doesn't always flag this clearly)
        # We'll use a simple heuristic: if team is listed first alphabetically, call them away
        if team < opp:
            away_team, away_score = team, row['score']
            home_team, home_score = opp, opp_row['score']
        else:
            away_team, away_score = opp, opp_row['score']
            home_team, home_score = team, row['score']
        
        games.append({
            'season': season,
            'week': week,
            'away_team': away_team,
            'home_team': home_team,
            'away_score': away_score,
            'home_score': home_score,
            'total': away_score + home_score,
            'margin': home_score - away_score
        })
    
    return pd.DataFrame(games).sort_values(['week', 'away_team'])


def backtest_week(season: int, week: int, 
                 train_through_week: int,
                 config: dict) -> pd.DataFrame:
    """
    Run model on a single historical week and compare to actual results.
    
    Args:
        season: Season year
        week: Week to predict
        train_through_week: Last week of data to use for training (week-1)
        config: Config dict with model parameters
    
    Returns:
        DataFrame with predictions and actuals
    """
    # Fetch training data (through previous week)
    url = f"{NFLVERSE_TEAM_BASE}stats_team_week_{season}.csv"
    df = _read_url_csv(url)
    df = df[(df['season_type'] == 'REG') & (df['week'] <= train_through_week)].copy()
    
    # Convert to teamweeks format (same as data_ingest.py)
    from nfl_edge.data_ingest import fetch_teamweeks_live
    # We'll reuse the same transformation logic
    # For now, simplified version:
    
    print(f"  Backtesting Week {week} (training through Week {train_through_week})...")
    
    # This is a placeholder - in production, would need full pipeline
    # For now, return empty to build infrastructure
    return pd.DataFrame()


def run_backtest(season: int, start_week: int = 5, end_week: int = 18,
                config_path: str = "config.yaml") -> pd.DataFrame:
    """
    Run backtesting across multiple weeks.
    
    Args:
        season: Season to backtest (e.g., 2024)
        start_week: First week to test (default 5, so we have 4 weeks of training)
        end_week: Last week to test (default 18)
        config_path: Path to config file
    
    Returns:
        DataFrame with all predictions and results
    """
    cfg = yaml.safe_load(open(config_path))
    
    print("=" * 80)
    print(f"BACKTESTING SEASON {season}, WEEKS {start_week}-{end_week}")
    print("=" * 80)
    
    # Fetch actual results
    print("\nFetching actual game results...")
    actuals = fetch_historical_games(season, list(range(start_week, end_week + 1)))
    print(f"Found {len(actuals)} games")
    
    # Run model for each week
    all_predictions = []
    
    for week in range(start_week, end_week + 1):
        preds = backtest_week(season, week, week - 1, cfg)
        if not preds.empty:
            all_predictions.append(preds)
    
    if not all_predictions:
        return pd.DataFrame()
    
    predictions = pd.concat(all_predictions, ignore_index=True)
    
    # Merge predictions with actuals
    results = predictions.merge(
        actuals,
        on=['season', 'week', 'away_team', 'home_team'],
        how='inner',
        suffixes=('_pred', '_actual')
    )
    
    return results


def calculate_metrics(results: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate backtest performance metrics.
    
    Args:
        results: DataFrame from run_backtest with predictions and actuals
    
    Returns:
        Dictionary of metrics
    """
    if results.empty:
        return {}
    
    # Total error
    total_error = results['total_pred'] - results['total']
    margin_error = results['margin_pred'] - results['margin']
    
    metrics = {
        'n_games': len(results),
        'mean_total_error': total_error.mean(),
        'mae_total': total_error.abs().mean(),
        'rmse_total': np.sqrt((total_error ** 2).mean()),
        'mean_margin_error': margin_error.mean(),
        'mae_margin': margin_error.abs().mean(),
        'rmse_margin': np.sqrt((margin_error ** 2).mean()),
    }
    
    # Spread accuracy (if we had predicted spreads)
    if 'spread_pred' in results.columns:
        correct_spread = ((results['margin'] > 0) == (results['spread_pred'] < 0)).sum()
        metrics['spread_accuracy'] = correct_spread / len(results)
    
    # Over/Under accuracy (if we had predicted over/under)
    if 'over_pred' in results.columns:
        correct_over = ((results['total'] > results['total_line']) == 
                       (results['over_pred'] > 0.5)).sum()
        metrics['over_accuracy'] = correct_over / len(results)
    
    return metrics


def generate_backtest_report(results: pd.DataFrame, 
                            output_path: str = "artifacts/backtest_report.txt") -> str:
    """
    Generate human-readable backtest report.
    
    Args:
        results: DataFrame from run_backtest
        output_path: Where to save report
    
    Returns:
        Report text
    """
    if results.empty:
        return "No backtest results available."
    
    metrics = calculate_metrics(results)
    
    lines = []
    lines.append("=" * 80)
    lines.append("BACKTEST REPORT")
    lines.append("=" * 80)
    lines.append(f"\nGames Analyzed: {metrics['n_games']}")
    lines.append(f"\nTOTAL PREDICTIONS:")
    lines.append(f"  Mean Error:  {metrics['mean_total_error']:+.1f} points")
    lines.append(f"  MAE:         {metrics['mae_total']:.1f} points")
    lines.append(f"  RMSE:        {metrics['rmse_total']:.1f} points")
    
    lines.append(f"\nMARGIN PREDICTIONS:")
    lines.append(f"  Mean Error:  {metrics['mean_margin_error']:+.1f} points")
    lines.append(f"  MAE:         {metrics['mae_margin']:.1f} points")
    lines.append(f"  RMSE:        {metrics['rmse_margin']:.1f} points")
    
    if 'spread_accuracy' in metrics:
        lines.append(f"\nSPREAD ACCURACY: {metrics['spread_accuracy']*100:.1f}%")
        lines.append(f"  (Need >52.4% to beat -110 juice)")
    
    if 'over_accuracy' in metrics:
        lines.append(f"\nOVER/UNDER ACCURACY: {metrics['over_accuracy']*100:.1f}%")
        lines.append(f"  (Need >52.4% to beat -110 juice)")
    
    lines.append("\n" + "=" * 80)
    
    report = "\n".join(lines)
    
    Path(output_path).parent.mkdir(exist_ok=True)
    Path(output_path).write_text(report)
    
    return report


