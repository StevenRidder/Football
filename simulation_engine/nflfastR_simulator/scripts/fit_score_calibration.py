"""
Fit calibration model to predict ACTUAL SCORES (not market-aligned).

Priority 1 from AUDIT_REPORT: Predict actual scores using raw simulator outputs.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pickle

def load_backtest_data():
    """Load historical backtest with raw scores and actual outcomes."""
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        raise FileNotFoundError(f"Backtest file not found: {backtest_file}")
    
    df = pd.read_csv(backtest_file)
    
    # Filter to completed games
    completed = df[df['actual_home_score'].notna()].copy()
    
    print(f"✅ Loaded {len(completed)} completed games")
    
    return completed

def prepare_features(df):
    """
    Prepare features for score calibration.
    
    Features:
    - Raw simulator scores (home/away/total/spread)
    - Raw simulator SDs
    - Situational factors (pace, dome, rest days)
    - Team strength indicators
    """
    features = []
    feature_names = []
    
    # Raw simulator outputs (PRIMARY FEATURES)
    if 'home_score_raw' in df.columns:
        features.append(df['home_score_raw'].fillna(df['total_raw'] / 2.0))
        feature_names.append('home_raw')
    elif 'total_raw' in df.columns and 'spread_raw' in df.columns:
        # Reconstruct from total and spread
        features.append((df['total_raw'] + df['spread_raw']) / 2.0)
        feature_names.append('home_raw')
    
    if 'away_score_raw' in df.columns:
        features.append(df['away_score_raw'].fillna(df['total_raw'] / 2.0))
        feature_names.append('away_raw')
    elif 'total_raw' in df.columns and 'spread_raw' in df.columns:
        features.append((df['total_raw'] - df['spread_raw']) / 2.0)
        feature_names.append('away_raw')
    
    if 'total_raw' in df.columns:
        features.append(df['total_raw'])
        feature_names.append('total_raw')
    else:
        features.append(np.zeros(len(df)))
        feature_names.append('total_raw')
    
    if 'spread_raw' in df.columns:
        features.append(df['spread_raw'])
        feature_names.append('spread_raw')
    else:
        features.append(np.zeros(len(df)))
        feature_names.append('spread_raw')
    
    # Variability indicators (SDs)
    if 'total_raw_sd' in df.columns:
        features.append(df['total_raw_sd'].fillna(9.0))
        feature_names.append('total_sd')
    else:
        features.append(np.full(len(df), 9.0))
        feature_names.append('total_sd')
    
    if 'spread_raw_sd' in df.columns:
        features.append(df['spread_raw_sd'].fillna(13.0))
        feature_names.append('spread_sd')
    else:
        features.append(np.full(len(df), 13.0))
        feature_names.append('spread_sd')
    
    # Situational factors (if available)
    # Note: These may not be in backtest CSV - will need to merge from other sources
    
    # Combine features
    X = np.column_stack(features)
    
    return X, feature_names

def fit_score_calibration(df):
    """
    Fit calibration model to predict actual scores from raw simulator outputs.
    
    Returns:
        Fitted model, scaler, feature names
    """
    print("\n" + "="*70)
    print("FITTING SCORE-LEVEL CALIBRATION")
    print("="*70)
    
    # Prepare features and targets
    X, feature_names = prepare_features(df)
    
    # Targets: actual scores
    y_home = df['actual_home_score'].values
    y_away = df['actual_away_score'].values
    y_total = df['actual_home_score'].values + df['actual_away_score'].values
    
    # Filter out missing targets
    valid_mask = ~(np.isnan(y_home) | np.isnan(y_away))
    X = X[valid_mask]
    y_home = y_home[valid_mask]
    y_away = y_away[valid_mask]
    y_total = y_total[valid_mask]
    
    print(f"\n📊 Dataset: {len(X)} games with complete data")
    print(f"   Features: {', '.join(feature_names)}")
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Fit separate models for home, away, total
    print(f"\n🔧 Fitting calibration models...")
    
    # Home score model
    model_home = Ridge(alpha=1.0)
    model_home.fit(X_scaled, y_home)
    home_score = model_home.score(X_scaled, y_home)
    print(f"   Home score: R² = {home_score:.3f}")
    
    # Away score model
    model_away = Ridge(alpha=1.0)
    model_away.fit(X_scaled, y_away)
    away_score = model_away.score(X_scaled, y_away)
    print(f"   Away score: R² = {away_score:.3f}")
    
    # Total model
    model_total = Ridge(alpha=1.0)
    model_total.fit(X_scaled, y_total)
    total_score = model_total.score(X_scaled, y_total)
    print(f"   Total score: R² = {total_score:.3f}")
    
    # Evaluate on test set
    X_train, X_test, y_home_train, y_home_test, y_away_train, y_away_test, y_total_train, y_total_test = train_test_split(
        X_scaled, y_home, y_away, y_total, test_size=0.2, random_state=42
    )
    
    # Refit on train
    model_home.fit(X_train, y_home_train)
    model_away.fit(X_train, y_away_train)
    model_total.fit(X_train, y_total_train)
    
    # Test predictions
    pred_home = model_home.predict(X_test)
    pred_away = model_away.predict(X_test)
    pred_total = model_total.predict(X_test)
    
    # Calculate metrics
    mae_home = np.mean(np.abs(pred_home - y_home_test))
    mae_away = np.mean(np.abs(pred_away - y_away_test))
    mae_total = np.mean(np.abs(pred_total - y_total_test))
    
    print(f"\n📈 Test Set Performance:")
    print(f"   Home MAE: {mae_home:.2f} points")
    print(f"   Away MAE: {mae_away:.2f} points")
    print(f"   Total MAE: {mae_total:.2f} points")
    
    return {
        'model_home': model_home,
        'model_away': model_away,
        'model_total': model_total,
        'scaler': scaler,
        'feature_names': feature_names
    }, {
        'train_r2_home': home_score,
        'train_r2_away': away_score,
        'train_r2_total': total_score,
        'test_mae_home': mae_home,
        'test_mae_away': mae_away,
        'test_mae_total': mae_total,
    }

def save_calibration(models_dict, metrics_dict):
    """Save fitted calibration models."""
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    # Save models
    with open(artifacts_dir / "score_calibration.pkl", 'wb') as f:
        pickle.dump(models_dict, f)
    
    # Save metrics
    import json
    with open(artifacts_dir / "score_calibration_metrics.json", 'w') as f:
        json.dump(metrics_dict, f, indent=2)
    
    print(f"\n💾 Saved calibration models to: {artifacts_dir / 'score_calibration.pkl'}")
    print(f"💾 Saved metrics to: {artifacts_dir / 'score_calibration_metrics.json'}")

if __name__ == "__main__":
    print("="*70)
    print("SCORE-LEVEL CALIBRATION")
    print("Predicting ACTUAL SCORES from raw simulator outputs")
    print("="*70)
    
    # Load data
    df = load_backtest_data()
    
    # Fit calibration
    models_dict, metrics_dict = fit_score_calibration(df)
    
    # Save
    save_calibration(models_dict, metrics_dict)
    
    print("\n✅ Calibration complete!")
    print("\n📋 Next Steps:")
    print("   1. Update backtest_all_games_conviction.py to use score calibration")
    print("   2. Remove or make market centering optional")
    print("   3. Test on OOS data (2025 weeks 1-8)")

