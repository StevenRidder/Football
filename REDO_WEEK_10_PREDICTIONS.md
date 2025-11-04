# How to Regenerate Week 10 Predictions

## ✅ Quick Answer

**Yes, it works from the front page!**

Just click the **"Predict Next 2 Weeks"** button on the homepage. It will automatically:
- Detect the current week (Week 10)
- Generate predictions for Week 10 + Week 11
- Update the frontend automatically

---

## 🖥️ Command Line Option

If you prefer to run it manually, you can specify just Week 10:

```bash
cd /Users/steveridder/Git/Football/simulation_engine/nflfastR_simulator
python3 scripts/generate_week9_10_predictions.py 10
```

This will generate predictions **only for Week 10**.

---

## 📋 What the Script Does

1. **Fetches odds** from The Odds API for Week 10
2. **Loads team profiles** with latest nflfastR data
3. **Runs 2000 simulations** per game
4. **Applies market centering** and calibration
5. **Generates betting recommendations** with conviction tiers
6. **Saves to**: `artifacts/simulator_predictions.csv`

---

## 🎯 Frontend Button

**Location**: Homepage → "Weekly Workflow" card → **"Predict Next 2 Weeks"** button

**What it does**:
- Automatically detects current week (Week 10)
- Generates predictions for Week 10 + Week 11
- Shows progress spinner
- Updates frontend when complete (~30-60 seconds)

**No manual steps needed!** Just click the button.

---

## 🔄 If You Want to Regenerate Just Week 10

The frontend button generates current week + next week. To regenerate **only Week 10**, use the command line:

```bash
cd /Users/steveridder/Git/Football/simulation_engine/nflfastR_simulator
python3 scripts/generate_week9_10_predictions.py 10
```

Then click **"Reload Predictions (Cache Bust)"** on the frontend to refresh the display.

---

## 📊 Output

Predictions are saved to:
- `artifacts/simulator_predictions.csv` (loaded by frontend)
- `artifacts/backtest_week9_10_predictions.csv` (detailed results)

The frontend automatically loads the latest predictions from `simulator_predictions.csv`.

---

## ✅ Summary

**Easiest way**: Click **"Predict Next 2 Weeks"** button on homepage
**Specific week**: Run command line with week number: `python3 scripts/generate_week9_10_predictions.py 10`

Both methods work perfectly with all the latest improvements! 🚀

