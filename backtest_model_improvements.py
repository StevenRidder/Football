#!/usr/bin/env python3
"""
Backtest model improvements:
- Compare OLD model (calibration=0.69, no success rates, no injuries, no situational features)
- vs NEW model (calibration=0.95, fixed success rates, injuries, situational features)

Backtest on:
- 2024 season (all weeks, weight=1.0)
- 2025 season (8 weeks, weight=2.0)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import yaml
from datetime import datetime

from nfl_edge.data_ingest import fetch_teamweeks_live, fetch_weather_for_matchups, fetch_injury_index
from nfl_edge.features import build_features, join_matchups, apply_weather_and_injuries
from nfl_edge.model import fit_expected_points_model, predict_expected_points
from nfl_edge.situational_features import add_all_situational_features


def get_actual_scores(season, week):
    """Fetch actual game results from nflverse"""
    try:
        url = f"https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_{season}.csv"
        df = pd.read_csv(url)
        
        # Filter to specific week
        week_data = df[df['week'] == week].copy()
        
        # Get scores
        scores = {}
        for _, row in week_data.iterrows():
            team = row['team']
            opponent = row['opponent_team']
            
            # Reconstruct points
            td_cols = ['passing_tds', 'rushing_tds', 'receiving_tds', 'def_tds', 'special_teams_tds']
            td_total = sum(row.get(c, 0) for c in td_cols)
            fg_made = row.get('fg_made', 0)
            pat_made = row.get('pat_made', 0)
            safeties = row.get('def_safeties', 0)
            pass_2pt = row.get('passing_2pt_conversions', 0)
            rush_2pt = row.get('rushing_2pt_conversions', 0)
            recv_2pt = row.get('receiving_2pt_conversions', 0)
            
            points = 6 * td_total + 3 * fg_made + 1 * pat_made + 2 * (safeties + pass_2pt + rush_2pt + recv_2pt)
            
            # Store as (away, home) tuple
            if (opponent, team) not in scores:
                scores[(team, opponent)] = {'away': team, 'home': opponent, 'away_score': points, 'home_score': None}
            else:
                scores[(opponent, team)]['home_score'] = points
        
        # Convert to list
        results = []
        for key, val in scores.items():
            if val['home_score'] is not None:
                results.append(val)
        
        return pd.DataFrame(results)
    
    except Exception as e:
        print(f"⚠️ Could not fetch scores for {season} Week {week}: {e}")
        return pd.DataFrame()


def run_model_old(teamweeks, matchups, cfg):
    """Run OLD model (0.69 calibration, no situational features)"""
    feats = build_features(teamweeks, recent_weight=cfg["recent_weight"])
    base = join_matchups(feats, matchups)
    weather = fetch_weather_for_matchups(matchups=matchups)
    
    # OLD: No injury data (always 0)
    injuries = pd.DataFrame([{"team": t, "injury_index": 0.0} for away, home in matchups for t in [away, home]]).drop_duplicates("team")
    
    # OLD: No situational features
    matches = apply_weather_and_injuries(base, weather, injuries, situational_df=None)
    
    models = fit_expected_points_model(matches)
    
    # OLD: 0.69 calibration
    muA, muH = predict_expected_points(models, matches, cfg["home_field_pts"], calibration_factor=0.69)
    
    return muA, muH, matches


def run_model_new(teamweeks, matchups, cfg, week=1):
    """Run NEW model (0.95 calibration, with situational features)"""
    feats = build_features(teamweeks, recent_weight=cfg["recent_weight"])
    base = join_matchups(feats, matchups)
    weather = fetch_weather_for_matchups(matchups=matchups)
    
    # NEW: Real injury data
    try:
        injuries = fetch_injury_index(matchups=matchups)
    except:
        injuries = pd.DataFrame([{"team": t, "injury_index": 0.0} for away, home in matchups for t in [away, home]]).drop_duplicates("team")
    
    # NEW: Situational features
    situational = add_all_situational_features(matchups, current_week=week)
    
    matches = apply_weather_and_injuries(base, weather, injuries, situational)
    
    models = fit_expected_points_model(matches)
    
    # NEW: 0.95 calibration
    muA, muH = predict_expected_points(models, matches, cfg["home_field_pts"], calibration_factor=0.95)
    
    return muA, muH, matches


def calculate_metrics(predictions, actuals):
    """Calculate prediction accuracy metrics"""
    if len(predictions) == 0 or len(actuals) == 0:
        return {}
    
    # Merge predictions with actuals
    merged = predictions.merge(actuals, on=['away', 'home'], how='inner')
    
    if len(merged) == 0:
        return {}
    
    # Calculate errors
    away_error = np.abs(merged['pred_away'] - merged['away_score'])
    home_error = np.abs(merged['pred_home'] - merged['home_score'])
    total_error = np.abs((merged['pred_away'] + merged['pred_home']) - (merged['away_score'] + merged['home_score']))
    
    # Calculate spread accuracy
    pred_spread = merged['pred_home'] - merged['pred_away']
    actual_spread = merged['home_score'] - merged['away_score']
    spread_error = np.abs(pred_spread - actual_spread)
    
    # Winner accuracy (did we predict the right winner?)
    pred_winner_correct = ((pred_spread > 0) & (actual_spread > 0)) | ((pred_spread < 0) & (actual_spread < 0))
    winner_accuracy = pred_winner_correct.mean()
    
    return {
        'games': len(merged),
        'mae_away': away_error.mean(),
        'mae_home': home_error.mean(),
        'mae_total': total_error.mean(),
        'mae_spread': spread_error.mean(),
        'winner_accuracy': winner_accuracy,
        'rmse_away': np.sqrt((away_error ** 2).mean()),
        'rmse_home': np.sqrt((home_error ** 2).mean()),
        'rmse_total': np.sqrt((total_error ** 2).mean()),
        'rmse_spread': np.sqrt((spread_error ** 2).mean())
    }


def backtest_season(season, weeks, cfg, weight=1.0):
    """Backtest a full season"""
    print(f"\n{'='*60}")
    print(f"Backtesting {season} Season (Weeks {min(weeks)}-{max(weeks)})")
    print(f"Weight: {weight}x")
    print(f"{'='*60}")
    
    old_metrics_list = []
    new_metrics_list = []
    
    # Fetch all team-week data for the season
    try:
        teamweeks = fetch_teamweeks_live(season=season)
    except Exception as e:
        print(f"❌ Could not fetch data for {season}: {e}")
        return None, None
    
    for week in weeks:
        print(f"\n📅 Week {week}...")
        
        # Get matchups for this week
        week_games = teamweeks[teamweeks['week'] == week]
        matchups = []
        seen = set()
        for _, row in week_games.iterrows():
            pair = tuple(sorted([row['team'], row['opponent']]))
            if pair not in seen:
                # Determine home/away (arbitrary for backtest)
                matchups.append((row['opponent'], row['team']))
                seen.add(pair)
        
        if len(matchups) == 0:
            print(f"  ⚠️ No games found for Week {week}")
            continue
        
        print(f"  Found {len(matchups)} games")
        
        # Get actual scores
        actuals = get_actual_scores(season, week)
        if len(actuals) == 0:
            print(f"  ⚠️ No actual scores found")
            continue
        
        # Run OLD model
        try:
            muA_old, muH_old, matches_old = run_model_old(teamweeks[teamweeks['week'] < week], matchups, cfg)
            preds_old = pd.DataFrame({
                'away': matches_old['away'],
                'home': matches_old['home'],
                'pred_away': muA_old,
                'pred_home': muH_old
            })
            metrics_old = calculate_metrics(preds_old, actuals)
            if metrics_old:
                old_metrics_list.append(metrics_old)
                print(f"  OLD Model: MAE Spread={metrics_old['mae_spread']:.2f}, Winner Acc={metrics_old['winner_accuracy']:.1%}")
        except Exception as e:
            print(f"  ❌ OLD model failed: {e}")
        
        # Run NEW model
        try:
            muA_new, muH_new, matches_new = run_model_new(teamweeks[teamweeks['week'] < week], matchups, cfg, week=week)
            preds_new = pd.DataFrame({
                'away': matches_new['away'],
                'home': matches_new['home'],
                'pred_away': muA_new,
                'pred_home': muH_new
            })
            metrics_new = calculate_metrics(preds_new, actuals)
            if metrics_new:
                new_metrics_list.append(metrics_new)
                print(f"  NEW Model: MAE Spread={metrics_new['mae_spread']:.2f}, Winner Acc={metrics_new['winner_accuracy']:.1%}")
        except Exception as e:
            print(f"  ❌ NEW model failed: {e}")
    
    # Aggregate metrics
    if len(old_metrics_list) == 0 or len(new_metrics_list) == 0:
        print(f"\n❌ Not enough data to compare models for {season}")
        return None, None
    
    old_agg = {
        'season': season,
        'weight': weight,
        'games': sum(m['games'] for m in old_metrics_list),
        'mae_spread': np.mean([m['mae_spread'] for m in old_metrics_list]),
        'winner_accuracy': np.mean([m['winner_accuracy'] for m in old_metrics_list]),
        'rmse_spread': np.mean([m['rmse_spread'] for m in old_metrics_list])
    }
    
    new_agg = {
        'season': season,
        'weight': weight,
        'games': sum(m['games'] for m in new_metrics_list),
        'mae_spread': np.mean([m['mae_spread'] for m in new_metrics_list]),
        'winner_accuracy': np.mean([m['winner_accuracy'] for m in new_metrics_list]),
        'rmse_spread': np.mean([m['rmse_spread'] for m in new_metrics_list])
    }
    
    print(f"\n📊 {season} Season Summary:")
    print(f"  OLD Model: MAE Spread={old_agg['mae_spread']:.2f}, Winner Acc={old_agg['winner_accuracy']:.1%}")
    print(f"  NEW Model: MAE Spread={new_agg['mae_spread']:.2f}, Winner Acc={new_agg['winner_accuracy']:.1%}")
    print(f"  Improvement: {((new_agg['mae_spread'] - old_agg['mae_spread']) / old_agg['mae_spread'] * 100):.1f}% MAE, {((new_agg['winner_accuracy'] - old_agg['winner_accuracy']) * 100):.1f}% Winner Acc")
    
    return old_agg, new_agg


def main():
    # Load config
    cfg = yaml.safe_load(open("config.yaml"))
    
    print("\n" + "="*60)
    print("🏈 NFL MODEL BACKTEST: OLD vs NEW")
    print("="*60)
    print("\nOLD Model:")
    print("  - Calibration: 0.69")
    print("  - Success rates: NaN (broken)")
    print("  - Injuries: 0.0 (placeholder)")
    print("  - Situational features: None")
    print("\nNEW Model:")
    print("  - Calibration: 0.95")
    print("  - Success rates: EPA-based (fixed)")
    print("  - Injuries: Real data from nflverse")
    print("  - Situational features: Travel, divisional, rest")
    
    # Backtest 2024 season (weight=1.0)
    old_2024, new_2024 = backtest_season(2024, range(1, 19), cfg, weight=1.0)
    
    # Backtest 2025 season (weight=2.0)
    old_2025, new_2025 = backtest_season(2025, range(1, 9), cfg, weight=2.0)
    
    # Calculate weighted average
    if old_2024 and new_2024 and old_2025 and new_2025:
        print("\n" + "="*60)
        print("📈 WEIGHTED OVERALL RESULTS")
        print("="*60)
        
        total_weight = old_2024['weight'] + old_2025['weight']
        
        old_weighted_mae = (old_2024['mae_spread'] * old_2024['weight'] + old_2025['mae_spread'] * old_2025['weight']) / total_weight
        new_weighted_mae = (new_2024['mae_spread'] * new_2024['weight'] + new_2025['mae_spread'] * new_2025['weight']) / total_weight
        
        old_weighted_acc = (old_2024['winner_accuracy'] * old_2024['weight'] + old_2025['winner_accuracy'] * old_2025['weight']) / total_weight
        new_weighted_acc = (new_2024['winner_accuracy'] * new_2024['weight'] + new_2025['winner_accuracy'] * new_2025['weight']) / total_weight
        
        print(f"\nOLD Model (Weighted):")
        print(f"  MAE Spread: {old_weighted_mae:.2f} points")
        print(f"  Winner Accuracy: {old_weighted_acc:.1%}")
        
        print(f"\nNEW Model (Weighted):")
        print(f"  MAE Spread: {new_weighted_mae:.2f} points")
        print(f"  Winner Accuracy: {new_weighted_acc:.1%}")
        
        mae_improvement = ((old_weighted_mae - new_weighted_mae) / old_weighted_mae) * 100
        acc_improvement = (new_weighted_acc - old_weighted_acc) * 100
        
        print(f"\n🎯 IMPROVEMENT:")
        print(f"  MAE Spread: {mae_improvement:+.1f}% (lower is better)")
        print(f"  Winner Accuracy: {acc_improvement:+.1f} percentage points")
        
        if mae_improvement > 0 and acc_improvement > 0:
            print(f"\n✅ NEW model is BETTER on both metrics!")
        elif mae_improvement > 0 or acc_improvement > 0:
            print(f"\n⚠️ NEW model is MIXED (better on some metrics)")
        else:
            print(f"\n❌ NEW model is WORSE (needs more tuning)")
        
        # Save results
        results_df = pd.DataFrame([
            {'model': 'OLD', 'season': 2024, 'mae_spread': old_2024['mae_spread'], 'winner_acc': old_2024['winner_accuracy']},
            {'model': 'NEW', 'season': 2024, 'mae_spread': new_2024['mae_spread'], 'winner_acc': new_2024['winner_accuracy']},
            {'model': 'OLD', 'season': 2025, 'mae_spread': old_2025['mae_spread'], 'winner_acc': old_2025['winner_accuracy']},
            {'model': 'NEW', 'season': 2025, 'mae_spread': new_2025['mae_spread'], 'winner_acc': new_2025['winner_accuracy']},
            {'model': 'OLD', 'season': 'Weighted', 'mae_spread': old_weighted_mae, 'winner_acc': old_weighted_acc},
            {'model': 'NEW', 'season': 'Weighted', 'mae_spread': new_weighted_mae, 'winner_acc': new_weighted_acc}
        ])
        
        Path("artifacts").mkdir(exist_ok=True)
        results_df.to_csv("artifacts/backtest_results.csv", index=False)
        print(f"\n💾 Results saved to artifacts/backtest_results.csv")


if __name__ == "__main__":
    main()

