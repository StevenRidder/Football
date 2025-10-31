#!/usr/bin/env python3
"""
Unit Test: Verify centering is exact.

Per strategy: centering must match market mean within 0.1 points.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "simulator"))

from simulator.market_centering import center_scores_to_market


def test_centering_exact():
    """Test that centering produces exact means."""
    print("="*80)
    print("UNIT TEST: Centering Exactness")
    print("="*80 + "\n")
    
    rng = np.random.default_rng(42)
    home = rng.normal(20, 7, 10000)
    away = rng.normal(17, 7, 10000)
    
    market_spread = -3.0  # Home favored by 3
    market_total = 46.5
    
    print(f"Raw home mean: {np.mean(home):.2f}")
    print(f"Raw away mean: {np.mean(away):.2f}")
    print(f"Raw spread mean (home - away): {np.mean(home - away):.2f}")
    print(f"Raw total mean: {np.mean(home + away):.2f}")
    print()
    
    ha, aa = center_scores_to_market(home, away, market_spread, market_total)
    
    centered_spread = np.mean(ha - aa)
    centered_total = np.mean(ha + aa)
    
    print(f"Centered home mean: {np.mean(ha):.2f}")
    print(f"Centered away mean: {np.mean(aa):.2f}")
    print(f"Centered spread mean (home - away): {centered_spread:.2f}")
    print(f"Centered total mean: {centered_total:.2f}")
    print()
    
    spread_error = abs(centered_spread - market_spread)
    total_error = abs(centered_total - market_total)
    
    print(f"Target spread: {market_spread:.1f}")
    print(f"Target total: {market_total:.1f}")
    print()
    print(f"Spread error: {spread_error:.4f}")
    print(f"Total error: {total_error:.4f}")
    print()
    
    # Assert within 0.1 points
    assert spread_error < 0.1, f"Spread error {spread_error:.4f} >= 0.1"
    assert total_error < 0.1, f"Total error {total_error:.4f} >= 0.1"
    
    print("✅ PASS: Centering is exact (within 0.1 points)")
    print("="*80 + "\n")


if __name__ == '__main__':
    test_centering_exact()

