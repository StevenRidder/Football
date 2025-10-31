"""
Step 3.1: Analyze distribution shape targets

Track:
- Spread SD (target ~13)
- Total SD (target ~9-10)
- Explosive play rate (target ~10-12%)
- Turnover rate (target ~league average)
- Key number hit rates (3, 7)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load results with PFF
results = pd.read_csv("artifacts/backtest_with_pff.csv")

print("=" * 60)
print("SHAPE TARGET ANALYSIS")
print("=" * 60)

# We don't have per-simulation data, so we can't compute these metrics
# Let me create a modified backtest that tracks these

print("\n⚠️  Need to modify backtest to track shape metrics")
print("   Creating enhanced backtest...")

# For now, let's analyze what we have
print(f"\n📊 GAMES ANALYZED: {len(results)}")
print(f"   With PFF: {results['has_pff'].sum()}")
print(f"   Without PFF: {(~results['has_pff']).sum()}")

# Analyze actual outcomes
print(f"\n📊 ACTUAL OUTCOMES:")
print(f"   Spread mean: {results['actual_spread'].mean():.2f}")
print(f"   Spread SD: {results['actual_spread'].std():.2f}")
print(f"   Total mean: {results['actual_total'].mean():.2f}")
print(f"   Total SD: {results['actual_total'].std():.2f}")

# Key numbers
spreads = results['actual_spread'].values
print(f"\n📊 KEY NUMBER HIT RATES (Actual):")
print(f"   Spread = 3: {np.sum(np.abs(spreads - 3) < 0.5)} games ({100*np.sum(np.abs(spreads - 3) < 0.5)/len(spreads):.1f}%)")
print(f"   Spread = 7: {np.sum(np.abs(spreads - 7) < 0.5)} games ({100*np.sum(np.abs(spreads - 7) < 0.5)/len(spreads):.1f}%)")
print(f"   Spread = -3: {np.sum(np.abs(spreads + 3) < 0.5)} games ({100*np.sum(np.abs(spreads + 3) < 0.5)/len(spreads):.1f}%)")
print(f"   Spread = -7: {np.sum(np.abs(spreads + 7) < 0.5)} games ({100*np.sum(np.abs(spreads + 7) < 0.5)/len(spreads):.1f}%)")

print("\n" + "=" * 60)
print("CREATING ENHANCED BACKTEST WITH SHAPE TRACKING")
print("=" * 60)

