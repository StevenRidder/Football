# 🏈 Weekly Prediction Workflow

Your complete guide to generating sharp NFL predictions every week.

---

## 📅 Weekly Schedule

### **Tuesday Morning** (6:00 AM - 9:00 AM)
**Goal:** Prepare fresh data for the upcoming week

#### Automated Step (2-3 minutes)
```bash
cd /Users/steveridder/Git/Football
./scripts/weekly_data_prep.sh
```

**This script automatically:**
1. ✅ Updates NFLverse stats (YPP, EPA, Red Zone, Special Teams, Turnover Rates)
2. ✅ Re-fits isotonic calibration with latest 2025 data

**Output:**
- Updated CSV files in `simulation_engine/nflfastR_simulator/data/nflfastR/`
- Updated calibration in `simulation_engine/nflfastR_simulator/artifacts/isotonic/`

---

### **Tuesday Afternoon** (Optional - 5 minutes)
**Goal:** Add elite QB performance data from PFF

#### Manual Step (Optional)
See: [`scripts/PFF_DOWNLOAD_GUIDE.md`](scripts/PFF_DOWNLOAD_GUIDE.md)

**Quick version:**
1. Login to https://premium.pff.com
2. Open DevTools > Network > Fetch/XHR
3. Navigate to QB grades page
4. Copy the API response JSON
5. Save to: `simulation_engine/nflfastR_simulator/data/pff_raw/pff_qb_2025_YYYYMMDD.json`

**Why optional?** Model works great without PFF. Use it for big games/playoffs.

---

### **Wednesday Morning** (10 seconds)
**Goal:** Generate predictions for upcoming week

#### Frontend Button
1. Open: http://localhost:9876
2. Click: **"Predict Next 2 Weeks"** button
3. Wait ~30 seconds for predictions to generate

**What happens automatically:**
- ✅ Detects current week (e.g., Week 10)
- ✅ Fetches odds from The Odds API
- ✅ Runs 2000 game simulations per matchup
- ✅ Generates betting recommendations
- ✅ Updates frontend with new predictions

**Output:**
- `artifacts/simulator_predictions.csv` (loaded by frontend)
- Predictions visible on homepage

---

### **Wednesday-Saturday** (Monitor)
**Goal:** Track line movement and adjust bets

#### Check for Line Changes
- Odds API provides real-time lines
- If lines move significantly, re-run predictions with updated odds

#### Re-run Predictions (if needed)
```bash
# If odds changed significantly
cd /Users/steveridder/Git/Football
# Click "Predict Next 2 Weeks" button again on frontend
```

---

### **Sunday** (Game Day)
**Goal:** Track live scores and bet results

#### Fetch Live Scores
1. Open: http://localhost:9876
2. Click: **"Fetch Latest Scores"** button
3. Predictions update with actual scores and bet results

**Automated Updates:**
- ✅ Fetches scores from ESPN API
- ✅ Calculates bet results (Win/Loss/Push)
- ✅ Updates spread_result and total_result columns

---

### **Monday** (Post-Week Review)
**Goal:** Analyze performance and prepare for next week

#### Review Performance
1. Go to: http://localhost:9876/performance
2. Review:
   - Weekly accuracy
   - ROI by bet type (spread/total)
   - High/medium/low conviction results
   - Line movement captures (CLV)

#### Verify Data Integrity
```bash
cd /Users/steveridder/Git/Football
# Check that all games have final scores
cat artifacts/simulator_predictions.csv | grep "Week 10"
```

---

## 🎯 Complete Week 10 Example

### **Tuesday, Nov 5** (Morning)
```bash
./scripts/weekly_data_prep.sh
```
**Output:** ✅ NFLverse data updated, calibration re-fit

### **Tuesday, Nov 5** (Afternoon - Optional)
- Login to PFF
- Copy QB grades JSON
- Save to `data/pff_raw/pff_qb_2025_20251105.json`

### **Wednesday, Nov 6** (Morning)
- Click **"Predict Next 2 Weeks"** on frontend
- Review recommendations for Week 10 and 11

