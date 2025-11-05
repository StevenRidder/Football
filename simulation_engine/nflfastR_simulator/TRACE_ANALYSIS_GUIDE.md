# Trace Analysis Guide

## Overview

Two scripts help you analyze simulator traces and compare to NFLfastR actuals:

1. **`compare_to_nflfastr.py`** - Basic calibration metrics (scores, EPA, pressure correlation)
2. **`analyze_traces_deep.py`** - Deep pattern detection with per-team analysis

## Quick Start

### Basic Calibration
```bash
python3 compare_to_nflfastr.py --season 2025 --weeks 1-8
```

This generates:
- `artifacts/calibration/summary_metrics.json` - Overall calibration stats
- `artifacts/calibration/per_team_bias.csv` - Per-team EPA residuals
- `artifacts/calibration/per_game_comparison.csv` - Game-by-game comparison
- `artifacts/calibration/plots/` - Visualization plots

### Deep Pattern Analysis
```bash
python3 analyze_traces_deep.py --season 2025 --weeks 1-8
```

This generates:
- `artifacts/trace_analysis/per_team_bias.csv` - Detailed per-team metrics
- `artifacts/trace_analysis/full_comparison.csv` - Complete comparison
- Pattern detection output (pressure, EPA, completion rate issues)

### Analyze Specific Team
```bash
python3 analyze_traces_deep.py --season 2025 --weeks 1-8 --team DAL
```

## What Patterns to Look For

### 1. Pressure Rate Issues
- **Sim < Actual**: Your OL/DL mismatch coefficient is too weak
- **Sim > Actual**: Your base pressure rate is too high
- **Per-team bias**: Certain teams have systematic pressure miscalibration

**Example from Week 9:**
- PIT: 29.6% sim vs 15% actual → Overestimating pressure
- KC: 30% sim vs 42.5% actual → Underestimating pressure

### 2. EPA Inflation
- **Sim EPA > Actual EPA**: Offensive efficiency too high, defensive variance too low
- **Large gaps (>0.15 EPA)**: Specific team inputs are wrong

**Example from Week 9:**
- IND: 0.165 sim vs -0.268 actual (0.434 gap!) → Massive overrating

### 3. Score Bias
- **Sim totals too high**: Drive efficiency too high, defensive stops too rare
- **Individual team bias**: Team-specific scoring issues

**Example from Week 9:**
- IND: 42 sim vs 20 actual (+22 points)
- MIN: 0 sim vs 27 actual (-27 points)

### 4. Completion Rate Issues
- **Clean pocket too high**: QB baseline completion rate too optimistic
- **Under pressure too high**: Pressure impact on completion too weak

## Weekly Calibration Workflow

1. **Run simulations** (generates traces)
2. **Run analysis**:
   ```bash
   python3 analyze_traces_deep.py --season 2025 --weeks 9
   ```
3. **Review patterns**:
   - Check per-team bias CSV for outliers
   - Look for systematic issues (pressure, EPA, completion)
4. **Adjust simulator**:
   - Tune OL/DL mismatch coefficient if pressure is off
   - Adjust defensive variance damping if EPA is inflated
   - Fix team-specific inputs if individual teams are wrong
5. **Re-run and verify** improvements

## Key Metrics Explained

### Pressure Bias
- **Positive**: Simulating more pressure than actual
- **Negative**: Simulating less pressure than actual
- **Target**: Within ±5% of actual

### EPA Bias
- **Positive**: Simulated offense is better than actual
- **Negative**: Simulated offense is worse than actual
- **Target**: Within ±0.05 EPA per play

### Score Bias
- **Positive**: Simulated scores are higher than actual
- **Negative**: Simulated scores are lower than actual
- **Target**: Within ±3 points per game

## Integration with Bias Calibration

The trace analysis complements your existing `bias_calibration.py`:

- **Trace analysis** = Diagnostic (what's wrong)
- **Bias calibration** = Correction (how to fix it)

Use trace analysis to identify issues, then let bias calibration correct them automatically.

## Next Steps

1. **Weekly analysis**: Run after each week's games
2. **Track trends**: Build time series of biases per team
3. **Calibrate iteratively**: Adjust one parameter at a time, re-run, verify
4. **Focus on outliers**: Teams with >2σ bias need immediate attention

