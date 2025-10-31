"""
Phase 1 - Step 4: Backtest EPA vs EPA+PFF

Compare two models:
1. EPA-only: Current Monte Carlo simulation (baseline)
2. EPA+PFF: Add OL/DL matchup features to Ridge regression

Goal: Does PFF add incremental value to EPA?
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import nfl_data_py as nfl
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
SCRIPT_DIR = Path(__file__).parent


def load_epa_data():
    """Load EPA data for 2022-2024."""
    print("📊 Loading EPA data...")
    
    pbp = nfl.import_pbp_data([2022, 2023, 2024])
    
    # Calculate team EPA
    team_epa = pbp.groupby(['season', 'posteam']).agg({
        'epa': 'mean',
        'qb_epa': 'mean'
    }).reset_index()
    team_epa.columns = ['season', 'team', 'off_epa', 'off_qb_epa']
    
    # Calculate defensive EPA (EPA allowed)
    def_epa = pbp.groupby(['season', 'defteam']).agg({
        'epa': 'mean'
    }).reset_index()
    def_epa.columns = ['season', 'team', 'def_epa']
    
    # Merge
    epa_df = team_epa.merge(def_epa, on=['season', 'team'], how='outer')
    epa_df = epa_df.fillna(0)
    
    print(f"   Team-seasons: {len(epa_df)}")
    
    return epa_df


def load_pff_matchup_data():
    """Load PFF matchup metrics."""
    print("📊 Loading PFF matchup data...")
    
    df = pd.read_csv(DATA_DIR / "matchup_metrics_2022_2024.csv")
    
    # Filter to completed games
    completed = df[df['point_differential'].notna()].copy()
    
    print(f"   Games: {len(completed)}")
    
    return completed


def merge_features(matchup_df, epa_df):
    """Merge EPA and PFF features for each game."""
    print("\n🔬 Merging features...")
    
    # Merge away team EPA
    merged = matchup_df.merge(
        epa_df,
        left_on=['season', 'away_team'],
        right_on=['season', 'team'],
        how='left',
        suffixes=('', '_away')
    )
    merged = merged.rename(columns={
        'off_epa': 'away_off_epa',
        'off_qb_epa': 'away_qb_epa',
        'def_epa': 'away_def_epa'
    })
    merged = merged.drop(columns=['team'], errors='ignore')
    
    # Merge home team EPA
    merged = merged.merge(
        epa_df,
        left_on=['season', 'home_team'],
        right_on=['season', 'team'],
        how='left',
        suffixes=('', '_home')
    )
    merged = merged.rename(columns={
        'off_epa': 'home_off_epa',
        'off_qb_epa': 'home_qb_epa',
        'def_epa': 'home_def_epa'
    })
    merged = merged.drop(columns=['team'], errors='ignore')
    
    # Fill NaN with 0
    merged = merged.fillna(0)
    
    print(f"   Merged games: {len(merged)}")
    
    return merged


def backtest_epa_only(df):
    """Backtest using EPA features only."""
    print("\n" + "="*80)
    print("MODEL 1: EPA-ONLY")
    print("="*80)
    
    # Features: EPA only
    feature_cols = [
        'away_off_epa', 'away_qb_epa', 'away_def_epa',
        'home_off_epa', 'home_qb_epa', 'home_def_epa'
    ]
    
    X = df[feature_cols].values
    y = df['point_differential'].values
    
    # Time series split (chronological)
    tscv = TimeSeriesSplit(n_splits=3)
    
    predictions = []
    actuals = []
    
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Ridge
        model = Ridge(alpha=1.0)
        model.fit(X_train_scaled, y_train)
        
        # Predict
        y_pred = model.predict(X_test_scaled)
        
        predictions.extend(y_pred)
        actuals.extend(y_test)
    
    predictions = np.array(predictions)
    actuals = np.array(actuals)
    
    # Calculate metrics
    mae = np.mean(np.abs(predictions - actuals))
    rmse = np.sqrt(np.mean((predictions - actuals)**2))
    corr = np.corrcoef(predictions, actuals)[0, 1]
    
    # Directional accuracy
    pred_home_win = predictions > 0
    actual_home_win = actuals > 0
    accuracy = np.mean(pred_home_win == actual_home_win)
    
    print(f"\n📊 MAE: {mae:.2f} points")
    print(f"📊 RMSE: {rmse:.2f} points")
    print(f"📊 Correlation: {corr:.4f}")
    print(f"📊 Directional Accuracy: {accuracy:.1%}")
    
    return {
        'model': 'EPA-only',
        'mae': mae,
        'rmse': rmse,
        'correlation': corr,
        'accuracy': accuracy,
        'predictions': predictions,
        'actuals': actuals
    }


def backtest_epa_plus_pff(df):
    """Backtest using EPA + PFF features."""
    print("\n" + "="*80)
    print("MODEL 2: EPA + PFF")
    print("="*80)
    
    # Features: EPA + PFF matchup metrics
    feature_cols = [
        'away_off_epa', 'away_qb_epa', 'away_def_epa',
        'home_off_epa', 'home_qb_epa', 'home_def_epa',
        'away_ol_grade', 'home_ol_grade',
        'away_dl_grade', 'home_dl_grade',
        'pressure_edge_away', 'pressure_edge_home',
        'net_pressure_advantage'
    ]
    
    X = df[feature_cols].values
    y = df['point_differential'].values
    
    # Time series split (chronological)
    tscv = TimeSeriesSplit(n_splits=3)
    
    predictions = []
    actuals = []
    
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Ridge
        model = Ridge(alpha=1.0)
        model.fit(X_train_scaled, y_train)
        
        # Predict
        y_pred = model.predict(X_test_scaled)
        
        predictions.extend(y_pred)
        actuals.extend(y_test)
    
    predictions = np.array(predictions)
    actuals = np.array(actuals)
    
    # Calculate metrics
    mae = np.mean(np.abs(predictions - actuals))
    rmse = np.sqrt(np.mean((predictions - actuals)**2))
    corr = np.corrcoef(predictions, actuals)[0, 1]
    
    # Directional accuracy
    pred_home_win = predictions > 0
    actual_home_win = actuals > 0
    accuracy = np.mean(pred_home_win == actual_home_win)
    
    print(f"\n📊 MAE: {mae:.2f} points")
    print(f"📊 RMSE: {rmse:.2f} points")
    print(f"📊 Correlation: {corr:.4f}")
    print(f"📊 Directional Accuracy: {accuracy:.1%}")
    
    return {
        'model': 'EPA+PFF',
        'mae': mae,
        'rmse': rmse,
        'correlation': corr,
        'accuracy': accuracy,
        'predictions': predictions,
        'actuals': actuals
    }


def compare_models(epa_results, pff_results):
    """Compare the two models."""
    print("\n" + "="*80)
    print("📊 MODEL COMPARISON")
    print("="*80)
    
    print("\n" + "-"*80)
    print(f"{'Metric':<25} {'EPA-only':<15} {'EPA+PFF':<15} {'Winner':<15}")
    print("-"*80)
    
    # MAE (lower is better)
    mae_winner = "EPA+PFF ✅" if pff_results['mae'] < epa_results['mae'] else "EPA-only ✅"
    print(f"{'MAE (points)':<25} {epa_results['mae']:<15.2f} {pff_results['mae']:<15.2f} {mae_winner:<15}")
    
    # RMSE (lower is better)
    rmse_winner = "EPA+PFF ✅" if pff_results['rmse'] < epa_results['rmse'] else "EPA-only ✅"
    print(f"{'RMSE (points)':<25} {epa_results['rmse']:<15.2f} {pff_results['rmse']:<15.2f} {rmse_winner:<15}")
    
    # Correlation (higher is better)
    corr_winner = "EPA+PFF ✅" if pff_results['correlation'] > epa_results['correlation'] else "EPA-only ✅"
    print(f"{'Correlation':<25} {epa_results['correlation']:<15.4f} {pff_results['correlation']:<15.4f} {corr_winner:<15}")
    
    # Accuracy (higher is better)
    acc_winner = "EPA+PFF ✅" if pff_results['accuracy'] > epa_results['accuracy'] else "EPA-only ✅"
    print(f"{'Directional Accuracy':<25} {epa_results['accuracy']:<15.1%} {pff_results['accuracy']:<15.1%} {acc_winner:<15}")
    
    print("-"*80)
    
    # Overall winner
    pff_wins = sum([
        pff_results['mae'] < epa_results['mae'],
        pff_results['rmse'] < epa_results['rmse'],
        pff_results['correlation'] > epa_results['correlation'],
        pff_results['accuracy'] > epa_results['accuracy']
    ])
    
    print(f"\n🏆 Overall: EPA+PFF wins {pff_wins}/4 metrics")
    
    if pff_wins >= 3:
        print("\n✅ CONCLUSION: PFF adds significant value to EPA model!")
        print("   → Recommend integrating PFF matchup features")
    elif pff_wins >= 2:
        print("\n⚠️  CONCLUSION: PFF adds marginal value to EPA model")
        print("   → Consider integrating if improvement is meaningful")
    else:
        print("\n❌ CONCLUSION: PFF does NOT add value to EPA model")
        print("   → Stick with EPA-only approach")


def main():
    """Run backtest comparison."""
    print("="*80)
    print("PHASE 1 - STEP 4: BACKTEST EPA vs EPA+PFF")
    print("="*80)
    
    # Load data
    epa_df = load_epa_data()
    matchup_df = load_pff_matchup_data()
    
    # Merge features
    df = merge_features(matchup_df, epa_df)
    
    # Backtest both models
    epa_results = backtest_epa_only(df)
    pff_results = backtest_epa_plus_pff(df)
    
    # Compare
    compare_models(epa_results, pff_results)
    
    print("\n" + "="*80)
    print("✅ BACKTEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

