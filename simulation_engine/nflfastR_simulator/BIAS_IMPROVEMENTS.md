# Bias Correction Improvements

## Changes Implemented

### 1. **Sharper Bias Signal**
- **Shorter memory**: `span_ewm` reduced from 4 → 2
- **Smaller cap**: `clip_points` reduced from 2.0 → 1.0
- **Split ratio**: Changed from (0.6, 0.4) → (0.5, 0.5) for more balanced offense/defense adjustment

### 2. **Venue-Aware Residuals**
- Bias tracking now separated by home/away venue
- Teams can have different bias patterns at home vs away
- Applied via `get_score_adjustment(..., venue='home'|'away')`

### 3. **Opponent-Adjusted Bias**
- Residuals are regressed against opponent defensive strength
- Removes schedule-driven bias (e.g., "team looks bad because they played tough defenses")
- Uses rolling average of opponent's points allowed as proxy for defensive strength

### 4. **Margin-Only Application**
- **Critical change**: Bias correction now adjusts **margin only**, not raw scores
- Total prediction stays unchanged (helps spreads without hurting totals)
- Implementation:
  ```
  1. Compute total_raw and margin_raw
  2. Get net bias for home/away (venue-aware)
  3. Adjust margin: margin_adj = margin_raw + clamp(home_net - away_net, ±1.0) * 0.5
  4. Rebuild scores: home = (total + margin_adj)/2, away = (total - margin_adj)/2
  ```

## Expected Results

### Spreads
- Should maintain ~64.9% win rate with better calibration
- Less team drift in leaderboard (PIT/DAL quirks should diminish)
- Margin MAE should decrease

### Totals
- Should revert to ~55% win rate (from 52.4%)
- Total prediction unchanged by bias correction
- Total MAE should stay stable or improve slightly

## Key Files Modified

1. **`bias_calibration.py`**
   - `_rolling_bias_table()`: Now venue-aware and opponent-adjusted
   - `get_score_adjustment()`: Added `venue` parameter, updated defaults
   - `apply_bias_correction_to_scores()`: Updated defaults (not used in margin-only approach)

2. **`backtest_all_games_conviction.py`**
   - Replaced `apply_bias_correction_to_scores()` with margin-only adjustment
   - Uses `get_score_adjustment()` directly for home/away net bias
   - Rebuilds scores from adjusted margin + original total

## Testing Recommendations

After running the backtest, check:

1. **Calibration curves**: Should show improved spread calibration
2. **Weekly ROI**: Should show totals ROI recovering toward +4.8%
3. **Bias history**: Look for venue-specific patterns in `bias_history.csv`
4. **Team residuals**: Should see reduced team-specific drift

## Next Steps (If Needed)

If totals still underperform:
- Consider disabling bias correction entirely for totals
- Or apply different bias correction parameters for totals vs spreads
- Monitor weekly trends - bias correction should improve as more weeks accumulate

