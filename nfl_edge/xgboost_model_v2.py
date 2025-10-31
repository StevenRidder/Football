#!/usr/bin/env python3
"""
Clean XGBoost Model for NFL Game Predictions - V2

FIXES:
1. Correct ATS label: home_score + spread_home > away_score
2. Remove market lines from alpha model (no leakage)
3. Time-based splits (no future data in training)
4. Calibration with CalibratedClassifierCV
5. SHAP-based explanations (not heuristics)
6. Betting signal with -110 breakeven threshold
7. Proper push handling

Predicts:
- Will home team cover the spread?
- Will the game go over the total?
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pickle
from sklearn.metrics import log_loss, roc_auc_score, brier_score_loss, accuracy_score
from sklearn.calibration import CalibratedClassifierCV
import shap

class NFLXGBoostModel:
    """XGBoost model for NFL game predictions with proper evaluation."""
    
    def __init__(self):
        self.spread_model = None
        self.total_model = None
        self.feature_cols = []
        self.is_trained = False
        self.spread_explainer = None
        self.total_explainer = None
        
    def _ats_labels(self, df: pd.DataFrame) -> pd.Series:
        """
        Return 'home covers ATS' label, excluding pushes.
        
        Correct definition: home_score + spread_home > away_score
        - spread_home is negative when home is favored
        - Returns 1 if home covers, 0 if away covers, NA if push
        """
        if not {'away_score', 'home_score', 'spread_home'}.issubset(df.columns):
            raise ValueError("Missing columns for ATS labels")
        
        # Home covers if: home_score + spread_home > away_score
        home_covers = (df['home_score'] + df['spread_home'] > df['away_score']).astype('Int64')
        
        # Push = exactly equals
        push_mask = (df['home_score'] + df['spread_home'] == df['away_score'])
        home_covers[push_mask] = pd.NA
        
        return home_covers
    
    def _ou_labels(self, df: pd.DataFrame) -> pd.Series:
        """Return Over label, excluding pushes."""
        if not {'away_score', 'home_score', 'total'}.issubset(df.columns):
            raise ValueError("Missing columns for OU labels")
        
        total_actual = df['away_score'] + df['home_score']
        over = (total_actual > df['total']).astype('Int64')
        
        # Push = exactly equals
        push_mask = (total_actual == df['total'])
        over[push_mask] = pd.NA
        
        return over
    
    def prepare_features(self, df: pd.DataFrame, use_market: bool = False) -> pd.DataFrame:
        """
        Prepare features for model training/prediction.
        
        Args:
            use_market: If True, include spread/total (for capacity testing only)
                       If False, use only football features (for alpha model)
        """
        
        # Core football features (no market leakage)
        base_cols = [
            'ol_pass_stress_away', 'ol_pass_stress_home',
            'ol_chaos_index_away', 'ol_chaos_index_home',
            'stress_diff', 'stress_z_score',
            'away_ol_continuity_full', 'home_ol_continuity_full',
            'away_ol_continuity_count', 'home_ol_continuity_count',
            'away_center_missing', 'home_center_missing',
            'away_left_tackle_missing', 'home_left_tackle_missing',
        ]
        
        feature_cols = list(base_cols)
        
        if use_market:
            # Only for capacity model - DO NOT USE FOR BETTING
            if 'spread_home' in df.columns:
                feature_cols.append('spread_home')
            if 'total' in df.columns:
                feature_cols.append('total')
        
        # Store feature columns for inference
        if not self.feature_cols:
            self.feature_cols = feature_cols
        
        # Return only the features we need, filled with 0 for missing
        return df.reindex(columns=feature_cols).fillna(0)
    
    def train(self, df: pd.DataFrame, use_market: bool = False):
        """
        Train the model with proper time-based splits and evaluation.
        
        Args:
            df: DataFrame with historical games
            use_market: If True, include market lines (capacity test only)
        """
        
        print("=" * 70)
        print("🤖 TRAINING XGBOOST MODEL (ALPHA - NO MARKET LEAKAGE)")
        print("=" * 70)
        
        # Time-based splits (NO FUTURE DATA IN TRAINING)
        train_df = df[df['season'].isin([2022, 2023])].copy()
        val_df = df[(df['season'] == 2024) & (df['week'] <= 10)].copy()
        test_df = df[(df['season'] == 2024) & (df['week'] > 10)].copy()
        
        print(f"\n📊 Data splits:")
        print(f"  Train: {len(train_df)} games (2022-2023)")
        print(f"  Val:   {len(val_df)} games (2024 W1-10)")
        print(f"  Test:  {len(test_df)} games (2024 W11+)")
        
        # Prepare features
        X_tr = self.prepare_features(train_df, use_market=use_market)
        X_va = self.prepare_features(val_df, use_market=use_market)
        X_te = self.prepare_features(test_df, use_market=use_market)
        
        print(f"\n📊 Features: {len(self.feature_cols)}")
        if use_market:
            print("  ⚠️  WARNING: Using market lines (capacity test only)")
        else:
            print("  ✅ Alpha model: Football features only")
        
        # ---- SPREAD MODEL: Home covers ATS ----
        print(f"\n🏈 Training SPREAD model...")
        
        y_tr_s = self._ats_labels(train_df).dropna()
        X_tr_s = X_tr.loc[y_tr_s.index]
        
        y_va_s = self._ats_labels(val_df).dropna()
        X_va_s = X_va.loc[y_va_s.index]
        
        y_te_s = self._ats_labels(test_df).dropna()
        X_te_s = X_te.loc[y_te_s.index]
        
        print(f"  Train: {len(y_tr_s)} games (after removing pushes)")
        print(f"  Test:  {len(y_te_s)} games (after removing pushes)")
        
        # Base XGBoost with calibration
        base_spread = xgb.XGBClassifier(
            n_estimators=400,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            eval_metric='logloss'
        )
        
        self.spread_model = CalibratedClassifierCV(
            estimator=base_spread,
            method='isotonic',
            cv=3
        )
        
        self.spread_model.fit(X_tr_s, y_tr_s.astype(int))
        
        # Evaluate
        p_te_s = self.spread_model.predict_proba(X_te_s)[:, 1]
        y_pred_s = (p_te_s > 0.5).astype(int)
        
        print(f"\n  📊 Test metrics:")
        print(f"    Accuracy:  {accuracy_score(y_te_s, y_pred_s):.3f}")
        print(f"    Log Loss:  {log_loss(y_te_s, p_te_s):.3f}")
        print(f"    AUC:       {roc_auc_score(y_te_s, p_te_s):.3f}")
        print(f"    Brier:     {brier_score_loss(y_te_s, p_te_s):.3f}")
        
        # Create SHAP explainer for spread model
        # Use the base estimator from the calibrated model
        base_model = self.spread_model.calibrated_classifiers_[0].estimator
        self.spread_explainer = shap.TreeExplainer(base_model)
        
        # ---- TOTAL MODEL: Over ----
        print(f"\n🎯 Training TOTAL model...")
        
        y_tr_t = self._ou_labels(train_df).dropna()
        X_tr_t = X_tr.loc[y_tr_t.index]
        
        y_te_t = self._ou_labels(test_df).dropna()
        X_te_t = X_te.loc[y_te_t.index]
        
        print(f"  Train: {len(y_tr_t)} games (after removing pushes)")
        print(f"  Test:  {len(y_te_t)} games (after removing pushes)")
        
        base_total = xgb.XGBClassifier(
            n_estimators=400,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            eval_metric='logloss'
        )
        
        self.total_model = CalibratedClassifierCV(
            estimator=base_total,
            method='isotonic',
            cv=3
        )
        
        self.total_model.fit(X_tr_t, y_tr_t.astype(int))
        
        # Evaluate
        p_te_t = self.total_model.predict_proba(X_te_t)[:, 1]
        y_pred_t = (p_te_t > 0.5).astype(int)
        
        print(f"\n  📊 Test metrics:")
        print(f"    Accuracy:  {accuracy_score(y_te_t, y_pred_t):.3f}")
        print(f"    Log Loss:  {log_loss(y_te_t, p_te_t):.3f}")
        print(f"    AUC:       {roc_auc_score(y_te_t, p_te_t):.3f}")
        print(f"    Brier:     {brier_score_loss(y_te_t, p_te_t):.3f}")
        
        # Create SHAP explainer for total model
        base_model_t = self.total_model.calibrated_classifiers_[0].estimator
        self.total_explainer = shap.TreeExplainer(base_model_t)
        
        self.is_trained = True
        
        print(f"\n✅ Training complete!")
    
    def betting_signal(self, probs: pd.Series, side: str, edge_bp: float = 0.0) -> pd.DataFrame:
        """
        Convert calibrated probabilities into bets with -110 pricing.
        
        Args:
            probs: Predicted probabilities
            side: 'spread' or 'total'
            edge_bp: Extra edge in percentage points (e.g., 0.02 = 2%)
        
        Returns:
            DataFrame with bet recommendations and edge
        """
        
        # -110 odds: need to win 52.38% to break even
        breakeven = 110 / 210  # 0.5238095238
        upper = breakeven + edge_bp
        lower = 1 - upper
        
        rec = pd.DataFrame({'p': probs})
        
        if side == 'spread':
            rec['bet'] = np.where(
                rec['p'] >= upper, 'Home ATS',
                np.where(rec['p'] <= lower, 'Away ATS', 'Pass')
            )
            rec['edge'] = np.where(
                rec['bet'] == 'Home ATS', rec['p'] - breakeven,
                np.where(rec['bet'] == 'Away ATS', (1 - rec['p']) - breakeven, 0.0)
            )
        elif side == 'total':
            rec['bet'] = np.where(
                rec['p'] >= upper, 'Over',
                np.where(rec['p'] <= lower, 'Under', 'Pass')
            )
            rec['edge'] = np.where(
                rec['bet'] == 'Over', rec['p'] - breakeven,
                np.where(rec['bet'] == 'Under', (1 - rec['p']) - breakeven, 0.0)
            )
        else:
            raise ValueError("side must be 'spread' or 'total'")
        
        return rec
    
    def predict(self, df: pd.DataFrame, edge_threshold: float = 0.0) -> pd.DataFrame:
        """
        Make predictions on new data with betting signals.
        
        Args:
            df: DataFrame with game data
            edge_threshold: Minimum edge required to bet (in percentage points)
        """
        
        if not self.is_trained:
            raise ValueError("Model not trained yet!")
        
        # Prepare features (use same columns as training)
        X = df.reindex(columns=self.feature_cols).fillna(0)
        
        results = df.copy()
        
        # Predict spread
        if self.spread_model is not None:
            spread_proba = self.spread_model.predict_proba(X)[:, 1]
            results['spread_home_cover_prob'] = spread_proba
            
            # Betting signal
            spread_signals = self.betting_signal(spread_proba, 'spread', edge_threshold)
            results['spread_bet'] = spread_signals['bet']
            results['spread_edge'] = spread_signals['edge']
            
            # Confidence level
            results['spread_confidence'] = np.abs(spread_proba - 0.5) * 2
            results['spread_confidence_level'] = pd.cut(
                results['spread_confidence'],
                bins=[0, 0.2, 0.4, 1.0],
                labels=['Low', 'Medium', 'High']
            )
        
        # Predict total
        if self.total_model is not None:
            total_proba = self.total_model.predict_proba(X)[:, 1]
            results['total_over_prob'] = total_proba
            
            # Betting signal
            total_signals = self.betting_signal(total_proba, 'total', edge_threshold)
            results['total_bet'] = total_signals['bet']
            results['total_edge'] = total_signals['edge']
            
            # Confidence level
            results['total_confidence'] = np.abs(total_proba - 0.5) * 2
            results['total_confidence_level'] = pd.cut(
                results['total_confidence'],
                bins=[0, 0.2, 0.4, 1.0],
                labels=['Low', 'Medium', 'High']
            )
        
        return results
    
    def explain_prediction(self, row: pd.Series, X: pd.DataFrame, idx: int) -> Dict:
        """
        Explain prediction using SHAP values (not heuristics).
        
        Args:
            row: Game row with predictions
            X: Feature matrix
            idx: Index in X
        """
        
        explanation = {
            'spread': {
                'prediction': row.get('spread_bet', 'Unknown'),
                'confidence': row.get('spread_confidence_level', 'Unknown'),
                'probability': f"{row.get('spread_home_cover_prob', 0):.1%}",
                'edge': f"{row.get('spread_edge', 0):.2%}",
                'reasons': []
            },
            'total': {
                'prediction': row.get('total_bet', 'Unknown'),
                'confidence': row.get('total_confidence_level', 'Unknown'),
                'probability': f"{row.get('total_over_prob', 0):.1%}",
                'edge': f"{row.get('total_edge', 0):.2%}",
                'reasons': []
            }
        }
        
        # Get SHAP values for this prediction
        if self.spread_explainer is not None:
            shap_values = self.spread_explainer.shap_values(X.iloc[[idx]])
            
            # Get top 3 features by absolute SHAP value
            shap_abs = np.abs(shap_values[0])
            top_features = np.argsort(shap_abs)[-3:][::-1]
            
            for feat_idx in top_features:
                feat_name = self.feature_cols[feat_idx]
                feat_value = X.iloc[idx, feat_idx]
                shap_val = shap_values[0][feat_idx]
                
                # Convert to readable explanation
                direction = "increases" if shap_val > 0 else "decreases"
                explanation['spread']['reasons'].append(
                    f"{feat_name}={feat_value:.2f} {direction} home cover prob by {abs(shap_val):.3f}"
                )
        
        if self.total_explainer is not None:
            shap_values_t = self.total_explainer.shap_values(X.iloc[[idx]])
            
            shap_abs_t = np.abs(shap_values_t[0])
            top_features_t = np.argsort(shap_abs_t)[-3:][::-1]
            
            for feat_idx in top_features_t:
                feat_name = self.feature_cols[feat_idx]
                feat_value = X.iloc[idx, feat_idx]
                shap_val = shap_values_t[0][feat_idx]
                
                direction = "increases" if shap_val > 0 else "decreases"
                explanation['total']['reasons'].append(
                    f"{feat_name}={feat_value:.2f} {direction} over prob by {abs(shap_val):.3f}"
                )
        
        return explanation
    
    def save(self, path: str):
        """Save model to disk."""
        with open(path, 'wb') as f:
            pickle.dump({
                'spread_model': self.spread_model,
                'total_model': self.total_model,
                'feature_cols': self.feature_cols,
                'is_trained': self.is_trained,
                'spread_explainer': self.spread_explainer,
                'total_explainer': self.total_explainer
            }, f)
        print(f"💾 Model saved to {path}")
    
    def load(self, path: str):
        """Load model from disk."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.spread_model = data['spread_model']
            self.total_model = data['total_model']
            self.feature_cols = data['feature_cols']
            self.is_trained = data['is_trained']
            self.spread_explainer = data.get('spread_explainer')
            self.total_explainer = data.get('total_explainer')
        print(f"📂 Model loaded from {path}")


