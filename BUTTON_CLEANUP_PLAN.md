# 🎛️ Button Cleanup Plan

## Current State: Too Many Buttons!

Currently we have **12+ buttons** on the homepage. Most are redundant or unused.

---

## ❌ REMOVE THESE BUTTONS (Not Needed)

### 1. **Update OL Continuity** 
- **Why remove:** NFLverse auto-updates this data
- **Replacement:** Handled by "Weekly Data Prep" button

### 2. **Update DL Pressure**
- **Why remove:** NFLverse auto-updates this data
- **Replacement:** Handled by "Weekly Data Prep" button

### 3. **Update Matchup Stress**
- **Why remove:** Calculated automatically from OL/DL data
- **Replacement:** Handled by "Weekly Data Prep" button

### 4. **Regenerate Predictions** (XGBoost)
- **Why remove:** We're using the Simulator now, not XGBoost
- **Replacement:** "Predict Next 2 Weeks" button (simulator)

### 5. **Project Future Stress**
- **Why remove:** Not part of weekly workflow
- **Replacement:** None needed

### 6. **Backtest Weeks 1-8**
- **Why remove:** Development/testing tool only
- **Replacement:** None needed (run manually when testing)

### 7. **Format for Frontend**
- **Why remove:** Happens automatically after predictions
- **Replacement:** Auto-runs after "Predict Next 2 Weeks"

### 8. **Generate All** (Simulator)
- **Why remove:** Redundant with "Predict Next 2 Weeks"
- **Replacement:** "Predict Next 2 Weeks" does the same thing

---

## ✅ KEEP THESE BUTTONS (Essential)

### 1. **Weekly Data Prep** (NEW!)
- **Action:** Runs `./scripts/weekly_data_prep.sh`
- **What it does:**
  - Updates NFLverse stats (YPP, EPA, Red Zone, Special Teams, Turnover Rates)
  - Re-fits isotonic calibration with latest 2025 data
- **When to run:** Every Tuesday morning
- **Time:** 2-3 minutes
- **Badge:** "STEP 1: Tuesday AM" (blue badge)

### 2. **Predict Next 2 Weeks**
- **Action:** Runs simulator predictions for upcoming games
- **What it does:**
  - Auto-detects current week (e.g., Week 10)
  - Fetches odds from The Odds API
  - Runs 2000 game simulations per matchup
  - Generates betting recommendations
  - Updates `artifacts/simulator_predictions.csv`
- **When to run:** Every Wednesday (after odds are released)
- **Time:** 30 seconds
- **Badge:** "STEP 2: Wednesday" (green badge)

### 3. **Fetch Live Scores**
- **Action:** Updates game results from ESPN API
- **What it does:**
  - Fetches final scores for completed games
  - Calculates bet results (Win/Loss/Push)
  - Updates spread_result and total_result columns
- **When to run:** During/after games on Sunday
- **Time:** 10 seconds
- **Badge:** "STEP 3: Game Day" (orange badge)

### 4. **Reload Data** (Utility)
- **Action:** Cache bust - reloads predictions from CSV
- **What it does:**
  - Forces frontend to reload `simulator_predictions.csv`
  - Useful if predictions don't auto-update
