
import pandas as pd
from sklearn.linear_model import Ridge

def fit_expected_points_model(history: pd.DataFrame):
    X_cols = ["away_OFF_EPA","home_DEF_EPA","away_OFF_SR","home_DEF_SR",
              "home_OFF_EPA","away_DEF_EPA","home_OFF_SR","away_DEF_SR",
              "away_PF_adj","home_PA","home_PF_adj","away_PA"]
    for c in X_cols + ["away_PF_adj","home_PF_adj"]:
        if c not in history.columns:
            raise RuntimeError(f"Model missing column: {c}")
    X = history[X_cols].fillna(0.0).values
    y_away = history["away_PF_adj"].values; y_home = history["home_PF_adj"].values
    away_model = Ridge(alpha=1.0).fit(X, y_away); home_model = Ridge(alpha=1.0).fit(X, y_home)
    return away_model, home_model, X_cols

def predict_expected_points(models, match_df: pd.DataFrame, home_field_pts: float, calibration_factor: float = 1.0):
    away_model, home_model, X_cols = models
    X = match_df[X_cols].fillna(0.0).values
    mu_away = away_model.predict(X) * calibration_factor
    mu_home = (home_model.predict(X) + home_field_pts) * calibration_factor
    return mu_away, mu_home
