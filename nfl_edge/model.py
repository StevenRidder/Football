
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except (ImportError, Exception) as e:
    XGBOOST_AVAILABLE = False
    if "XGBoostError" in str(type(e).__name__):
        print("⚠️  XGBoost library error (missing OpenMP). Using Ridge regression instead.")
    else:
        print("⚠️  XGBoost not available. Using Ridge regression instead.")

def fit_expected_points_model(history: pd.DataFrame, use_xgboost: bool = True):
    # Core EPA and success rate features
    X_cols = ["away_OFF_EPA","home_DEF_EPA","away_OFF_SR","home_DEF_SR",
              "home_OFF_EPA","away_DEF_EPA","home_OFF_SR","away_DEF_SR",
              "away_PF_adj","home_PA","home_PF_adj","away_PA"]
    
    # Add situational features if available
    situational_cols = ["away_travel_miles", "timezone_diff", "is_divisional", 
                       "is_conference", "away_injury", "home_injury"]
    for col in situational_cols:
        if col in history.columns:
            X_cols.append(col)
    
    # Add interaction features for better predictions
    interaction_features = []
    if "away_OFF_EPA" in history.columns and "home_DEF_EPA" in history.columns:
        history["away_OFF_vs_home_DEF"] = history["away_OFF_EPA"] * history["home_DEF_EPA"]
        interaction_features.append("away_OFF_vs_home_DEF")
    
    if "home_OFF_EPA" in history.columns and "away_DEF_EPA" in history.columns:
        history["home_OFF_vs_away_DEF"] = history["home_OFF_EPA"] * history["away_DEF_EPA"]
        interaction_features.append("home_OFF_vs_away_DEF")
    
    if "is_divisional" in history.columns and "away_OFF_EPA" in history.columns:
        history["divisional_chaos"] = history["is_divisional"] * history["away_OFF_EPA"]
        interaction_features.append("divisional_chaos")
    
    X_cols.extend(interaction_features)
    
    # Verify required columns exist
    for c in ["away_PF_adj","home_PF_adj"]:
        if c not in history.columns:
            raise RuntimeError(f"Model missing column: {c}")
    
    # Build feature matrix (fill missing with 0)
    X = history[X_cols].fillna(0.0).values
    y_away = history["away_PF_adj"].values
    y_home = history["home_PF_adj"].values
    
    # Choose model type
    if use_xgboost and XGBOOST_AVAILABLE:
        print("🚀 Training lightweight XGBoost models...")
        # Lightweight XGBoost parameters for older laptops
        away_model = XGBRegressor(
            n_estimators=50,            # Fewer trees = faster (was 150)
            max_depth=3,                # Shallower trees = faster (was 5)
            learning_rate=0.1,          # Higher LR with fewer trees (was 0.05)
            subsample=0.8,              # Use 80% of data per tree
            colsample_bytree=0.8,       # Use 80% of features per tree
            reg_alpha=0.3,              # Light L1 regularization
            reg_lambda=0.5,             # Light L2 regularization
            random_state=42,
            n_jobs=2,                   # Use only 2 cores (was -1)
            tree_method='auto'          # Auto-select fastest method
        ).fit(X, y_away, verbose=False)
        
        home_model = XGBRegressor(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.3,
            reg_lambda=0.5,
            random_state=42,
            n_jobs=2,
            tree_method='auto'
        ).fit(X, y_home, verbose=False)
        
        print(f"✅ Lightweight XGBoost models trained with {len(X_cols)} features")
    else:
        if use_xgboost:
            print("⚠️  XGBoost requested but not available, falling back to Ridge")
        print("📊 Training Ridge regression models...")
        away_model = Ridge(alpha=1.0).fit(X, y_away)
        home_model = Ridge(alpha=1.0).fit(X, y_home)
        print(f"✅ Ridge models trained with {len(X_cols)} features")
    
    return away_model, home_model, X_cols

def predict_expected_points(models, match_df: pd.DataFrame, home_field_pts: float, calibration_factor: float = 1.0):
    away_model, home_model, X_cols = models
    
    # Create interaction features if they're in X_cols
    if "away_OFF_vs_home_DEF" in X_cols:
        match_df["away_OFF_vs_home_DEF"] = match_df["away_OFF_EPA"] * match_df["home_DEF_EPA"]
    
    if "home_OFF_vs_away_DEF" in X_cols:
        match_df["home_OFF_vs_away_DEF"] = match_df["home_OFF_EPA"] * match_df["away_DEF_EPA"]
    
    if "divisional_chaos" in X_cols and "is_divisional" in match_df.columns:
        match_df["divisional_chaos"] = match_df["is_divisional"] * match_df["away_OFF_EPA"]
    
    X = match_df[X_cols].fillna(0.0).values
    mu_away = away_model.predict(X) * calibration_factor
    mu_home = (home_model.predict(X) + home_field_pts) * calibration_factor
    
    # Removed blowout reduction - it made predictions worse
    # Model actually predicts blowout winners well (87.5% accuracy)
    
    return mu_away, mu_home