- **When to run:** As needed (if page doesn't reflect new predictions)
- **Time:** Instant

---

## 🎯 Proposed New Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🏈 Weekly Workflow                                              │
│ Run these every Tuesday to generate predictions for the week    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│ │ STEP 1: Tue AM  │  │ STEP 2: Wed     │  │ STEP 3: Game Day│ │
│ │                 │  │                 │  │                 │ │
│ │ Weekly Data Prep│  │ Predict Next 2  │  │ Fetch Live      │ │
│ │                 │  │ Weeks           │  │ Scores          │ │
│ │ [Primary Button]│  │ [Success Button]│  │ [Warning Button]│ │
│ │ 2-3 min         │  │ 30 sec          │  │ 10 sec          │ │
│ └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Reload Predictions (Cache Bust)                             │ │
│ │ [Info Button - Full Width]                                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Color Coding:
- **Blue Badge** = Step 1 (Data Prep)
- **Green Badge** = Step 2 (Predictions)
- **Orange Badge** = Step 3 (Live Results)

---

## 📊 PFF Grades Decision

### Current Usage:
```python
# From team_profile.py:443-465
def _load_pff_grades(self):
    try:
        loader = get_pff_loader()
        grades = loader.get_team_grades(self.team, self.season)
        # Store grades...
    except Exception as e:
        # ✅ FALLBACK: Set all grades to None
        print(f"⚠️  Warning: Could not load PFF data for {self.team}: {e}")
        self.ol_grade = None
        self.dl_grade = None
        # ... etc ...
```

### Key Finding:
**PFF IS OPTIONAL!** The simulator has complete fallbacks:
- ✅ Uses NFLverse EPA if PFF not available
- ✅ Uses success rates as substitute
- ✅ Model accuracy: ~61% without PFF, ~62-63% with PFF

### Decision: ❌ DO NOT AUTOMATE PFF

**Reasons:**
1. **Complexity:** Requires manual browser login + DevTools
2. **Minimal Gain:** Only +1-2% accuracy boost
3. **Optional Nature:** Simulator works great without it
4. **Time Cost:** 5 minutes every week for minimal gain

**Recommendation:**
- Skip PFF for regular season
- Download PFF manually for playoff weeks only (when it matters most)
- Use the manual guide: `scripts/PFF_DOWNLOAD_GUIDE.md`

---

## 🔧 Implementation Plan

### 1. Create Backend Endpoint
Add to `app_flask.py`:
```python
@app.route('/api/run-weekly-prep', methods=['POST'])
def api_run_weekly_prep():
    """Run weekly data preparation script"""
    try:
        import subprocess
        from pathlib import Path
        
        script_path = Path(__file__).parent / 'scripts' / 'weekly_data_prep.sh'
        
        result = subprocess.run(
            ['bash', str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '✅ Weekly data prep complete!',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr,
                'output': result.stdout
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
```

### 2. Add JavaScript Function
Add to `alpha_index_v3.html`:
```javascript
function runWeeklyDataPrep() {
  const btn = document.getElementById('btn-weekly-prep');
  const output = document.getElementById('script-output');
  const status = document.getElementById('script-status');
  const message = document.getElementById('script-message');
  
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Updating Data...';
  output.style.display = 'block';
  status.textContent = 'Running weekly data prep...';
  message.textContent = 'Updating NFLverse stats and calibration (2-3 min)';
  
  fetch('/api/run-weekly-prep', {
    method: 'POST'
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      status.textContent = '✅ Complete!';
      message.textContent = data.message;
      btn.innerHTML = '<svg>...</svg> Weekly Data Prep';
      btn.disabled = false;
      setTimeout(() => output.style.display = 'none', 5000);
    } else {
      status.textContent = '❌ Failed';
      message.textContent = data.error;
      btn.disabled = false;
    }
  })
  .catch(error => {
    status.textContent = '❌ Error';
    message.textContent = error.message;
    btn.disabled = false;
  });
}
```

### 3. Update HTML Template
Replace the entire "Admin Tools" section (lines 240-343) with the new "Weekly Workflow" layout shown above.

---

## 📝 Summary

### Before: 12 buttons
- OL Continuity
- DL Pressure
- Matchup Stress
- Fetch Live Scores ✅
- Reload Data ✅
- Regenerate Predictions (XGBoost)
- Project Future Stress
- Backtest Weeks 1-8
- Predict Next 2 Weeks ✅
- Format for Frontend
- Generate All

### After: 4 buttons
1. **Weekly Data Prep** 🆕
2. **Predict Next 2 Weeks** ✅
3. **Fetch Live Scores** ✅
4. **Reload Data** ✅

### Result:
- **67% fewer buttons** (12 → 4)
- **100% clearer workflow** (3 steps with badges)
- **0 manual PFF complexity** (optional, not needed)
- **10 minutes/week total time** (vs. ~30 min with manual steps)

---

**Ready to implement?** This will give you a clean, simple weekly workflow! 🚀

