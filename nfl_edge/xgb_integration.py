"""
XGBoost Model Integration

This module integrates the XGBoost residual model into the main prediction pipeline.
It runs alongside the current model and provides additional predictions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

from nfl_edge.xgb_residuals import ResidualModel
from nfl_edge.features import build_features
from nfl_edge.data_ingest import fetch_teamweeks_live


def add_xgb_predictions(df: pd.DataFrame, season: int = 2025) -> pd.DataFrame:
    """
    Add XGBoost residual model predictions to the predictions DataFrame.
    
    Args:
        df: DataFrame with current model predictions (from run_week)
        season: NFL season
    
    Returns:
        DataFrame with additional XGBoost columns:
        - xgb_margin: XGBoost predicted margin (home - away)
        - xgb_total: XGBoost predicted total
        - xgb_spread_rec: XGBoost spread recommendation
        - xgb_total_rec: XGBoost total recommendation
        - xgb_confidence: XGBoost confidence level
    """
    print("\n🤖 Running XGBoost Residual Model...")
    
    # Load trained model (if exists)
    model_path = Path('/Users/steveridder/Git/Football/artifacts/xgb_model.pkl')
    
    if not model_path.exists():
        print("⚠️  XGBoost model not trained yet. Training now...")
        model = train_xgb_model(season)
    else:
        print("✅ Loading trained XGBoost model...")
        import pickle
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
    
    # Prepare features
    try:
        team_stats = fetch_teamweeks_live(season)
        if team_stats.empty:
            print("⚠️  No team stats available, skipping XGBoost predictions")
            return df
        
        features_df = build_features(team_stats)
        
        # Build XGBoost features for each matchup
        xgb_features = []
        
        for _, row in df.iterrows():
            away = row['away']
            home = row['home']
            
            # Get team features
            away_features = features_df[features_df['team'] == away]
            home_features = features_df[features_df['team'] == home]
            
            if len(away_features) == 0 or len(home_features) == 0:
                xgb_features.append(None)
                continue
            
            # Build feature dict
            feature_dict = {
                'opening_spread': row.get('Spread used (home-)', 0),
                'opening_total': row.get('Total used', 0),
                'closing_spread': row.get('Spread used (home-)', 0),  # Use opening as closing for now
                'closing_total': row.get('Total used', 0),
                'spread_movement': 0.0,
                'total_movement': 0.0,
                'spread_movement_abs': 0.0,
                'total_movement_abs': 0.0
            }
            
            # Add team features
            for col in ['OFF_EPA', 'DEF_EPA', 'OFF_SR', 'DEF_SR', 'TO_DIFF']:
                if col in features_df.columns:
                    feature_dict[f'away_{col}'] = away_features[col].iloc[0] if len(away_features) > 0 else 0
                    feature_dict[f'home_{col}'] = home_features[col].iloc[0] if len(home_features) > 0 else 0
            
            # Add matchup features
            if 'away_OFF_EPA' in feature_dict and 'home_DEF_EPA' in feature_dict:
                feature_dict['away_OFF_vs_home_DEF'] = feature_dict['away_OFF_EPA'] * feature_dict['home_DEF_EPA']
            if 'home_OFF_EPA' in feature_dict and 'away_DEF_EPA' in feature_dict:
                feature_dict['home_OFF_vs_away_DEF'] = feature_dict['home_OFF_EPA'] * feature_dict['away_DEF_EPA']
            
            # Add net EPA
            if 'away_OFF_EPA' in feature_dict and 'away_DEF_EPA' in feature_dict:
                feature_dict['away_net_epa'] = feature_dict['away_OFF_EPA'] - feature_dict['away_DEF_EPA']
            if 'home_OFF_EPA' in feature_dict and 'home_DEF_EPA' in feature_dict:
                feature_dict['home_net_epa'] = feature_dict['home_OFF_EPA'] - feature_dict['home_DEF_EPA']
            
            xgb_features.append(feature_dict)
        
        # Convert to DataFrame
        xgb_df = pd.DataFrame(xgb_features)
        
        if xgb_df.empty or xgb_df.isnull().all().all():
            print("⚠️  Could not build XGBoost features, skipping")
            return df
        
        # Build features using model's method
        xgb_input = model.build_features(xgb_df, xgb_df)
        
        # Predict
        margin_preds, total_preds = model.predict(xgb_input)
        
        # Add to DataFrame
        df['xgb_margin'] = margin_preds
        df['xgb_total'] = total_preds
        
        # Generate recommendations
        df['xgb_spread_rec'] = df.apply(lambda row: generate_spread_rec(row, 'xgb'), axis=1)
        df['xgb_total_rec'] = df.apply(lambda row: generate_total_rec(row, 'xgb'), axis=1)
        df['xgb_confidence'] = df.apply(lambda row: calculate_xgb_confidence(row), axis=1)
        
        print(f"✅ Added XGBoost predictions for {len(df)} games")
        
    except Exception as e:
        print(f"❌ Error generating XGBoost predictions: {e}")
        import traceback
        traceback.print_exc()
    
    return df


def train_xgb_model(season: int = 2025) -> ResidualModel:
    """
    Train XGBoost model on historical data.
    
    This is a simplified training function for production use.
    For full backtesting, use train_and_backtest_residual.py
    """
    print("\n🎯 Training XGBoost model on historical data...")
    
    # This would load historical data and train
    # For now, return a new model (will be trained on first use)
    model = ResidualModel()
    
    print("⚠️  Model training not implemented in production yet")
    print("   Run train_and_backtest_residual.py to train and save model")
    
    return model


def generate_spread_rec(row: pd.Series, model_prefix: str = 'xgb') -> str:
    """Generate spread recommendation from XGBoost prediction."""
    try:
        predicted_margin = row.get(f'{model_prefix}_margin', 0)
        market_spread = row.get('Spread used (home-)', 0)
        
        # Edge is difference between predicted and market
        edge = predicted_margin - (-market_spread)
        
        if abs(edge) < 1.0:
            return "SKIP"
        elif edge > 0:
            return f"BET HOME {market_spread:+.1f} (Edge: {edge:+.1f})"
        else:
            return f"BET AWAY {-market_spread:+.1f} (Edge: {edge:+.1f})"
    except:
        return "SKIP"


def generate_total_rec(row: pd.Series, model_prefix: str = 'xgb') -> str:
    """Generate total recommendation from XGBoost prediction."""
    try:
        predicted_total = row.get(f'{model_prefix}_total', 0)
        market_total = row.get('Total used', 0)
        
        # Edge is difference
        edge = predicted_total - market_total
        
        if abs(edge) < 1.0:
            return "SKIP"
        elif edge > 0:
            return f"BET OVER {market_total:.1f} (Edge: {edge:+.1f})"
        else:
            return f"BET UNDER {market_total:.1f} (Edge: {edge:+.1f})"
    except:
        return "SKIP"


def calculate_xgb_confidence(row: pd.Series) -> str:
    """Calculate confidence level for XGBoost prediction."""
    try:
        margin_edge = abs(row.get('xgb_margin', 0) - (-row.get('Spread used (home-)', 0)))
        total_edge = abs(row.get('xgb_total', 0) - row.get('Total used', 0))
        
        max_edge = max(margin_edge, total_edge)
        
        if max_edge > 3.0:
            return "HIGH"
        elif max_edge > 1.5:
            return "MEDIUM"
        else:
            return "LOW"
    except:
        return "LOW"

