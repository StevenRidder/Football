# 🏈 PFF QB Grades Download Guide

## Overview
PFF (Pro Football Focus) grades are **optional** but provide elite-level QB performance data including:
- Weekly QB grades
- Pass blocking grades (OL)
- Coverage grades (Secondary)
- Depth chart information
- Injury status

**Status:** ⚠️ Manual process (requires PFF Premium subscription)

---

## When to Download

**Timing:** Every **Tuesday** after the previous week's games are graded by PFF (usually available by Tuesday morning)

**Example for Week 10:**
- Week 9 games complete: Sunday, Nov 3
- PFF grades published: Monday/Tuesday, Nov 4-5
- **Download:** Tuesday, Nov 5
- **Generate predictions:** Wednesday, Nov 6

---

## Step-by-Step Process

### Step 1: Log into PFF Premium
1. Open Chrome
2. Go to https://premium.pff.com
3. Log in with your PFF account
4. Navigate to: **Players** > **Grades** > **QB**

### Step 2: Open Developer Tools
1. Press `F12` or `Cmd+Option+I` (Mac)
2. Go to **Network** tab
3. Click **"Fetch/XHR"** filter to show only API calls

### Step 3: Trigger the Data Request
1. On the PFF page, change filters:
   - **Season:** 2025
   - **Weeks:** 1-10 (or current week range)
   - **Position:** QB
2. Click **"Apply"** or refresh the page
3. In DevTools Network tab, look for requests like:
   - `/api/v1/players/grades`
   - `/api/v1/facet/summary`
   - `/players?position=QB`

### Step 4: Copy the Response
1. **Right-click** on the API request in Network tab
2. Click **"Copy"** > **"Copy Response"**
3. Paste into a text editor

### Step 5: Save the Data
Save the JSON response as:
```
simulation_engine/nflfastR_simulator/data/pff_raw/pff_qb_2025_YYYYMMDD.json
```

**Example filename:** `pff_qb_2025_20251105.json`

### Step 6: Extract Starter Information
Run the parser script:
```bash
cd simulation_engine/nflfastR_simulator
python scripts/parse_pff_json.py data/pff_raw/pff_qb_2025_20251105.json
```

This creates: `data/pff/projected_starters_2025.csv`

---

## Alternative: Use the Interactive Script

We have a helper script that prompts you through the process:

```bash
cd simulation_engine/nflfastR_simulator
python scripts/download_pff_qb_data.py
```

**It will:**
1. Ask you to paste your PFF session cookie
2. Attempt to fetch data from PFF API
3. Save raw JSON files automatically

**Note:** Session cookies expire frequently, so you may need to re-copy them each week.

---

## What If I Skip PFF?

**The model works fine without PFF!** It uses:
- ✅ NFLverse EPA and success rates
- ✅ ESPN injury reports (via OpenAI)
- ✅ Historical performance data

**PFF just adds:** Slightly more precise QB performance grading

**Recommendation:** Download PFF for playoff weeks and big games, skip for regular season if pressed for time.

---

## Troubleshooting

### "401 Unauthorized" Error
- Your session cookie expired
- Re-login to PFF and copy a fresh cookie

### "No data found" Error
- Week hasn't been graded yet (check PFF website)
- API endpoint changed (check DevTools Network tab for new URLs)

### "Rate limited" Error
- PFF detected automated requests
- Wait 5 minutes and try again
- Use manual copy/paste method instead

---

## Summary

**Time Required:** 5 minutes  
**Frequency:** Once per week (Tuesday)  
**Priority:** Optional (model works without it)  
**Benefit:** +1-2% accuracy on QB-dependent games

---

**Updated:** November 2025

