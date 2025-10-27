# Feature Validation Strategy: How to Know If New Data Helps

## The Problem
Adding features without validation can:
1. **Add noise** - random correlations that don't generalize
2. **Overfit** - model memorizes training data, fails on new games
3. **Dilute signal** - good features get drowned out by bad ones
4. **Increase complexity** - more data to maintain, slower predictions

## The Solution: Rigorous Backtesting

For each proposed feature, we need to:
1. **Add it to the model**
2. **Backtest on historical data** (Weeks 1-8)
3. **Compare performance metrics** vs baseline
4. **Check if improvement is statistically significant**
5. **Only keep it if it clearly helps**

## Proposed Features - Validation Plan

### 1. Weather (ESPN vs Open-Meteo)
**What we'd do:**
- Replace Open-Meteo with ESPN weather data
- Keep same wind penalty logic

**How to validate:**
- Backtest Weeks 1-8 with ESPN weather
- Compare to current model with Open-Meteo
- Metrics: Winner accuracy, spread error (MAE), bet accuracy

**Expected outcome:**
- Likely **NEUTRAL** - both sources are good
- ESPN might be slightly more accurate for game-time conditions
- **Verdict: LOW PRIORITY** - not worth the effort to switch

**Risk of harm:** Very low (weather is weather)

---

### 2. Home/Away Splits
**What we'd do:**
- Calculate separate EPA/success rate for home vs away games
- Add features: `away_OFF_EPA_road`, `home_OFF_EPA_home`, etc.
- Model would learn that some teams (e.g., SEA) are much better at home

**How to validate:**
- Add home/away split features to model
- Backtest Weeks 1-8
- Compare winner accuracy and spread error

**Expected outcome:**
- Likely **POSITIVE** - home field advantage varies by team
- Should improve predictions for teams with big home/road splits
- Example: SEA is +5 points better at home, model should learn this

**Risk of harm:** Medium - could overfit if sample size is small

**Validation test:**
```python
# Before: away_OFF_EPA = 0.10
# After:  away_OFF_EPA_road = 0.05, away_OFF_EPA_home = 0.15
# Model learns: This team is worse on the road
```

**Statistical test:**
- Is the improvement in MAE > 0.5 points per game?
- Is winner accuracy improvement > 2%?
- If YES to either → keep it

---

### 3. Last 5 Games Momentum
**What we'd do:**
- Calculate win/loss record in last 5 games
- Add feature: `away_last5_wins` (0-5), `home_last5_wins` (0-5)
- Or: `away_momentum` = (recent_perf - season_avg)

**How to validate:**
- Add momentum feature
- Backtest Weeks 1-8
- Check if teams on hot streaks outperform predictions

**Expected outcome:**
- Likely **NEUTRAL or SLIGHTLY POSITIVE**
- Momentum is real, but we already capture it with `recent_weight=0.95`
- Might add 1-2% to winner accuracy

**Risk of harm:** Medium - "hot hand fallacy" is real in sports

**Validation test:**
```python
# Test: Do teams with 4-1 last 5 outperform teams with 1-4 last 5?
# If yes by >3 points/game → add feature
# If no → skip it (already captured by recency weight)
```

**Statistical test:**
- Split games into "hot" (4-5 wins in last 5) vs "cold" (0-1 wins)
- Compare actual vs predicted margin
- If hot teams beat predictions by >2 points → keep it

---

### 4. Grass vs Turf
**What we'd do:**
- Add binary feature: `is_turf` (0 or 1)
- Add interaction: `away_OFF_EPA * is_turf` (some offenses better on turf)

**How to validate:**
- Add turf feature
- Backtest Weeks 1-8
- Check if predictions improve for turf games

**Expected outcome:**
- Likely **NEUTRAL** - modern turf is very similar to grass
- Might matter for specific players (speed guys on turf)
- But team-level effect is probably small

**Risk of harm:** Medium - could be pure noise

**Validation test:**
```python
# Test: Is there a difference in scoring on grass vs turf?
# If turf games average >2 more points → add feature
# If difference < 1 point → skip it (noise)
```

**Statistical test:**
- Compare actual scores: grass games vs turf games
- If no significant difference (p > 0.05) → skip it

---

### 5. Prime Time Games
**What we'd do:**
- Add binary feature: `is_primetime` (SNF, MNF, TNF)
- Add interaction: `away_OFF_EPA * is_primetime` (some teams choke)

**How to validate:**
- Add primetime feature
- Backtest Weeks 1-8
- Check if certain teams underperform in primetime

**Expected outcome:**
- Likely **SLIGHTLY POSITIVE** - primetime effect is real
- Some teams (e.g., DAL) historically underperform in primetime
- But effect is small (~1-2 points)

**Risk of harm:** Medium - sample size is small (only 3 primetime games/week)

**Validation test:**
```python
# Test: Do teams score differently in primetime vs early games?
# If primetime games are lower scoring by >3 points → add feature
# If difference < 1 point → skip it
```

**Statistical test:**
- Compare team performance: primetime vs non-primetime
- If certain teams consistently underperform (>5 points) → add team-specific penalty
- If no pattern → skip it

---

### 6. Attendance (Crowd Noise)
**What we'd do:**
- Add feature: `attendance_pct` (actual / capacity)
- Hypothesis: Higher attendance = more home field advantage

