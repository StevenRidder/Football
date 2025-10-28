"""
XGBoost Residual Model for NFL Betting

This module trains XGBoost models to predict residuals on top of market lines:
- Margin residual: actual_margin - (-closing_spread)
- Total residual: actual_total - closing_total

The goal is to find edges the market has not fully priced.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Optional
from sklearn.model_selection import TimeSeriesSplit
from sklearn.isotonic import IsotonicRegression

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not available. Install with: pip install xgboost")


class ResidualModel:
    """
    XGBoost model for predicting residuals on top of market lines.
    
    Features:
    - QB quality and availability
    - OL/WR protection and weapons
    - Defense shape (pressure, early-down SR, red-zone EPA)
    - Pace and script tendencies
    - Market priors (opening, closing, movement)
    - Weather and surface
    """
    
    def __init__(self):
        self.margin_model = None
        self.total_model = None
        self.margin_calibrator = None
        self.total_calibrator = None
        self.feature_cols = []
        
    def build_features(self, df: pd.DataFrame, market_lines: pd.DataFrame) -> pd.DataFrame:
        """
        Build features for residual prediction.
        
        Args:
            df: Team-level features (EPA, success rate, etc.)
            market_lines: Market lines (opening, closing, movement)
        
        Returns:
            DataFrame with features for XGBoost
        """
        # Merge team features with market lines
        features = market_lines.copy()
        
        # Add team features (EPA, success rate, etc.)
        # These come from nfl_edge/features.py
        for col in ['OFF_EPA', 'DEF_EPA', 'OFF_SR', 'DEF_SR', 'TO_DIFF']:
            if f'away_{col}' in df.columns:
                features[f'away_{col}'] = df[f'away_{col}']
            if f'home_{col}' in df.columns:
                features[f'home_{col}'] = df[f'home_{col}']
        
        # Market priors
        if 'opening_spread' in features.columns and 'closing_spread' in features.columns:
            features['spread_movement'] = features['closing_spread'] - features['opening_spread']
            features['spread_movement_abs'] = features['spread_movement'].abs()
        
        if 'opening_total' in features.columns and 'closing_total' in features.columns:
            features['total_movement'] = features['closing_total'] - features['opening_total']
            features['total_movement_abs'] = features['total_movement'].abs()
        
        # Matchup features (offense vs defense)
        if 'away_OFF_EPA' in features.columns and 'home_DEF_EPA' in features.columns:
            features['away_OFF_vs_home_DEF'] = features['away_OFF_EPA'] * features['home_DEF_EPA']
        if 'home_OFF_EPA' in features.columns and 'away_DEF_EPA' in features.columns:
            features['home_OFF_vs_away_DEF'] = features['home_OFF_EPA'] * features['away_DEF_EPA']
        
        # Net EPA advantage
        if 'away_OFF_EPA' in features.columns and 'away_DEF_EPA' in features.columns:
            features['away_net_epa'] = features['away_OFF_EPA'] - features['away_DEF_EPA']
        if 'home_OFF_EPA' in features.columns and 'home_DEF_EPA' in features.columns:
            features['home_net_epa'] = features['home_OFF_EPA'] - features['home_DEF_EPA']
        
        return features
    
    def train(self, 
              train_df: pd.DataFrame,
              target_margin: pd.Series,
              target_total: pd.Series,
              n_splits: int = 3) -> Dict[str, float]:
        """
        Train XGBoost models with time-series cross-validation.
        
        Args:
            train_df: Features
            target_margin: Margin residuals (actual - (-closing_spread))
            target_total: Total residuals (actual - closing_total)
            n_splits: Number of time-series CV splits
        
        Returns:
            Dictionary with CV scores
        """
        if not XGBOOST_AVAILABLE:
            raise RuntimeError("XGBoost not available")
        
        # Select feature columns (exclude targets, identifiers, and string columns)
        exclude_cols = ['week', 'away', 'home', 'actual_margin', 'actual_total', 
                       'margin_residual', 'total_residual', 'game_id']
        self.feature_cols = [c for c in train_df.columns 
                            if c not in exclude_cols 
                            and train_df[c].dtype in ['float64', 'int64', 'bool']]
        
        X = train_df[self.feature_cols].fillna(0)
        
        # Conservative XGBoost parameters (prevent overfitting)
        xgb_params = {
            'n_estimators': 100,
            'max_depth': 3,
            'learning_rate': 0.05,
            'subsample': 0.7,
            'colsample_bytree': 0.7,
            'reg_alpha': 1.0,  # L1 regularization
            'reg_lambda': 2.0,  # L2 regularization
            'min_child_weight': 5,  # Prevent overfitting to small samples
            'random_state': 42,
            'n_jobs': 2,
            'tree_method': 'auto'
        }
        
        # Train margin model
        print("\n🎯 Training Margin Residual Model...")
        self.margin_model = XGBRegressor(**xgb_params)
        self.margin_model.fit(X, target_margin, verbose=False)
        
        # Train total model
        print("🎯 Training Total Residual Model...")
        self.total_model = XGBRegressor(**xgb_params)
        self.total_model.fit(X, target_total, verbose=False)
        
        # Calibrate with isotonic regression
        print("📊 Calibrating predictions...")
        margin_preds = self.margin_model.predict(X)
        total_preds = self.total_model.predict(X)
        
        self.margin_calibrator = IsotonicRegression(out_of_bounds='clip')
        self.margin_calibrator.fit(margin_preds, target_margin)
        
        self.total_calibrator = IsotonicRegression(out_of_bounds='clip')
        self.total_calibrator.fit(total_preds, target_total)
        
        # Compute training MAE
        margin_mae = np.mean(np.abs(margin_preds - target_margin))
        total_mae = np.mean(np.abs(total_preds - target_total))
        
        print(f"✅ Margin MAE: {margin_mae:.2f} points")
        print(f"✅ Total MAE: {total_mae:.2f} points")
        
        return {
            'margin_mae': margin_mae,
            'total_mae': total_mae
        }
    
    def predict(self, test_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict margin and total residuals.
        
        Args:
            test_df: Features for prediction
        
        Returns:
            (margin_residuals, total_residuals)
        """
        if self.margin_model is None or self.total_model is None:
            raise RuntimeError("Models not trained. Call train() first.")
        
        X = test_df[self.feature_cols].fillna(0)
        
        # Raw predictions
        margin_preds = self.margin_model.predict(X)
        total_preds = self.total_model.predict(X)
        
        # Calibrate
        if self.margin_calibrator is not None:
            margin_preds = self.margin_calibrator.predict(margin_preds)
        if self.total_calibrator is not None:
            total_preds = self.total_calibrator.predict(total_preds)
        
        return margin_preds, total_preds
    
    def predict_with_market(self, 
                           test_df: pd.DataFrame,
                           closing_spread: pd.Series,
                           closing_total: pd.Series) -> pd.DataFrame:
        """
        Predict final margin and total by adding residuals to market lines.
        
        Args:
            test_df: Features
            closing_spread: Closing spread (home-)
            closing_total: Closing total
        
        Returns:
            DataFrame with predictions
        """
        margin_residuals, total_residuals = self.predict(test_df)
        
        results = pd.DataFrame({
            'predicted_margin': -closing_spread + margin_residuals,  # Convert spread to margin
            'predicted_total': closing_total + total_residuals,
            'margin_residual': margin_residuals,
            'total_residual': total_residuals,
            'closing_spread': closing_spread,
            'closing_total': closing_total
        })
        
        return results
    
    def get_feature_importance(self, top_n: int = 15) -> pd.DataFrame:
        """
        Get feature importance from trained models.
        
        Args:
            top_n: Number of top features to return
        
        Returns:
            DataFrame with feature importances
        """
        if self.margin_model is None or self.total_model is None:
            raise RuntimeError("Models not trained")
        
        margin_importance = pd.DataFrame({
            'feature': self.feature_cols,
            'margin_importance': self.margin_model.feature_importances_
        }).sort_values('margin_importance', ascending=False).head(top_n)
        
        total_importance = pd.DataFrame({
            'feature': self.feature_cols,
            'total_importance': self.total_model.feature_importances_
        }).sort_values('total_importance', ascending=False).head(top_n)
        
        # Merge
        importance = margin_importance.merge(total_importance, on='feature', how='outer')
        importance = importance.fillna(0)
        importance['avg_importance'] = (importance['margin_importance'] + importance['total_importance']) / 2
        importance = importance.sort_values('avg_importance', ascending=False)
        
        return importance

