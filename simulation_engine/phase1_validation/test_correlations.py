"""
Phase 1 - Step 3: Test Correlations

Test if OL/DL matchup metrics correlate with game outcomes:
- Does net_pressure_advantage correlate with point_differential?
- Does it correlate better than market spread?
- Is there predictive power here?
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"


def load_matchup_data():
    """Load matchup metrics."""
    print("📊 Loading matchup metrics...")
    df = pd.read_csv(DATA_DIR / "matchup_metrics_2022_2024.csv")
    
    # Filter to completed games only
    completed = df[df['point_differential'].notna()].copy()
    
    print(f"   Total games: {len(completed)}")
    print(f"   Years: {completed['season'].min()}-{completed['season'].max()}")
    
    return completed


def test_pressure_correlation(df):
    """Test if pressure advantage correlates with point differential."""
    print("\n" + "="*80)
    print("TEST 1: PRESSURE ADVANTAGE vs POINT DIFFERENTIAL")
    print("="*80)
    
    # Calculate correlation
    corr, p_value = stats.pearsonr(df['net_pressure_advantage'], df['point_differential'])
    
    print(f"\n📊 Correlation: {corr:.4f}")
    print(f"📊 P-value: {p_value:.6f}")
    print(f"📊 Significant: {'YES ✅' if p_value < 0.05 else 'NO ❌'}")
    
    # Compare to market spread correlation
    games_with_spread = df[df['spread_line'].notna()].copy()
    if len(games_with_spread) > 0:
        spread_corr, spread_p = stats.pearsonr(games_with_spread['spread_line'], games_with_spread['point_differential'])
        print(f"\n📊 Market Spread Correlation: {spread_corr:.4f}")
        print(f"📊 Market Spread P-value: {spread_p:.6f}")
        
        print(f"\n🎯 Pressure Edge vs Market:")
        print(f"   Pressure: {abs(corr):.4f}")
        print(f"   Market:   {abs(spread_corr):.4f}")
        print(f"   Winner:   {'PRESSURE ✅' if abs(corr) > abs(spread_corr) else 'MARKET ❌'}")
    
    return corr, p_value


def test_big_mismatch_games(df):
    """Test if games with big pressure mismatches have different outcomes."""
    print("\n" + "="*80)
    print("TEST 2: BIG MISMATCH GAMES")
    print("="*80)
    
    # Define "big mismatch" as top 25% of absolute pressure advantage
    df['abs_pressure_advantage'] = df['net_pressure_advantage'].abs()
    threshold = df['abs_pressure_advantage'].quantile(0.75)
    
    big_mismatch = df[df['abs_pressure_advantage'] > threshold].copy()
    small_mismatch = df[df['abs_pressure_advantage'] <= threshold].copy()
    
    print(f"\n📊 Threshold: {threshold:.2f}")
    print(f"📊 Big mismatch games: {len(big_mismatch)}")
    print(f"📊 Small mismatch games: {len(small_mismatch)}")
    
    # Test if point differentials are different
    t_stat, p_value = stats.ttest_ind(
        big_mismatch['point_differential'].abs(),
        small_mismatch['point_differential'].abs()
    )
    
    print(f"\n📊 Avg point diff (big mismatch): {big_mismatch['point_differential'].abs().mean():.2f}")
    print(f"📊 Avg point diff (small mismatch): {small_mismatch['point_differential'].abs().mean():.2f}")
    print(f"📊 T-statistic: {t_stat:.4f}")
    print(f"📊 P-value: {p_value:.6f}")
    print(f"📊 Significant: {'YES ✅' if p_value < 0.05 else 'NO ❌'}")
    
    return t_stat, p_value


def test_directional_prediction(df):
    """Test if pressure advantage predicts WHO wins (not just by how much)."""
    print("\n" + "="*80)
    print("TEST 3: DIRECTIONAL PREDICTION")
    print("="*80)
    
    # Predict: If net_pressure_advantage > 0, home wins
    df['predicted_home_win'] = df['net_pressure_advantage'] > 0
    df['actual_home_win'] = df['point_differential'] > 0
    
    correct = (df['predicted_home_win'] == df['actual_home_win']).sum()
    total = len(df)
    accuracy = correct / total
    
    print(f"\n📊 Correct predictions: {correct}/{total}")
    print(f"📊 Accuracy: {accuracy:.1%}")
    print(f"📊 Baseline (50%): {'BEAT ✅' if accuracy > 0.50 else 'MISS ❌'}")
    
    # Compare to market spread
    games_with_spread = df[df['spread_line'].notna()].copy()
    if len(games_with_spread) > 0:
        games_with_spread['market_predicted_home_win'] = games_with_spread['spread_line'] > 0
        market_correct = (games_with_spread['market_predicted_home_win'] == games_with_spread['actual_home_win']).sum()
        market_accuracy = market_correct / len(games_with_spread)
        
        print(f"\n📊 Market Accuracy: {market_accuracy:.1%}")
        print(f"📊 Winner: {'PRESSURE ✅' if accuracy > market_accuracy else 'MARKET ❌'}")
    
    return accuracy


def main():
    """Run all correlation tests."""
    print("="*80)
    print("PHASE 1 - STEP 3: CORRELATION TESTS")
    print("Testing if OL/DL matchups predict game outcomes")
    print("="*80)
    
    # Load data
    df = load_matchup_data()
    
    # Run tests
    corr, p_val = test_pressure_correlation(df)
    t_stat, t_p = test_big_mismatch_games(df)
    accuracy = test_directional_prediction(df)
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"\n1. Pressure Correlation: {corr:.4f} (p={p_val:.6f})")
    print(f"2. Big Mismatch T-test: t={t_stat:.4f} (p={t_p:.6f})")
    print(f"3. Directional Accuracy: {accuracy:.1%}")
    
    if p_val < 0.05 and accuracy > 0.50:
        print("\n✅ CONCLUSION: Pressure advantage shows SIGNIFICANT predictive power!")
        print("   → Proceed to Phase 1 Step 4: Add to Ridge model and backtest")
    elif p_val < 0.05:
        print("\n⚠️  CONCLUSION: Pressure advantage correlates but doesn't predict direction well")
        print("   → May need non-linear model or interaction terms")
    else:
        print("\n❌ CONCLUSION: Pressure advantage does NOT show significant predictive power")
        print("   → PFF matchup data may not provide edge over current EPA model")


if __name__ == "__main__":
    main()

