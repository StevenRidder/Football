"""
Test isotonic vs linear calibration on backtest (High Priority #1).

Compare ROI, win rate, and reliability between:
1. Linear calibration (current default)
2. Isotonic calibration (new priority)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_backtest_results():
    """Load completed backtest games."""
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        raise FileNotFoundError(f"Backtest file not found: {backtest_file}")
    
    df = pd.read_csv(backtest_file)
    completed = df[df['actual_home_score'].notna()].copy()
    
    return completed

def grade_bet_calibration_method(df, calibration_col):
    """
    Grade bets assuming a specific calibration method was used.
    
    Args:
        df: DataFrame with game results
        calibration_col: Column name for probabilities (e.g., 'p_home_cover', 'p_over')
    """
    # Filter to games where we would have bet
    bets = df[df[calibration_col].notna()].copy()
    
    if calibration_col.startswith('p_home'):
        # Spread bet - home cover
        bets['bet_side'] = 'home'
        bets['bet_outcome'] = (bets['actual_spread'] > bets['spread_line']).astype(float)
        bets.loc[abs(bets['actual_spread'] - bets['spread_line']) < 0.1, 'bet_outcome'] = 0.5  # Push
        line_col = 'spread_line'
        edge_col = 'spread_edge_pct'
    elif calibration_col.startswith('p_over'):
        # Total bet - over
        bets['bet_side'] = 'over'
        bets['bet_outcome'] = (bets['actual_total'] > bets['total_line']).astype(float)
        bets.loc[abs(bets['actual_total'] - bets['total_line']) < 0.5, 'bet_outcome'] = 0.5  # Push
        line_col = 'total_line'
        edge_col = 'total_edge_pct'
    else:
        raise ValueError(f"Unknown calibration column: {calibration_col}")
    
    # Calculate edge
    if edge_col in bets.columns:
        bets['edge'] = bets[edge_col]
    else:
        # Calculate edge from probability and line
        if calibration_col.startswith('p_home'):
            breakeven_p = 0.524  # -110 odds
            bets['edge'] = bets[calibration_col] - breakeven_p
        else:
            breakeven_p = 0.524
            bets['edge'] = bets[calibration_col] - breakeven_p
    
    # Filter to positive edge bets
    positive_edge = bets[bets['edge'] > 0.02].copy()  # 2% edge threshold
    
    if len(positive_edge) == 0:
        return {
            'total_bets': 0,
            'wins': 0,
            'losses': 0,
            'pushes': 0,
            'win_rate': 0.0,
            'roi': 0.0
        }
    
    # Grade bets
    wins = (positive_edge['bet_outcome'] == 1.0).sum()
    losses = (positive_edge['bet_outcome'] == 0.0).sum()
    pushes = (positive_edge['bet_outcome'] == 0.5).sum()
    
    # ROI (assuming -110 odds, exclude pushes)
    net_wins = wins - losses
    roi = (net_wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0.0
    
    return {
        'total_bets': len(positive_edge),
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'win_rate': (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0.0,
        'roi': roi
    }

def compare_calibration_methods():
    """Compare linear vs isotonic calibration performance."""
    print("="*70)
    print("CALIBRATION METHOD COMPARISON")
    print("="*70)
    
    df = load_backtest_results()
    print(f"\n✅ Loaded {len(df)} completed games")
    
    # Check which calibration columns exist
    linear_cols = ['p_home_cover', 'p_over']  # These might be linear
    isotonic_cols = ['p_home_cover_isotonic', 'p_over_isotonic']  # Check if these exist
    
    # Actually, check what calibration_method columns tell us
    if 'calibration_method' in df.columns:
        linear_games = df[df['calibration_method'] == 'linear']
        isotonic_games = df[df['calibration_method'] == 'isotonic']
        
        print(f"\n📊 Calibration Method Distribution:")
        print(f"   Linear: {len(linear_games)} games")
        print(f"   Isotonic: {len(isotonic_games)} games")
        
        # Grade each method
        print(f"\n📈 SPREAD BETS:")
        print(f"\n   Linear Calibration:")
        linear_spread = grade_bet_calibration_method(linear_games, 'p_home_cover')
        print(f"      Bets: {linear_spread['total_bets']}")
        print(f"      Win Rate: {linear_spread['win_rate']:.1f}%")
        print(f"      ROI: {linear_spread['roi']:.1f}%")
        
        if len(isotonic_games) > 0:
            print(f"\n   Isotonic Calibration:")
            isotonic_spread = grade_bet_calibration_method(isotonic_games, 'p_home_cover')
            print(f"      Bets: {isotonic_spread['total_bets']}")
            print(f"      Win Rate: {isotonic_spread['win_rate']:.1f}%")
            print(f"      ROI: {isotonic_spread['roi']:.1f}%")
        
        print(f"\n📈 TOTAL BETS:")
        print(f"\n   Linear Calibration:")
        linear_total = grade_bet_calibration_method(linear_games, 'p_over')
        print(f"      Bets: {linear_total['total_bets']}")
        print(f"      Win Rate: {linear_total['win_rate']:.1f}%")
        print(f"      ROI: {linear_total['roi']:.1f}%")
        
        if len(isotonic_games) > 0:
            print(f"\n   Isotonic Calibration:")
            isotonic_total = grade_bet_calibration_method(isotonic_games, 'p_over')
            print(f"      Bets: {isotonic_total['total_bets']}")
            print(f"      Win Rate: {isotonic_total['win_rate']:.1f}%")
            print(f"      ROI: {isotonic_total['roi']:.1f}%")
    else:
        print(f"\n⚠️  No 'calibration_method' column found")
        print(f"   Available columns: {list(df.columns)}")
        
        # Try to infer from probability values
        print(f"\n📊 Probability Statistics:")
        if 'p_home_cover' in df.columns:
            print(f"   p_home_cover range: [{df['p_home_cover'].min():.3f}, {df['p_home_cover'].max():.3f}]")
            print(f"   p_home_cover mean: {df['p_home_cover'].mean():.3f}")
        
        if 'p_over' in df.columns:
            print(f"   p_over range: [{df['p_over'].min():.3f}, {df['p_over'].max():.3f}]")
            print(f"   p_over mean: {df['p_over'].mean():.3f}")

if __name__ == "__main__":
    compare_calibration_methods()

