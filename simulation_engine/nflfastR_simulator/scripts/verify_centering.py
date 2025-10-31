"""
Verify that centering is working correctly:
- mean(home_adj - away_adj) should equal spread_line
- mean(home_adj + away_adj) should equal total_line
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

# Load the backtest results
results = pd.read_csv("artifacts/backtest_2024_w1-8.csv")

print("=" * 60)
print("CENTERING VERIFICATION")
print("=" * 60)

# Check spread centering
spread_error = results['spread_mean'] - results['spread_line']
print(f"\n📊 SPREAD CENTERING:")
print(f"   Mean error: {spread_error.mean():.4f} (should be ~0)")
print(f"   Max error: {spread_error.abs().max():.4f}")
print(f"   Std error: {spread_error.std():.4f}")

# Check total centering
total_error = results['total_mean'] - results['total_line']
print(f"\n📊 TOTAL CENTERING:")
print(f"   Mean error: {total_error.mean():.4f} (should be ~0)")
print(f"   Max error: {total_error.abs().max():.4f}")
print(f"   Std error: {total_error.std():.4f}")

# Check if centering is within tolerance
spread_ok = spread_error.abs().max() < 0.1
total_ok = total_error.abs().max() < 0.1

if spread_ok and total_ok:
    print("\n✅ CENTERING IS CORRECT")
else:
    print("\n❌ CENTERING HAS ISSUES")
    if not spread_ok:
        print(f"   Spread max error {spread_error.abs().max():.4f} > 0.1")
    if not total_ok:
        print(f"   Total max error {total_error.abs().max():.4f} > 0.1")

print("\n" + "=" * 60)

