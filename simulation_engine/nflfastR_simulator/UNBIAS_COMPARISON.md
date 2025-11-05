# Unbias Model vs Previous Model - Comparison

## Overall Results

### Spread Bets
**Both models show identical overall performance:**
- Total bets: 97 (unchanged)
- Win rate: 64.9% (unchanged)
- ROI: +24.0% (unchanged)
- Record: 63W-34L (unchanged)

### Totals Bets
**Unbias model shows slight degradation:**
- Total bets: 84 (was 82) - **+2 bets**
- Win rate: 52.4% (was 54.9%) - **-2.5%**
- ROI: -0.0% (was +4.8%) - **-4.8% ROI**
- Record: 44W-40L (was 45W-37L)

## By Conviction Tier

### Spread Bets - HIGH Conviction
- **Previous**: 26 bets, 76.9% win rate, +46.8% ROI
- **Unbias**: 30 bets, 76.7% win rate, +46.4% ROI
- **Analysis**: More bets classified as HIGH, but win rate and ROI virtually identical

### Spread Bets - MEDIUM Conviction
- **Previous**: 29 bets, 72.4% win rate, +38.2% ROI
- **Unbias**: 33 bets, 69.7% win rate, +33.1% ROI
- **Analysis**: More bets classified as MEDIUM, but win rate and ROI slightly lower

### Spread Bets - LOW Conviction
- **Previous**: 42 bets, 52.4% win rate, -0.0% ROI
- **Unbias**: 34 bets, 50.0% win rate, -4.5% ROI
- **Analysis**: Fewer LOW bets (good), but those remaining perform worse

### Totals Bets - HIGH Conviction
- **Previous**: 22 bets, 63.6% win rate, +21.5% ROI
- **Unbias**: 22 bets, 59.1% win rate, +12.8% ROI
- **Analysis**: Same bet count, but win rate and ROI significantly lower

### Totals Bets - MEDIUM Conviction
- **Previous**: 20 bets, 60.0% win rate, +14.5% ROI
- **Unbias**: 19 bets, 57.9% win rate, +10.5% ROI
- **Analysis**: Similar bet count, slightly lower performance

### Totals Bets - LOW Conviction
- **Previous**: 40 bets, 47.5% win rate, -9.3% ROI
- **Unbias**: 43 bets, 46.5% win rate, -11.2% ROI
- **Analysis**: More LOW bets, worse performance

## Key Observations

### What's Working
1. **Spread bets maintain excellent performance** - ROI unchanged at +24.0%
2. **Bias correction is redistributing bets** - More bets moving from LOW to HIGH/MEDIUM for spreads
3. **No data leakage** - Bias correction only uses prior weeks

### Concerns
1. **Totals bets degraded** - Lost 4.8% ROI, win rate dropped 2.5%
2. **HIGH conviction totals underperforming** - ROI dropped from +21.5% to +12.8%
3. **LOW conviction bets getting worse** - Both spreads and totals showing negative ROI in LOW tier

## Potential Issues

### 1. LA Team Warnings
**Issue**: Multiple warnings about "LA" team not found in PFF data
- PFF data uses "LAR" (Los Angeles Rams)
- Game data uses "LA" 
- **Status**: Fixed in `pff_loader.py` - now maps "LA" → "LAR"

### 2. Bias Correction Impact
The bias correction may be:
- **Overcorrecting** for some teams (especially early in season with limited history)
- **Undercorrecting** for totals (which may need different bias patterns than spreads)
- **Creating noise** in LOW conviction bets

## Recommendations

1. **Monitor calibration curves** - Check `calibration_spread_all.png` and `calibration_total_all.png`
2. **Review bias_history.csv** - Look for teams with large persistent residuals
3. **Consider separate bias correction** for spreads vs totals
4. **Adjust split ratio** - Current 60/40 offense/defense may need tuning
5. **Season progression** - Bias correction should improve as more weeks accumulate

## Next Steps

1. ✅ Fixed LA team mapping issue
2. Review calibration plots to assess probability calibration
3. Analyze weekly ROI trends in `weekly_roi.csv`
4. Consider making bias correction optional or weighted by number of prior games

