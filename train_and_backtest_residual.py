"""
Train and Backtest XGBoost Residual Model

This script:
1. Loads historical game results and market lines
2. Trains XGBoost models to predict residuals
3. Backtests with walk-forward validation
4. Compares CLV against current model
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from nfl_edge.xgb_residuals import ResidualModel
from nfl_edge.qb_features import add_qb_features
from nfl_edge.features import build_features
from nfl_edge.data_ingest import fetch_teamweeks_live
from nfl_edge.team_mapping import normalize_team
from nfl_edge.epa_interactions import add_epa_interaction_features
from nfl_edge.weather_features import add_weather_features
from nfl_edge.travel_rest_features import add_travel_rest_features


# ============================================================================
# CONFIGURATION
# ============================================================================

TRAIN_WEEKS = list(range(1, 5))  # Weeks 1-4 for training
TEST_WEEKS = list(range(5, 8))   # Weeks 5-7 for testing
CURRENT_SEASON = 2025
ARTIFACTS_DIR = Path('/Users/steveridder/Git/Football/artifacts')


# ============================================================================
# DATA LOADING
# ============================================================================

def load_historical_results() -> pd.DataFrame:
    """Load actual game results from ESPN."""
    import requests
    
    print("\n📥 Loading historical game results...")
    
    all_results = []
    
    for week in range(1, 8):
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={CURRENT_SEASON}&seasontype=2&week={week}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            for event in data.get('events', []):
                if event['status']['type']['completed']:
                    comps = event['competitions'][0]
                    away_team = comps['competitors'][1]
                    home_team = comps['competitors'][0]
                    
                    # Normalize team abbreviations
                    away_abbr = normalize_team(away_team['team']['abbreviation'], 'espn')
                    home_abbr = normalize_team(home_team['team']['abbreviation'], 'espn')
                    
                    all_results.append({
                        'week': week,
                        'away': away_abbr,
                        'home': home_abbr,
                        'away_score': int(away_team['score']),
                        'home_score': int(home_team['score']),
                        'actual_margin': int(home_team['score']) - int(away_team['score']),
                        'actual_total': int(away_team['score']) + int(home_team['score'])
                    })
        except Exception as e:
            print(f"⚠️  Week {week}: {e}")
    
    df = pd.DataFrame(all_results)
    print(f"✅ Loaded {len(df)} games")
    return df


def load_market_lines() -> pd.DataFrame:
    """Load opening and closing lines."""
    print("\n📥 Loading market lines...")
    
    # Load opening lines
    opening_file = ARTIFACTS_DIR / 'opening_closing_lines_weeks_1-7_20251027.csv'
    
    if not opening_file.exists():
        raise FileNotFoundError(f"Opening lines file not found: {opening_file}")
    
    opening_df = pd.read_csv(opening_file)
    opening_df['away'] = opening_df['away'].apply(lambda x: 'LAR' if x == 'LA' else x)
    opening_df['home'] = opening_df['home'].apply(lambda x: 'LAR' if x == 'LA' else x)
    opening_df = opening_df[opening_df['line_type'] == 'opening']
    
    print(f"✅ Loaded {len(opening_df)} opening line snapshots")
    
    # Load REAL closing lines
    closing_file = ARTIFACTS_DIR / 'real_closing_lines_weeks_1-7_20251027_192725.csv'
    
    if not closing_file.exists():
        print(f"⚠️  Real closing lines not found, using opening as closing")
        closing_df = opening_df.copy()
    else:
        closing_df = pd.read_csv(closing_file)
        print(f"✅ Loaded {len(closing_df)} REAL closing lines")
    
    # Merge opening and closing
    games = []
    
    for _, closing_row in closing_df.iterrows():
        week = closing_row['week']
        away = closing_row['away']
        home = closing_row['home']
        
        # Find matching opening line
        opening_match = opening_df[
            (opening_df['week'] == week) &
            (opening_df['away'] == away) &
            (opening_df['home'] == home)
        ]
        
        if len(opening_match) > 0:
            opening_spread = opening_match['spread'].iloc[0]
            opening_total = opening_match['total'].iloc[0]
        else:
            # No opening line, use closing as opening
            opening_spread = closing_row['closing_spread']
            opening_total = closing_row['closing_total']
        
        games.append({
            'week': week,
            'away': away,
            'home': home,
            'opening_spread': opening_spread,
            'opening_total': opening_total,
            'closing_spread': closing_row['closing_spread'],
            'closing_total': closing_row['closing_total'],
            'spread_movement': closing_row['closing_spread'] - opening_spread,
            'total_movement': closing_row['closing_total'] - opening_total
        })
    
    market_df = pd.DataFrame(games)
    print(f"✅ Parsed {len(market_df)} games with REAL opening and closing lines")
    print(f"   Avg spread movement: {market_df['spread_movement'].abs().mean():.2f} pts")
    print(f"   Avg total movement: {market_df['total_movement'].abs().mean():.2f} pts")
    return market_df


def load_team_features(weeks: list) -> pd.DataFrame:
    """Load team-level features (EPA, success rate, etc.)."""
    print("\n📥 Loading team features...")
    
    # Fetch current season stats
    team_stats = fetch_teamweeks_live(CURRENT_SEASON)
    
    if team_stats.empty:
        print("⚠️  No team stats available, using defaults")
        return pd.DataFrame()
    
    # Build features using existing pipeline
    features_df = build_features(team_stats)
    
    print(f"✅ Loaded features for {len(features_df)} teams")
    return features_df


# ============================================================================
# TRAINING
# ============================================================================

def prepare_training_data(results: pd.DataFrame, 
                         market_lines: pd.DataFrame,
                         team_features: pd.DataFrame) -> pd.DataFrame:
    """
    Merge results, market lines, and team features.
    Calculate residuals.
    """
    print("\n🔧 Preparing training data...")
    
    # Merge results with market lines
    df = results.merge(market_lines, on=['week', 'away', 'home'], how='inner')
    
    # Calculate residuals
    df['margin_residual'] = df['actual_margin'] - (-df['closing_spread'])
    df['total_residual'] = df['actual_total'] - df['closing_total']
    
    # Add team features for away and home
    if not team_features.empty:
        # Create matchup features
        for col in ['OFF_EPA', 'DEF_EPA', 'OFF_SR', 'DEF_SR', 'TO_DIFF']:
            if col in team_features.columns:
                # Away team features
                away_map = team_features.set_index('team')[col].to_dict()
                df[f'away_{col}'] = df['away'].map(away_map)
                
                # Home team features
                home_map = team_features.set_index('team')[col].to_dict()
                df[f'home_{col}'] = df['home'].map(home_map)
    
    # Add QB features (DISABLED - causes data loss due to merge issues)
    # df = add_qb_features(df, season=CURRENT_SEASON)
    
    # Add enhanced EPA interaction features
    print("\n🔧 Adding enhanced EPA interaction features...")
    weeks_to_include = df['week'].unique().tolist()
    df = add_epa_interaction_features(df, season=CURRENT_SEASON, weeks_to_fetch=weeks_to_include)
    
    # Add travel and rest features
    print("\n🔧 Adding travel and rest features...")
    df = add_travel_rest_features(df)
    
    # Add weather features
    print("\n🔧 Adding weather features...")
    # Note: Weather requires game dates, which we need to estimate or fetch
    # For now, we'll add weather for each week
    df = add_weather_features(df, season=CURRENT_SEASON)
    
    print(f"✅ Prepared {len(df)} games for training")
    print(f"   Features: {len([c for c in df.columns if c not in ['week', 'away', 'home', 'actual_margin', 'actual_total', 'margin_residual', 'total_residual']])}")
    print(f"   Games by week: {df.groupby('week').size().to_dict()}")
    
    return df


def train_residual_model(train_df: pd.DataFrame) -> ResidualModel:
    """Train XGBoost residual model."""
    print("\n" + "="*80)
    print("TRAINING RESIDUAL MODEL")
    print("="*80)
    
    model = ResidualModel()
    
    # Build features
    features_df = model.build_features(train_df, train_df)
    
    # Train
    scores = model.train(
        features_df,
        train_df['margin_residual'],
        train_df['total_residual'],
        n_splits=3
    )
    
    print("\n📊 Feature Importance (Top 15):")
    importance = model.get_feature_importance(top_n=15)
    for _, row in importance.iterrows():
        print(f"  {row['feature']:30s} | Margin: {row['margin_importance']:.3f} | Total: {row['total_importance']:.3f}")
    
    return model


# ============================================================================
# BACKTESTING
# ============================================================================

def backtest_residual_model(model: ResidualModel, 
                            test_df: pd.DataFrame,
                            confidence_threshold: float = 0.6,
                            clv_threshold: float = 1.0) -> pd.DataFrame:
    """
    Backtest residual model on test weeks with TRUE CLV calculation.
    
    Args:
        model: Trained residual model
        test_df: Test data with actual results and REAL closing lines
        confidence_threshold: Minimum confidence to place bet (0-1)
        clv_threshold: Minimum projected CLV to place bet (points)
    
    Returns:
        DataFrame with bet results including CLV
    """
    print("\n" + "="*80)
    print("BACKTESTING RESIDUAL MODEL (WITH REAL CLV)")
    print("="*80)
    
    # Build features
    features_df = model.build_features(test_df, test_df)
    
    # Predict
    predictions = model.predict_with_market(
        features_df,
        test_df['closing_spread'],
        test_df['closing_total']
    )
    
    # Add predictions to test_df
    test_df = test_df.copy()
    test_df['predicted_margin'] = predictions['predicted_margin']
    test_df['predicted_total'] = predictions['predicted_total']
    test_df['margin_residual_pred'] = predictions['margin_residual']
    test_df['total_residual_pred'] = predictions['total_residual']
    
    # Evaluate bets
    results = []
    
    for idx, row in test_df.iterrows():
        # Spread bet evaluation
        spread_edge = abs(row['margin_residual_pred'])
        if spread_edge >= clv_threshold:
            # Determine side
            if row['predicted_margin'] > -row['closing_spread']:
                # Bet home
                side = 'home'
                line = row['closing_spread']
                actual_diff = row['actual_margin'] - line
            else:
                # Bet away
                side = 'away'
                line = -row['closing_spread']
                actual_diff = -row['actual_margin'] - line
            
            # Grade
            if abs(actual_diff) < 1e-9:
                result = 'PUSH'
                profit = 0
            elif actual_diff > 0:
                result = 'WIN'
                profit = 100 * 0.909  # Win $100 for $110 bet
            else:
                result = 'LOSS'
                profit = -110
            
            # Calculate CLV (bet at opening, compare to closing)
            opening_line = row['opening_spread'] if side == 'home' else -row['opening_spread']
            closing_line = row['closing_spread'] if side == 'home' else -row['closing_spread']
            clv = closing_line - opening_line  # Positive CLV = line moved in our favor
            
            results.append({
                'week': row['week'],
                'game': f"{row['away']}@{row['home']}",
                'bet_type': 'spread',
                'side': side,
                'line': line,
                'edge': spread_edge,
                'result': result,
                'profit': profit,
                'actual_margin': row['actual_margin'],
                'predicted_margin': row['predicted_margin'],
                'opening_line': opening_line,
                'closing_line': closing_line,
                'clv': clv
            })
        
        # Total bet evaluation
        total_edge = abs(row['total_residual_pred'])
        if total_edge >= clv_threshold:
            # Determine side
            if row['predicted_total'] > row['closing_total']:
                side = 'over'
                actual_diff = row['actual_total'] - row['closing_total']
            else:
                side = 'under'
                actual_diff = row['closing_total'] - row['actual_total']
            
            # Grade
            if abs(actual_diff) < 1e-9:
                result = 'PUSH'
                profit = 0
            elif actual_diff > 0:
                result = 'WIN'
                profit = 100 * 0.909
            else:
                result = 'LOSS'
                profit = -110
            
            # Calculate CLV for totals
            opening_total = row['opening_total']
            closing_total = row['closing_total']
            clv = abs(closing_total - opening_total)  # Line movement magnitude
            # Adjust sign based on direction
            if side == 'over':
                clv = closing_total - opening_total  # Higher total = better for over
            else:
                clv = opening_total - closing_total  # Lower total = better for under
            
            results.append({
                'week': row['week'],
                'game': f"{row['away']}@{row['home']}",
                'bet_type': 'total',
                'side': side,
                'line': row['closing_total'],
                'edge': total_edge,
                'result': result,
                'profit': profit,
                'actual_total': row['actual_total'],
                'predicted_total': row['predicted_total'],
                'opening_line': opening_total,
                'closing_line': closing_total,
                'clv': clv
            })
    
    return pd.DataFrame(results)


def print_backtest_summary(results: pd.DataFrame):
    """Print summary of backtest results."""
    print("\n" + "="*80)
    print("BACKTEST RESULTS SUMMARY")
    print("="*80)
    
    if len(results) == 0:
        print("\n❌ No bets placed (edge thresholds not met)")
        return
    
    total_bets = len(results)
    wins = len(results[results['result'] == 'WIN'])
    pushes = len(results[results['result'] == 'PUSH'])
    losses = len(results[results['result'] == 'LOSS'])
    
    total_profit = results['profit'].sum()
    total_risked = total_bets * 110
    roi = (total_profit / total_risked) * 100
    
    print(f"\nTotal Bets: {total_bets}")
    print(f"Wins: {wins}")
    print(f"Pushes: {pushes}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {(wins/(total_bets-pushes)*100):.1f}%")
    print(f"\nTotal Risked: ${total_risked:.2f}")
    print(f"Total Profit: ${total_profit:.2f}")
    print(f"ROI: {roi:.1f}%")
    
    # CLV Analysis
    if 'clv' in results.columns:
        avg_clv = results['clv'].mean()
        positive_clv = (results['clv'] > 0).sum()
        clv_pct = (positive_clv / total_bets) * 100
        
        print(f"\nCLV (Closing Line Value):")
        print(f"  Average CLV: {avg_clv:+.2f} points")
        print(f"  Positive CLV: {clv_pct:.1f}% of bets ({positive_clv}/{total_bets})")
        
        if clv_pct > 50:
            print(f"  ✅ POSITIVE CLV - Model beats market closing price")
        elif clv_pct > 45:
            print(f"  ⚠️  MARGINAL CLV - Weak edge")
        else:
            print(f"  ❌ NEGATIVE CLV - No sustainable edge")
    
    # By week
    print("\n" + "-"*80)
    print("BY WEEK:")
    for week in sorted(results['week'].unique()):
        week_results = results[results['week'] == week]
        week_wins = len(week_results[week_results['result'] == 'WIN'])
        week_profit = week_results['profit'].sum()
        week_roi = (week_profit / (len(week_results) * 110)) * 100
        print(f"  Week {week}: {week_wins}/{len(week_results)} wins, Profit: ${week_profit:.2f}, ROI: {week_roi:.1f}%")
    
    # By bet type
    print("\n" + "-"*80)
    print("BY BET TYPE:")
    for bet_type in results['bet_type'].unique():
        type_results = results[results['bet_type'] == bet_type]
        type_wins = len(type_results[type_results['result'] == 'WIN'])
        type_profit = type_results['profit'].sum()
        type_roi = (type_profit / (len(type_results) * 110)) * 100
        print(f"  {bet_type.upper()}: {type_wins}/{len(type_results)} wins, Profit: ${type_profit:.2f}, ROI: {type_roi:.1f}%")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution."""
    print("\n" + "="*80)
    print("XGBOOST RESIDUAL MODEL - TRAIN & BACKTEST")
    print("="*80)
    
    # Load data
    results = load_historical_results()
    market_lines = load_market_lines()
    team_features = load_team_features(list(range(1, 8)))
    
    # Prepare training data
    full_df = prepare_training_data(results, market_lines, team_features)
    
    # Split train/test
    train_df = full_df[full_df['week'].isin(TRAIN_WEEKS)]
    test_df = full_df[full_df['week'].isin(TEST_WEEKS)]
    
    print(f"\n📊 Data Split:")
    print(f"   Train: {len(train_df)} games (Weeks {min(TRAIN_WEEKS)}-{max(TRAIN_WEEKS)})")
    print(f"   Test:  {len(test_df)} games (Weeks {min(TEST_WEEKS)}-{max(TEST_WEEKS)})")
    
    # Train model
    model = train_residual_model(train_df)
    
    # Backtest
    backtest_results = backtest_residual_model(model, test_df, clv_threshold=1.0)
    
    # Print summary
    print_backtest_summary(backtest_results)
    
    # Save results
    if len(backtest_results) > 0:
        output_file = ARTIFACTS_DIR / f"xgb_residual_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        backtest_results.to_csv(output_file, index=False)
        print(f"\n📊 Results saved to: {output_file}")
    
    print("\n✅ Done!")


if __name__ == '__main__':
    main()

