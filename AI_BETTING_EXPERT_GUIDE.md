# 🤖 AI Betting Expert Feature Guide

## Overview

The AI Betting Expert uses ChatGPT-4 to analyze your model's predictions and identify the best betting opportunities each week.

## Setup

### 1. Get an OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `sk-...`)

### 2. Set the API Key

**Option A: Environment Variable (Recommended)**
```bash
export OPENAI_API_KEY='sk-your-key-here'
```

**Option B: Add to your shell profile** (`~/.zshrc` or `~/.bash_profile`):
```bash
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Restart Flask
```bash
cd /Users/steveridder/Git/Football
pkill -f flask
FLASK_APP=app_flask.py flask run --host=0.0.0.0 --port=9876
```

## How to Use

### Step 1: Generate Predictions
1. Go to http://localhost:9876/
2. Click "Regenerate Predictions" or "Generate All" under Simulator Predictions
3. Wait for predictions to complete

### Step 2: Generate AI Analysis
1. On the home page, you'll see a new "AI Betting Expert" section (below the 4 summary boxes)
2. Select the week you want to analyze
3. Click **"Generate AI Picks"**
4. Wait 30-60 seconds while ChatGPT analyzes the data
5. The section will populate with 4 tables:
   - **Against-the-Spread (ATS) Plays** - Best spread bets
   - **Totals (Over/Under)** - Best O/U bets
   - **Moneyline Value Plays** - Best ML bets
   - **Top Picks of the Week** - Final recommendations

## What the AI Analyzes

The AI expert looks for:

1. **Edge Size**: Difference between your model line and market line
   - 10+ points = 100% confidence (BEST BETS)
   - 5-9 points = 70-90% confidence (strong)
   - 3-4 points = 53-60% confidence (solid)
   - <3 points = Pass (no edge)

2. **Mispriced Lines**: Games where the market is significantly wrong

3. **Risk/Reward**: Balance between confidence and potential value

## Better Prompt Formula

The AI uses this structured analysis:

```
1. Load all game predictions with market vs. model lines
2. Calculate edge size for each game
3. Rank by confidence and edge size
4. Filter out games with <3 point edge
5. Identify top 5-7 plays for each bet type
6. Provide final recommendations with reasoning
```

This is MUCH better than just copying raw data because:
- ✅ Structured analysis with clear criteria
- ✅ Focus on edge size and confidence
- ✅ Filters out low-value plays
- ✅ Provides reasoning for picks

## File Locations

- AI picks module: `/edge_hunt/chatgpt_picks.py`
- Saved picks: `/artifacts/chatgpt_picks_week{N}.json`
- API endpoints: `/api/generate-ai-picks` and `/api/ai-picks`

## Cost Estimate

- ~$0.05-0.15 per week analysis (ChatGPT-4 Turbo)
- Saved results are cached, so regenerating is free

## Troubleshooting

**Error: "No OpenAI API key found"**
- Set the `OPENAI_API_KEY` environment variable
- Restart Flask

**Error: "No predictions found for week X"**
- Run "Regenerate Predictions" first
- Check that `artifacts/simulator_predictions.csv` exists

**Error: "openai module not found"**
- Run: `python3 -m pip install openai`

**AI section not showing**
- Generate picks first by clicking the button
- Refresh the page

## Future Enhancements

- [ ] Auto-generate picks after each prediction run
- [ ] Email/SMS alerts for new picks
- [ ] Historical performance tracking of AI picks
- [ ] Integration with live odds to show current value
- [ ] Parlays/teasers suggestions

## How It's Better Than Manual Analysis

**Before (Manual):**
- Copy all game data
- Paste into ChatGPT
- Get unstructured response
- Manually format tables
- Time: 5-10 minutes

**After (Automated):**
- Click one button
- AI analyzes with optimized prompt
- Auto-formatted tables
- Cached results
- Time: 30 seconds

**Win!** 🎯