### **Sunday, Nov 10** (Game Day)
- Click **"Fetch Latest Scores"** after each game window
- Monitor bet results in real-time

### **Monday, Nov 11** (Review)
- Go to `/performance` page
- Analyze Week 10 results
- Prepare for Week 11 cycle

---

## ⚡ Quick Reference Commands

### Full Weekly Prep (Automated)
```bash
./scripts/weekly_data_prep.sh
```

### PFF Download (Manual)
See: [`scripts/PFF_DOWNLOAD_GUIDE.md`](scripts/PFF_DOWNLOAD_GUIDE.md)

### Generate Predictions
Open: http://localhost:9876 → Click **"Predict Next 2 Weeks"**

### Fetch Live Scores
Open: http://localhost:9876 → Click **"Fetch Latest Scores"**

### Review Performance
Open: http://localhost:9876/performance

---

## 📊 Data Sources

| Data Type | Source | Update Frequency | Status |
|-----------|--------|------------------|--------|
| Play-by-play | nflfastR | Real-time | ✅ Auto |
| EPA/Success | nflfastR | Real-time | ✅ Auto |
| Team Stats | nflfastR | Weekly | ✅ Auto |
| Odds | The Odds API | Real-time | ✅ Auto |
| Live Scores | ESPN API | Real-time | ✅ Button |
| PFF Grades | PFF Premium | Weekly | ⚠️ Manual |
| Injuries | ESPN + OpenAI | Real-time | ✅ Auto |

---

## 🚨 Troubleshooting

### "No odds available for Week N"
- Check that week's games are scheduled
- Odds typically release Tuesday afternoon
- Re-run predictions Wednesday after odds are live

### "Predictions file not found"
- Ensure you ran `weekly_data_prep.sh`
- Click "Predict Next 2 Weeks" button
- Check: `artifacts/simulator_predictions.csv` exists

### "Isotonic calibration failed"
- Need at least 8 weeks of 2025 data
- Early season: Uses 2024 calibration as fallback
- Re-run `weekly_data_prep.sh` after Week 8

### "PFF data outdated"
- PFF grades release Monday/Tuesday
- Optional: Model works without PFF
- Download manually per `PFF_DOWNLOAD_GUIDE.md`

---

## 💡 Pro Tips

### Maximize Accuracy
1. Run `weekly_data_prep.sh` **every Tuesday** (fresh data)
2. Download PFF grades for **playoff weeks** (elite QB data)
3. Re-run predictions if odds move **>2 points** (line value)
4. Use **high conviction bets only** (proven edge)

### Minimize Time
1. Skip PFF downloads for regular season (optional)
2. Set Tuesday cron job for `weekly_data_prep.sh` (hands-free)
3. Use frontend buttons only (no manual scripts)

### Track Performance
1. Review `/performance` page every Monday
2. Note which bet types are profitable (spread vs. total)
3. Adjust conviction thresholds based on results

---

## 🎯 Time Breakdown

| Task | Time | Frequency |
|------|------|-----------|
| **Automated Prep** | 2-3 min | Weekly (Tue) |
| **PFF Download** | 5 min | Optional |
| **Generate Predictions** | 30 sec | Weekly (Wed) |
| **Fetch Live Scores** | 10 sec | Game Day |
| **Review Performance** | 5 min | Weekly (Mon) |
| **TOTAL** | ~10-15 min/week | |

---

## 📈 Success Metrics

### Model Performance Goals
- **Accuracy:** >55% on all bets (breakeven at 52.4%)
- **ROI:** >5% per bet (after juice)
- **High Conviction:** >60% accuracy
- **CLV:** Positive closing line value on >50% of bets

### Track Weekly
- Spread accuracy by conviction level
- Total accuracy (over vs. under)
- ROI by game type (divisional, primetime, etc.)
- Line movement capture (did we get good numbers?)

---

**Last Updated:** November 3, 2025  
**Model Version:** Simulator + XGBoost Ensemble  
**Current Season:** 2025 (Week 9)

