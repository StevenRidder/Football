"""
SANITY TEST: Does PFF Help Beat the Market?

Compare ATS (Against The Spread) Mean Absolute Error:
1. Market Baseline (always predict spread = 0)
2. EPA-only model
3. EPA+PFF model

If EPA+PFF doesn't beat EPA by a meaningful amount, PFF adds no value.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"


def load_data():
    """Load matchup metrics with EPA and PFF data."""
    print("📊 Loading data...")
    
    df = pd.read_csv(DATA_DIR / "matchup_metrics_2022_2024.csv")
    
    # Filter to completed games with spread lines
    completed = df[
        df['point_differential'].notna() & 
        df['spread_line'].notna()
    ].copy()
    
    print(f"   Games with spreads: {len(completed)}")
    
    return completed


def calculate_market_baseline_mae(df):
    """
    Market Baseline: Always predict the spread will be exactly the market line.
    MAE = how far off the market spread is from actual spread.
    """
    print("\n" + "="*80)
    print("1. MARKET BASELINE (predict spread = market spread)")
    print("="*80)
    
    # Market predicts: actual_spread = spread_line
    # Error = actual_spread - spread_line
    errors = df['point_differential'] - df['spread_line']
    mae = np.mean(np.abs(errors))
    
    print(f"\n📊 Market MAE: {mae:.2f} points")
    print(f"   (This is how accurate Vegas is on average)")
    
    return mae


def calculate_market_adjusted_pff_mae(df):
    """
    PFF-only: Use market spread as baseline, add PFF pressure adjustment.
    
    Theory: Market is already efficient, but PFF OL/DL mismatch might add signal.
    If net_pressure_advantage > 0, home should do better than market expects.
    """
    print("\n" + "="*80)
    print("2. MARKET + PFF ADJUSTMENT")
    print("="*80)
    
    # Start with market spread as baseline
    # Add PFF pressure adjustment
    # net_pressure_advantage > 0 means home has pressure edge
    df['pff_adjustment'] = df['net_pressure_advantage'] * 0.15  # Scale factor to calibrate
    
    df['market_pff_predicted_spread'] = df['spread_line'] + df['pff_adjustment']
    
    # Calculate error vs actual
    errors = df['point_differential'] - df['market_pff_predicted_spread']
    mae = np.mean(np.abs(errors))
    
    print(f"\n📊 Market+PFF MAE: {mae:.2f} points")
    print(f"   PFF correlation with market residual: {df['net_pressure_advantage'].corr(df['point_differential'] - df['spread_line']):.3f}")
    
    # Check if PFF adds signal to market residuals
    market_errors = df['point_differential'] - df['spread_line']
    pff_predicts_error = df['net_pressure_advantage'].corr(market_errors)
    print(f"   Does PFF predict market errors? r={pff_predicts_error:.3f}")
    
    return mae


def compare_results(market_mae, pff_mae):
    """Compare market baseline vs market+PFF."""
    print("\n" + "="*80)
    print("📊 COMPARISON")
    print("="*80)
    
    print(f"\n{'Model':<30} {'MAE':<15} {'vs Market':<20}")
    print("-"*65)
    
    # Market baseline
    print(f"{'Market Baseline':<30} {market_mae:<15.2f} {'-':<20}")
    
    # Market+PFF
    pff_improvement = market_mae - pff_mae
    pff_pct = (pff_improvement / market_mae) * 100
    print(f"{'Market + PFF Adjustment':<30} {pff_mae:<15.2f} {pff_improvement:+.2f} ({pff_pct:+.1f}%)")
    
    print("-"*65)
    
    # Verdict
    print("\n🎯 VERDICT:")
    
    if pff_mae < market_mae:
        improvement = market_mae - pff_mae
        if improvement > 0.3:  # Meaningful improvement (>3% of ~9.5pt MAE)
            print(f"   ✅ PFF HELPS: Reduces error by {improvement:.2f} points ({pff_pct:.1f}%)")
            print(f"   → PFF OL/DL matchups add signal beyond market")
            print(f"   → Worth integrating into Monte Carlo simulation")
        else:
            print(f"   ⚠️  PFF HELPS SLIGHTLY: Only {improvement:.2f} points ({pff_pct:.1f}%)")
            print(f"   → Marginal benefit, may not be worth complexity")
            print(f"   → Stick with EPA-only simulation")
    else:
        decline = pff_mae - market_mae
        print(f"   ❌ PFF MAKES IT WORSE: Increases error by {decline:.2f} points")
        print(f"   → PFF OL/DL matchups have NO predictive value")
        print(f"   → Keep simulator lean, skip PFF")


def main():
    """Run sanity test."""
    print("="*80)
    print("SANITY TEST: Does PFF Help Beat the Market?")
    print("Testing on 2022-2024 data")
    print("="*80)
    
    # Load data
    df = load_data()
    
    # Calculate MAE for each approach
    market_mae = calculate_market_baseline_mae(df)
    pff_mae = calculate_market_adjusted_pff_mae(df)
    
    # Compare
    compare_results(market_mae, pff_mae)
    
    print("\n" + "="*80)
    print("✅ SANITY TEST COMPLETE")
    print("="*80)
    print("\n📋 Next Steps:")
    print("   1. If PFF helps (>0.3pt improvement):")
    print("      → Build Monte Carlo sim with PFF OL/DL pressure adjustments")
    print("      → Test: simulate_drive(epa, ol_grade, dl_grade)")
    print("   2. If PFF doesn't help:")
    print("      → Keep simulator lean (EPA-only)")
    print("      → Focus on other edges (coaching, game script, etc.)")


if __name__ == "__main__":
    main()

