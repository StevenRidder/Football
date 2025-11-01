# Evergreen Data & Prediction Strategy

## Current State Analysis

### ✅ What's Already Automated/Easy

1. **Game Results (ESPN API)**
   - Frontend has "Fetch Live Scores" button
   - Auto-fetches final scores for Weeks 1-10
   - Updates `simulator_predictions.csv` automatically
   - **Status:** ✅ Fully automated

2. **nflfastR Data**
   - Auto-updates via `nfl_data_py` library
   - Play-by-play data refreshes automatically
   - **Status:** ✅ Automated (library handles it)

### ⚠️ What Requires Manual Steps

3. **PFF Grades (Weekly)**
   - Script: `scripts/download_pff_qb_data.py`
   - **Current:** Manual run required each week
   - **Need:** Weekly QB grades, OL/DL grades, coverage grades
   - **Status:** ⚠️ Manual (requires PFF API key & weekly run)

4. **Odds Data (Closing Lines)**
   - **Source:** The Odds API or similar
   - **Current:** Manually updated in test files
   - **Timing:** Lines typically close ~10 minutes before kickoff
   - **Week 10 Odds:** Usually available Tuesday/Wednesday before the games
   - **Status:** ⚠️ Manual (not integrated)

5. **Isotonic Calibration Re-fitting**
   - Script: `fit_isotonic_2025_only.py`
   - **Current:** Manual run after each week
   - **Should Run:** After Week 8, 9, 10, etc. as more data accumulates
   - **Status:** ⚠️ Manual

6. **Weekly QB Stats Extraction**
   - Script: `preprocessing/extract_weekly_qb_stats.py`
   - **Current:** Manual run
   - **Depends on:** nflfastR data (auto-updated)
   - **Status:** ⚠️ Manual

## Weekly Workflow (What Should Happen)

### Tuesday/Wednesday (Before Week N)
1. ✅ **Week N odds release** (typically Tuesday afternoon)
   - Need to fetch from Odds API
   - Store in database or CSV

2. ⚠️ **Download PFF grades for Week N-1** (completed games)
   ```bash
   python3 scripts/download_pff_qb_data.py
   ```

3. ⚠️ **Extract QB stats for Week N-1**
   ```bash
   python3 preprocessing/extract_weekly_qb_stats.py
   ```

4. ⚠️ **Re-fit isotonic calibration** (with new Week N-1 data)
   ```bash
   python3 fit_isotonic_2025_only.py
   ```

5. ⚠️ **Generate Week N predictions**
   ```bash
   ./scripts/update_frontend_predictions.sh
   ```

### During Week N (Games in Progress)
1. ✅ **Fetch live scores** (frontend button or cron job)
   - Updates as games complete
   - Auto-calculates bet results

### Monday After Week N
1. ⚠️ **Verify all final scores** loaded
2. ⚠️ **Download PFF grades** for Week N
3. ⚠️ **Prepare for next week's cycle**

## Proposed Automation Strategy

### Priority 1: Automate Weekly Data Pipeline
Create `scripts/weekly_data_update.sh`:
```bash
#!/bin/bash
# Run every Tuesday morning at 6am (before odds release)

cd /path/to/Football

# 1. Extract latest QB stats from nflfastR (auto-updated)
python3 simulation_engine/nflfastR_simulator/preprocessing/extract_weekly_qb_stats.py

# 2. Download PFF grades (requires API key)
python3 simulation_engine/nflfastR_simulator/scripts/download_pff_qb_data.py

# 3. Re-fit isotonic calibration with all available 2025 data
python3 simulation_engine/nflfastR_simulator/fit_isotonic_2025_only.py

# 4. Fetch latest odds (TODO: implement odds API integration)
# python3 scripts/fetch_weekly_odds.py

# 5. Generate predictions for upcoming week
cd simulation_engine/nflfastR_simulator
./scripts/update_frontend_predictions.sh

# 6. Restart Flask app to reload data
pkill -f "python3 app_flask.py"
cd /path/to/Football
nohup python3 app_flask.py > flask.log 2>&1 &

echo "✅ Weekly update complete!"
```

### Priority 2: Odds API Integration
- **Provider:** The Odds API (oddsapi.io) or similar
- **Cost:** ~$25-50/month for historical + live lines
- **Features needed:**
  - Fetch opening lines (Monday/Tuesday)
  - Fetch closing lines (game time)
  - Store in CSV or database
  - Auto-populate prediction scripts

### Priority 3: Automated Isotonic Refitting
- Run `fit_isotonic_2025_only.py` after each completed week
- Monitors: As more 2025 data accumulates, calibration improves
- Alert if calibration quality degrades

## Implementation Checklist

- [ ] Create `weekly_data_update.sh` automation script
- [ ] Set up cron job for Tuesday 6am runs
- [ ] Integrate Odds API for line fetching
- [ ] Add monitoring/alerting for failed data pulls
- [ ] Create data validation checks (missing PFF, odds, etc.)
- [ ] Add logging for each step of pipeline
- [ ] Build dashboard showing "last updated" timestamps
- [ ] Document manual override procedures

## Current Gaps to Fill

1. **Odds API Integration** - Biggest gap, currently manual
2. **PFF API Automation** - Need to verify API key works in cron
3. **Error Handling** - What if PFF API is down? Use fallbacks?
4. **Data Validation** - Verify all 32 teams have data before prediction
5. **Rollback Strategy** - If predictions fail, keep previous week's

## Timeline: Week 10 Predictions

**Week 10 Games:** Sunday, November 10, 2024

**Typical Schedule:**
- **Tuesday, Nov 5** (5 days before): Opening lines released
- **Wednesday-Saturday**: Lines move based on betting action
- **Sunday, Nov 10** (~10 min before each game): Lines close

**Our Workflow:**
1. **Tuesday AM**: Run `weekly_data_update.sh` (automated)
2. **Tuesday PM**: Fetch Week 10 odds (manual or automated if API integrated)
3. **Wednesday AM**: Generate Week 10 predictions with new odds
4. **Sunday**: Predictions go live on frontend

## Bottom Line

**Current State:** 70% manual, 30% automated  
**Target State:** 90% automated, 10% manual oversight  
**Key Missing Piece:** Odds API integration  
**Time to Full Automation:** 1-2 days of dev work


