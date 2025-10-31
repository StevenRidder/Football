"""
Step 1.2: Reliability analysis and Probability Integral Transform
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

# Load results
results = pd.read_csv("artifacts/backtest_2024_w1-8.csv")

print("=" * 60)
print("RELIABILITY ANALYSIS")
print("=" * 60)

# Calculate actual outcomes
results['actual_spread'] = results['actual_home_score'] - results['actual_away_score']
results['actual_total'] = results['actual_home_score'] + results['actual_away_score']

# Determine actual outcomes (handle pushes)
results['home_covered'] = (results['actual_spread'] > results['spread_line']).astype(float)
results['home_covered'] = results['home_covered'].where(
    results['actual_spread'] != results['spread_line'], 
    np.nan  # Push
)

results['over_hit'] = (results['actual_total'] > results['total_line']).astype(float)
results['over_hit'] = results['over_hit'].where(
    results['actual_total'] != results['total_line'],
    np.nan  # Push
)

# Probability Integral Transform for spreads
print("\n📊 PROBABILITY INTEGRAL TRANSFORM (Spread):")
results['spread_z'] = (results['actual_spread'] - results['spread_mean']) / results['spread_sd']
results['spread_cdf'] = stats.norm.cdf(results['spread_z'])
print(f"   Mean CDF: {results['spread_cdf'].mean():.4f} (should be ~0.5)")
print(f"   Std CDF: {results['spread_cdf'].std():.4f} (should be ~0.289)")

# Kolmogorov-Smirnov test (should be uniform if calibrated)
ks_stat, ks_pval = stats.kstest(results['spread_cdf'], 'uniform')
print(f"   KS test: stat={ks_stat:.4f}, p={ks_pval:.4f}")
if ks_pval > 0.05:
    print("   ✅ Distribution is consistent with uniform (well calibrated)")
else:
    print("   ⚠️  Distribution differs from uniform (calibration issue)")

# Reliability analysis for spreads
print("\n📊 RELIABILITY ANALYSIS (Spread):")
bins = [0, 0.4, 0.45, 0.5, 0.55, 0.6, 1.0]
results['p_bin'] = pd.cut(results['p_home_cover'], bins=bins)

reliability_spread = results.groupby('p_bin', observed=True).agg({
    'home_covered': ['mean', 'count'],
    'p_home_cover': 'mean'
}).round(4)

print(reliability_spread)

# Reliability analysis for totals
print("\n📊 RELIABILITY ANALYSIS (Total):")
results['p_bin_total'] = pd.cut(results['p_over'], bins=bins)

reliability_total = results.groupby('p_bin_total', observed=True).agg({
    'over_hit': ['mean', 'count'],
    'p_over': 'mean'
}).round(4)

print(reliability_total)

# Brier Score (lower is better, random is 0.25)
spread_valid = results.dropna(subset=['home_covered'])
brier_spread = np.mean((spread_valid['p_home_cover'] - spread_valid['home_covered'])**2)
print(f"\n📊 BRIER SCORE:")
print(f"   Spread: {brier_spread:.4f} (random=0.25, perfect=0.00)")

total_valid = results.dropna(subset=['over_hit'])
brier_total = np.mean((total_valid['p_over'] - total_valid['over_hit'])**2)
print(f"   Total: {brier_total:.4f} (random=0.25, perfect=0.00)")

# Log Loss (lower is better)
eps = 1e-10
log_loss_spread = -np.mean(
    spread_valid['home_covered'] * np.log(spread_valid['p_home_cover'] + eps) +
    (1 - spread_valid['home_covered']) * np.log(1 - spread_valid['p_home_cover'] + eps)
)
print(f"\n📊 LOG LOSS:")
print(f"   Spread: {log_loss_spread:.4f} (random=0.693, perfect=0.00)")

log_loss_total = -np.mean(
    total_valid['over_hit'] * np.log(total_valid['p_over'] + eps) +
    (1 - total_valid['over_hit']) * np.log(1 - total_valid['p_over'] + eps)
)
print(f"   Total: {log_loss_total:.4f} (random=0.693, perfect=0.00)")

# Create reliability plots
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Spread reliability plot
ax = axes[0]
for _, row in reliability_spread.iterrows():
    pred = row[('p_home_cover', 'mean')]
    actual = row[('home_covered', 'mean')]
    count = row[('home_covered', 'count')]
    if not np.isnan(actual):
        ax.scatter(pred, actual, s=count*10, alpha=0.6)
ax.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
ax.set_xlabel('Predicted Probability')
ax.set_ylabel('Observed Frequency')
ax.set_title('Spread Reliability Plot')
ax.legend()
ax.grid(True, alpha=0.3)

# Total reliability plot
ax = axes[1]
for _, row in reliability_total.iterrows():
    pred = row[('p_over', 'mean')]
    actual = row[('over_hit', 'mean')]
    count = row[('over_hit', 'count')]
    if not np.isnan(actual):
        ax.scatter(pred, actual, s=count*10, alpha=0.6)
ax.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
ax.set_xlabel('Predicted Probability')
ax.set_ylabel('Observed Frequency')
ax.set_title('Total Reliability Plot')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('artifacts/reliability_plots.png', dpi=150)
print("\n💾 Saved reliability plots to artifacts/reliability_plots.png")

print("\n" + "=" * 60)
