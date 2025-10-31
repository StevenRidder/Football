#!/usr/bin/env python3
"""
Clean XGBoost Model for NFL Game Predictions

Predicts:
- Will the underdog cover the spread?
- Will the game go over the total?

Returns predictions with confidence levels and explanations.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path
from typing import Dict, List, Tuple
import pickle

class NFLXGBoostModel:
    """XGBoost model for NFL game predictions."""
    
    def __init__(self):
        self.spread_model = None
        self.total_model = None
        self.feature_cols = []
        self.is_trained = False
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for model training/prediction."""
        
        # Core features from OL/DL stress
        feature_cols = [
            'ol_pass_stress_away', 'ol_pass_stress_home',
            'ol_chaos_index_away', 'ol_chaos_index_home',
            'stress_diff', 'stress_z_score',
            'away_ol_continuity_full', 'home_ol_continuity_full',
            'away_ol_continuity_count', 'home_ol_continuity_count',
            'away_center_missing', 'home_center_missing',
            'away_left_tackle_missing', 'home_left_tackle_missing',
        ]
        
        # Add market priors if available
        if 'spread_home' in df.columns:
            feature_cols.append('spread_home')
        if 'total' in df.columns:
            feature_cols.append('total')
            
        self.feature_cols = feature_cols
        
        # Fill missing values
        X = df[feature_cols].fillna(0)
        
        return X
    
    def train(self, df: pd.DataFrame):
        """Train the model on historical data."""
        
        print("🤖 Training XGBoost models...")
        
        # Prepare features
        X = self.prepare_features(df)
        
        # Target 1: Will underdog cover? (spread_result > 0)
        if 'actual_margin' in df.columns and 'spread_home' in df.columns:
            y_spread = (df['actual_margin'] > df['spread_home']).astype(int)
            
            self.spread_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                random_state=42,
                eval_metric='logloss'
            )
            self.spread_model.fit(X, y_spread)
            
            print(f"  ✅ Spread model trained on {len(df)} games")
        
        # Target 2: Will game go over? (actual_total > total)
        if 'actual_total' in df.columns and 'total' in df.columns:
            y_total = (df['actual_total'] > df['total']).astype(int)
            
            self.total_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                random_state=42,
                eval_metric='logloss'
            )
            self.total_model.fit(X, y_total)
            
            print(f"  ✅ Total model trained on {len(df)} games")
        
        self.is_trained = True
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Make predictions on new data."""
        
        if not self.is_trained:
            raise ValueError("Model not trained yet!")
        
        # Prepare features
        X = self.prepare_features(df)
        
        results = df.copy()
        
        # Predict spread
        if self.spread_model is not None:
            spread_proba = self.spread_model.predict_proba(X)[:, 1]
            results['spread_cover_prob'] = spread_proba
            results['spread_prediction'] = (spread_proba > 0.5).astype(int)
            
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
            results['total_prediction'] = (total_proba > 0.5).astype(int)
            
            # Confidence level
            results['total_confidence'] = np.abs(total_proba - 0.5) * 2
            results['total_confidence_level'] = pd.cut(
                results['total_confidence'],
                bins=[0, 0.2, 0.4, 1.0],
                labels=['Low', 'Medium', 'High']
            )
        
        return results
    
    def explain_prediction(self, row: pd.Series) -> Dict:
        """Explain why the model has high/low confidence."""
        
        explanation = {
            'spread': {
                'prediction': 'Underdog covers' if row.get('spread_prediction', 0) == 1 else 'Favorite covers',
                'confidence': row.get('spread_confidence_level', 'Unknown'),
                'probability': f"{row.get('spread_cover_prob', 0):.1%}",
                'reasons': []
            },
            'total': {
                'prediction': 'Over' if row.get('total_prediction', 0) == 1 else 'Under',
                'confidence': row.get('total_confidence_level', 'Unknown'),
                'probability': f"{row.get('total_over_prob', 0):.1%}",
                'reasons': []
            }
        }
        
        # Analyze key features for spread
        if row.get('stress_diff', 0) > 0.1:
            explanation['spread']['reasons'].append(
                f"Away team has OL advantage (stress diff: {row.get('stress_diff', 0):+.2f})"
            )
        elif row.get('stress_diff', 0) < -0.1:
            explanation['spread']['reasons'].append(
                f"Home team has OL advantage (stress diff: {row.get('stress_diff', 0):+.2f})"
            )
        
        if row.get('away_ol_continuity_full', 0) == 1:
            explanation['spread']['reasons'].append("Away OL fully intact")
        elif row.get('home_ol_continuity_full', 0) == 1:
            explanation['spread']['reasons'].append("Home OL fully intact")
        
        if row.get('away_center_missing', 0) == 1:
            explanation['spread']['reasons'].append("Away center missing (protection risk)")
        elif row.get('home_center_missing', 0) == 1:
            explanation['spread']['reasons'].append("Home center missing (protection risk)")
        
        # Analyze key features for total
        if row.get('ol_chaos_index_away', 0) > 0.5 or row.get('ol_chaos_index_home', 0) > 0.5:
            explanation['total']['reasons'].append("High OL chaos suggests lower scoring")
        
        if row.get('total', 0) > 50:
            explanation['total']['reasons'].append("High total suggests offensive game")
        elif row.get('total', 0) < 40:
            explanation['total']['reasons'].append("Low total suggests defensive game")
        
        return explanation
    
    def save(self, path: str):
        """Save model to disk."""
        with open(path, 'wb') as f:
            pickle.dump({
                'spread_model': self.spread_model,
                'total_model': self.total_model,
                'feature_cols': self.feature_cols,
                'is_trained': self.is_trained
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
        print(f"📂 Model loaded from {path}")


def train_model_on_historical_data():
    """Train model on 2022-2024 data."""
    
    print("=" * 70)
    print("🤖 TRAINING XGBOOST MODEL")
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
    merged['actual_margin'] = merged['away_score'] - merged['home_score']
    merged['actual_total'] = merged['away_score'] + merged['home_score']
    
    # Filter to completed games
    merged = merged[merged['away_score'].notna()].copy()
    
    print(f"\n📊 Training data: {len(merged)} games (2022-2024)")
    
    # Train model
    model = NFLXGBoostModel()
    model.train(merged)
    
    # Save model
    model.save('artifacts/xgboost_model.pkl')
    
    return model


if __name__ == "__main__":
    train_model_on_historical_data()

