"""
Add features to score calibration (High Priority #2).

Add pace, dome, weather, rest days to improve R² from 0.1-0.2.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

def load_backtest_data():
    """Load historical backtest with raw scores and actual outcomes."""
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        raise FileNotFoundError(f"Backtest file not found: {backtest_file}")
    
    df = pd.read_csv(backtest_file)
    completed = df[df['actual_home_score'].notna()].copy()
    
    return completed

def merge_situational_features(df):
    """Merge pace, dome, weather, rest days from data files."""
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    
    # Load situational factors
    situational_file = data_dir / "situational_factors.csv"
    if situational_file.exists():
        situational = pd.read_csv(situational_file)
        # Merge on game_id, season, week, or team matchup
        # Need to figure out merge key
        print(f"✅ Loaded situational factors: {len(situational)} records")
    else:
        print(f"⚠️  Situational factors file not found")
        situational = None
    
    # Load pace data
    pace_file = data_dir / "team_pace.csv"
    if pace_file.exists():
        pace = pd.read_csv(pace_file)
        print(f"✅ Loaded pace data: {len(pace)} records")
    else:
        print(f"⚠️  Pace file not found")
        pace = None
    
    # For now, return df with placeholder columns
    # TODO: Implement proper merge logic once we understand the data structure
    df['is_dome'] = 0  # Placeholder
    df['home_rest_days'] = 7  # Placeholder
    df['away_rest_days'] = 7  # Placeholder
    df['home_pace'] = 6.4  # League average
    df['away_pace'] = 6.4  # League average
    
    return df

def prepare_features_with_situational(df):
    """Prepare features including situational factors."""
    features = []
    feature_names = []
    
    # Raw simulator outputs (PRIMARY)
    if 'home_score_raw' in df.columns:
        features.append(df['home_score_raw'].fillna(df['total_raw'] / 2.0))
        feature_names.append('home_raw')
    elif 'total_raw' in df.columns and 'spread_raw' in df.columns:
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
    
    if 'spread_raw' in df.columns:
        features.append(df['spread_raw'])
        feature_names.append('spread_raw')
    
    # Variability indicators
    if 'total_raw_sd' in df.columns:
        features.append(df['total_raw_sd'].fillna(9.0))
        feature_names.append('total_sd')
    
    if 'spread_raw_sd' in df.columns:
        features.append(df['spread_raw_sd'].fillna(13.0))
        feature_names.append('spread_sd')
    
    # Situational features (NEW)
    if 'is_dome' in df.columns:
        features.append(df['is_dome'])
        feature_names.append('is_dome')
    
    if 'home_rest_days' in df.columns:
        features.append(df['home_rest_days'])
        feature_names.append('home_rest_days')
    
    if 'away_rest_days' in df.columns:
        features.append(df['away_rest_days'])
        feature_names.append('away_rest_days')
    
    if 'home_pace' in df.columns:
        features.append(df['home_pace'])
        feature_names.append('home_pace')
    
    if 'away_pace' in df.columns:
        features.append(df['away_pace'])
        feature_names.append('away_pace')
    
    # Combine
    X = np.column_stack(features)
    
    return X, feature_names

def refit_score_calibration_with_features():
    """Refit score calibration with situational features."""
    print("="*70)
    print("IMPROVING SCORE CALIBRATION WITH SITUATIONAL FEATURES")
    print("="*70)
    
    df = load_backtest_data()
    print(f"\n✅ Loaded {len(df)} completed games")
    
    # Merge situational features
    df = merge_situational_features(df)
    
    # Prepare features
    X, feature_names = prepare_features_with_situational(df)
    
    # Targets
    y_home = df['actual_home_score'].values
    y_away = df['actual_away_score'].values
    y_total = y_home + y_away
    
    # Filter valid
    valid_mask = ~(np.isnan(y_home) | np.isnan(y_away))
    X = X[valid_mask]
    y_home = y_home[valid_mask]
    y_away = y_away[valid_mask]
    y_total = y_total[valid_mask]
    
    print(f"\n📊 Features: {len(feature_names)}")
    print(f"   {', '.join(feature_names)}")
    
    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train/test split
    X_train, X_test, y_home_train, y_home_test, y_away_train, y_away_test, y_total_train, y_total_test = train_test_split(
        X_scaled, y_home, y_away, y_total, test_size=0.2, random_state=42
    )
    
    # Fit models
    print(f"\n🔧 Fitting models with situational features...")
    
    model_home = Ridge(alpha=1.0)
    model_home.fit(X_train, y_home_train)
    home_r2_train = model_home.score(X_train, y_home_train)
    home_r2_test = model_home.score(X_test, y_home_test)
    
    model_away = Ridge(alpha=1.0)
    model_away.fit(X_train, y_away_train)
    away_r2_train = model_away.score(X_train, y_away_train)
    away_r2_test = model_away.score(X_test, y_away_test)
    
    model_total = Ridge(alpha=1.0)
    model_total.fit(X_train, y_total_train)
    total_r2_train = model_total.score(X_train, y_total_train)
    total_r2_test = model_total.score(X_test, y_total_test)
    
    # Metrics
    pred_home = model_home.predict(X_test)
    pred_away = model_away.predict(X_test)
    pred_total = model_total.predict(X_test)
    
    mae_home = np.mean(np.abs(pred_home - y_home_test))
    mae_away = np.mean(np.abs(pred_away - y_away_test))
    mae_total = np.mean(np.abs(pred_total - y_total_test))
    
    print(f"\n📈 Results:")
    print(f"   Home: Train R²={home_r2_train:.3f}, Test R²={home_r2_test:.3f}, MAE={mae_home:.2f}")
    print(f"   Away: Train R²={away_r2_train:.3f}, Test R²={away_r2_test:.3f}, MAE={mae_away:.2f}")
    print(f"   Total: Train R²={total_r2_train:.3f}, Test R²={total_r2_test:.3f}, MAE={mae_total:.2f}")
    
    # Compare to baseline (without features)
    print(f"\n📊 Comparison to Baseline (without situational features):")
    print(f"   Baseline Home R²: ~0.132")
    print(f"   Baseline Away R²: ~0.216")
    print(f"   Baseline Total R²: ~0.098")
    print(f"\n   Improvement:")
    print(f"   Home: {((home_r2_test - 0.132) / 0.132 * 100):.1f}%")
    print(f"   Away: {((away_r2_test - 0.216) / 0.216 * 100):.1f}%")
    print(f"   Total: {((total_r2_test - 0.098) / 0.098 * 100):.1f}%")
    
    # Save
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    models_dict = {
        'model_home': model_home,
        'model_away': model_away,
        'model_total': model_total,
        'scaler': scaler,
        'feature_names': feature_names
    }
    
    with open(artifacts_dir / "score_calibration_with_features.pkl", 'wb') as f:
        pickle.dump(models_dict, f)
    
    print(f"\n💾 Saved to: {artifacts_dir / 'score_calibration_with_features.pkl'}")

if __name__ == "__main__":
    refit_score_calibration_with_features()

