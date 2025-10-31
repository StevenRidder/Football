# nflfastR Play-by-Play Simulator - Status

## ✅ Completed (Phase 1)

### Data Extraction
- ✅ QB pressure splits (clean vs pressure performance)
  - 64,306 dropbacks analyzed
  - Clean: 61.5% completion, +0.11 EPA
  - Pressure: 21.9% completion, -0.98 EPA
  - **-1.09 EPA swing from pressure!**

- ✅ Play-calling tendencies by situation
  - 105,681 offensive plays
  - Down 14+: 68.5% pass rate
  - Up 14+: 32.6% pass rate

- ✅ Drive probabilities by field position
  - 18,657 drives analyzed
  - 7 field position buckets

### Simulator Architecture
- ✅ `GameState` - Tracks game situation (down, distance, score, time)
- ✅ `TeamProfile` - Loads team data (EPA, QB stats, play-calling)
- ✅ `PlaySimulator` - Simulates individual plays (pass/run)
- ✅ `GameSimulator` - Orchestrates full game play-by-play

### Initial Test
- ✅ Simulator runs successfully
- ✅ Monte Carlo works (100 sims in ~1 second)
- ⚠️  **Scores too low (17 pts avg vs ~45 expected)**

---

## 🔧 Needs Calibration

### Issue: Scoring Too Low
Current avg total: **17.4 points** (should be ~45)

**Root causes:**
1. Drive simulation ending too early
2. Not enough plays per drive
3. Scoring probabilities too conservative

**Fixes needed:**
1. Increase base scoring probability in `simulate_pass_play()`
2. Adjust yards gained distributions
3. Calibrate against actual 2024 game scores

---

## 📋 Next Steps

### Immediate (Calibration)
1. Run 10 games, track plays per drive
2. Compare to nflfastR actual (6.6 plays/drive)
3. Adjust scoring probabilities to match NFL reality
4. Target: Avg total ~45 points

### Phase 2 (Backtest)
1. Run on 2024 full season (200+ games)
2. Compare spread MAE to:
   - Market baseline (~9.5 pts)
   - EPA-only Monte Carlo (~11.7 pts)
3. Check ATS accuracy (target >52.4%)

### Phase 3 (Production)
1. Generate Week 10 predictions
2. Compare to market lines
3. Identify value bets (>1.5pt edge)

---

## 🎯 Success Criteria

Per strategy doc:
- **Spread MAE < 10 points** (beat market)
- **ATS accuracy > 55%** (profitable)
- **Tail prediction correlation > 0.3** (blowouts, unders)

---

## 📊 Key Insights So Far

1. **QB pressure matters MASSIVELY**
   - -1.09 EPA swing
   - 44.9% sack rate under pressure
   - This is the real signal!

2. **Game script matters**
   - Pass rate varies 32% → 68% by score
   - 2-minute drill: 61% pass rate

3. **Simulator architecture is solid**
   - Play-by-play logic works
   - Game flow tracking works
   - Just needs scoring calibration

---

## 🚀 What Makes This Different

**vs Ridge/XGBoost (old approach):**
- Linear models can't capture compounding effects
- No game flow modeling
- No QB-specific pressure performance

**vs Simple Monte Carlo (current production):**
- Play-by-play (not drive-level)
- Situational play-calling
- QB pressure splits
- Game script adjustments

**The edge:**
- Market prices team averages
- We model **variance and game flow**
- Compounding effects of pressure → turnovers → script changes

---

## 📁 File Structure

```
simulation_engine/nflfastR_simulator/
├── data/nflfastR/
│   ├── qb_pressure_splits_weekly.csv
│   ├── qb_pressure_splits_season.csv
│   ├── playcalling_tendencies_weekly.csv
│   ├── playcalling_tendencies_season.csv
│   ├── drive_probabilities_weekly.csv
│   ├── drive_probabilities_season.csv
│   ├── drive_probabilities_league.csv
│   └── team_pace.csv
├── preprocessing/
│   ├── extract_qb_splits.py ✅
│   ├── extract_playcalling.py ✅
│   ├── extract_drive_probs.py ✅
│   └── RUN_ALL.sh
├── simulator/
│   ├── game_state.py ✅
│   ├── team_profile.py ✅
│   ├── play_simulator.py ✅ (needs calibration)
│   ├── game_simulator.py ✅
│   └── test_simulator.py ✅
├── backtest/ (TODO)
│   └── run_backtest_2024.py
└── production/ (TODO)
    └── generate_predictions.py
```

---

**Next: Calibrate scoring probabilities to match NFL reality (45 pts avg).**

