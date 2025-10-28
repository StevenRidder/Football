# 🚨 CRITICAL FIXES NEEDED

## ✅ COMPLETED
1. ✅ Fixed weather data (km/h → mph conversion)
2. ✅ Created adjusted recommendations system (ADJUSTED vs MARKET)
3. ✅ Moved injury report to game detail pages
4. ✅ Fixed JavaScript undefined errors
5. ✅ LLM injury detection working (OpenAI)

## ❌ CRITICAL ISSUE: Market Lines Are Wrong

### Problem
**The predictions are using MODEL predictions as "market lines", not REAL market lines from sportsbooks!**

Example - CAR @ GB:
- **Real Market:** GB -12.5, Total 44.5
- **What's in CSV:** Spread 10.97, Total 49.08 (MODEL predictions!)

This means:
- ❌ Market-implied scores are wrong
- ❌ Adjusted scores are wrong
- ❌ Betting recommendations are wrong
- ❌ We're comparing our model to itself, not to the market!

### Solution

**Step 1: Get your Odds API key**
Visit: https://the-odds-api.com/

**Step 2: Set environment variable**
```bash
export ODDS_API_KEY='your-real-key-here'
```

**Step 3: Fetch real market lines**
```bash
cd /Users/steveridder/Git/Football
python3 fetch_current_market_lines.py
```

This will:
1. Fetch current lines from The Odds API
2. Update `predictions_2025_2025-10-28.csv` with REAL market lines
3. Replace model predictions with actual sportsbook numbers

**Step 4: Regenerate signals**
```bash
python3 precompute_edge_hunt_signals.py
```

**Step 5: Restart Flask**
```bash
lsof -ti:9876 | xargs kill -9
python3 app_flask.py
```

---

## How It Should Work (Once Fixed)

### Example: CAR @ GB

**1. Market Lines (from Odds API):**
- Spread: GB -12.5
- Total: 44.5

**2. Market-Implied Score:**
```
Away - Home = 12.5 (GB favored by 12.5)
Away + Home = 44.5
→ CAR = 16, GB = 29
```

**3. Apply Adjustments:**
- No injuries detected
- No weather signals
- **Adjusted = Market** (16-29)

**4. Betting Decision:**
- Adjusted Total: 45 (16+29)
- Market Total: 44.5
- Edge: 0.5 points (too small)
- **Recommendation: SKIP**

### Example: MIN @ DET (With Injury)

**1. Market Lines:**
- Spread: DET -8.5
- Total: 47.5

**2. Market-Implied Score:**
```
Home - Away = 8.5 (DET favored)
Away + Home = 47.5
→ MIN = 19.5, DET = 28
```

**3. Apply Adjustments:**
- MIN: -10 points (Wentz out, 2 OL out)
- DET: 0 points
- **Adjusted: MIN 9.5, DET 28**

**4. Betting Decision:**
- Adjusted Spread: DET -18.5
- Market Spread: DET -8.5
- **Spread Edge: 10 points → BET DET -8.5** ✅

- Adjusted Total: 37.5 (9.5+28)
- Market Total: 47.5
- **Total Edge: 10 points → BET UNDER 47.5** ✅

---

## Current Status

### What's Working ✅
- LLM injury detection (OpenAI)
- Weather data (fixed km/h conversion)
- Adjusted recommendation logic
- Flask API serving data
- UI displaying scores

### What's Broken ❌
- **Market lines are model predictions, not real market**
- All calculations are based on fake market data
- Can't trust any betting recommendations until this is fixed

---

## Quick Test After Fix

Run this to verify:
```bash
curl -s http://localhost:9876/api/games | python3 -c "
import json, sys
data = json.load(sys.stdin)
car_gb = [g for g in data if g['away'] == 'CAR' and g['home'] == 'GB'][0]
print(f'Market Spread: {car_gb[\"market_spread\"]}')
print(f'Market Total: {car_gb[\"market_total\"]}')
print(f'Expected: -12.5, 44.5')
"
```

Should show:
```
Market Spread: -12.5
Market Total: 44.5
Expected: -12.5, 44.5
```

---

## Files Created

1. **`fetch_current_market_lines.py`** - Fetches real market lines from Odds API
2. **`nfl_edge/adjusted_recommendations.py`** - Generates betting recs (ADJUSTED vs MARKET)
3. **`edge_hunt/llm_injury_detector.py`** - LLM-powered injury detection
4. **`market_implied_scores.py`** - Converts lines ↔ scores

---

## Next Steps

1. **GET ODDS API KEY** (critical!)
2. Run `fetch_current_market_lines.py`
3. Verify market lines are correct
4. Run `precompute_edge_hunt_signals.py`
5. Restart Flask
6. Test with Playwright to verify UI

**Without real market lines, the entire system is comparing the model to itself, which is useless for betting.**