**How to validate:**
- Add attendance feature
- Backtest Weeks 1-8
- Check if high-attendance games favor home team more

**Expected outcome:**
- Likely **NEUTRAL** - attendance varies but effect is unclear
- Loud stadiums (SEA, KC) already have strong home field in data
- Attendance might be correlated with team quality (good teams = more fans)

**Risk of harm:** High - likely just noise or reverse causality

**Validation test:**
```python
# Test: Do home teams win more often when attendance > 90%?
# If yes by >5% → add feature
# If no → skip it (noise)
```

**Statistical test:**
- Compare home team performance: high attendance vs low attendance
- Control for team quality (good teams have high attendance)
- If no independent effect → skip it

---

### 7. ESPN Win Probability
**What we'd do:**
- Use ESPN's pre-game win probability as a feature
- Hypothesis: ESPN's model has information we don't

**How to validate:**
- Add ESPN win prob as feature
- Backtest Weeks 1-8
- Check if it improves predictions

**Expected outcome:**
- Likely **POSITIVE BUT POLLUTES MODEL**
- ESPN's model is good, so it would help
- BUT: Makes our model dependent on ESPN
- We want an independent model

**Risk of harm:** Very high - makes model less useful

**Validation test:**
```python
# Test: How accurate is ESPN's win probability?
# If ESPN is 70%+ accurate → it would help
# But we DON'T WANT to use it (not independent)
```

**Statistical test:**
- Compare ESPN predictions to actual outcomes
- Even if it helps → **DON'T USE IT** (defeats purpose of our model)

---

### 8. ATS Records (Against the Spread)
**What we'd do:**
- Add feature: `away_ats_record` (% of games they cover spread)
- Hypothesis: Teams that consistently cover are undervalued

**How to validate:**
- Add ATS record feature
- Backtest Weeks 1-8
- Check if high-ATS teams beat predictions

**Expected outcome:**
- Likely **NEUTRAL** - ATS record is mostly random
- "Hot" ATS teams regress to mean quickly
- Might add noise

**Risk of harm:** High - ATS records are noisy and mean-reverting

**Validation test:**
```python
# Test: Do teams with 70%+ ATS records continue to cover?
# If yes → add feature
# If no (likely) → skip it (gambler's fallacy)
```

**Statistical test:**
- Split season in half: first 4 weeks vs last 4 weeks
- Check if high-ATS teams in first half stay high in second half
- If correlation < 0.3 → skip it (not predictive)

---

## The Validation Process

### Step 1: Baseline Performance
Run current model on Weeks 1-8:
```bash
python3 backtest_model_v2.py --weeks 1-8
```

Record:
- Winner accuracy: X%
- Spread MAE: Y points
- Bet accuracy (EV > 2%): Z%

### Step 2: Add Feature
Add new feature to model:
```python
# In features.py
out["home_away_split"] = calculate_home_away_split(df)
```

### Step 3: Backtest with Feature
```bash
python3 backtest_model_v2.py --weeks 1-8 --feature home_away_split
```

Record:
- Winner accuracy: X'%
- Spread MAE: Y' points
- Bet accuracy: Z'%

### Step 4: Statistical Significance Test
```python
# Is improvement real or random?
improvement = (X' - X)
if improvement > 2% and p_value < 0.05:
    print("Feature is significant! Keep it.")
else:
    print("Feature is noise. Skip it.")
```

### Step 5: Out-of-Sample Test
- Train on Weeks 1-7
- Test on Week 8
- If Week 8 performance also improves → feature is real
- If Week 8 performance degrades → feature is overfitting

---

## Decision Framework

| Feature | Expected Value | Risk of Harm | Validation Effort | Recommendation |
|---------|---------------|--------------|-------------------|----------------|
| ESPN Weather | Low | Very Low | Low | Skip (not worth effort) |
| Home/Away Splits | Medium | Medium | Medium | **TEST IT** |
| Last 5 Momentum | Low-Medium | Medium | Low | **TEST IT** |
| Grass vs Turf | Low | Medium | Low | Skip (likely noise) |
| Prime Time | Low | Medium | Medium | Skip (small sample) |
| Attendance | Very Low | High | Medium | Skip (likely noise) |
| ESPN Win Prob | High | Very High | Low | **NEVER USE** (pollutes model) |
| ATS Records | Very Low | High | Low | Skip (gambler's fallacy) |

---

## Final Recommendation

### Test These Two:
1. **Home/Away Splits** - Most likely to help, reasonable risk
2. **Last 5 Momentum** - Easy to test, might add small edge

### Skip Everything Else:
- **Weather**: Not worth switching
- **Grass/Turf**: Likely noise
- **Prime Time**: Small sample, unclear effect
- **Attendance**: Reverse causality problem
- **ESPN Win Prob**: Defeats purpose of independent model
- **ATS Records**: Gambler's fallacy

### How to Test:
```bash
# 1. Create backtest script that adds feature
# 2. Run on Weeks 1-8
# 3. Compare to baseline
# 4. If improvement > 2% winner accuracy OR > 0.5 MAE → keep it
# 5. Otherwise → discard it
```

---

## The Golden Rule

**"In God we trust, all others bring data."**

Don't add a feature unless:
1. You have a clear hypothesis for WHY it should help
2. You've tested it on historical data
3. The improvement is statistically significant
4. It doesn't make the model dependent on external sources

Otherwise, you're just adding noise and making the model worse.