def train_model_on_historical_data():
    """Train alpha model on 2022-2024 data (NO MARKET LEAKAGE)."""
    
    print("=" * 70)
    print("🤖 TRAINING ALPHA MODEL (NO MARKET LEAKAGE)")
    print("=" * 70)
    
    # Load historical data
    stress = pd.read_csv('data/features/matchup_stress_2022_2025.csv')
    
    # Load schedules with results
    import nfl_data_py as nfl
    schedules = []
    for year in [2022, 2023, 2024]:
        sched = nfl.import_schedules([year])
        sched = sched[sched['game_type'] == 'REG'].copy()
        schedules.append(sched)
    
    all_schedules = pd.concat(schedules, ignore_index=True)
    
    # Normalize team names
    import sys
    sys.path.insert(0, '.')
    from nfl_edge.team_mapping import normalize_team
    all_schedules['away'] = all_schedules['away_team'].apply(normalize_team)
    all_schedules['home'] = all_schedules['home_team'].apply(normalize_team)
    
    # Merge
    merged = pd.merge(
        stress,
        all_schedules[['season', 'week', 'away', 'home', 'spread_line', 'total_line',
                       'away_score', 'home_score']],
        on=['season', 'week', 'away', 'home'],
        how='inner'
    )
    
    # Rename columns
    merged['spread_home'] = merged['spread_line']
    merged['total'] = merged['total_line']
    
    # Filter to completed games
    merged = merged[merged['away_score'].notna()].copy()
    
    print(f"\n📊 Training data: {len(merged)} games (2022-2024)")
    
    # Train ALPHA model (NO MARKET LINES)
    model = NFLXGBoostModel()
    model.train(merged, use_market=False)
    
    # Save model
    model.save('artifacts/xgboost_alpha_model.pkl')
    
    return model


if __name__ == "__main__":
    train_model_on_historical_data()

