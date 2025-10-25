# Weekly Bet Update Guide

## How to Update Your Bets Each Week

### Quick Start
```bash
cd /Users/steveridder/Git/Football
source .venv/bin/activate
python3 update_bets_weekly.py
```

### What It Does
1. ✅ Opens BetOnline in a browser
2. ✅ Waits 30 seconds for you to log in and navigate to "Bet History"
3. ✅ Automatically extracts ALL your bets with current statuses
4. ✅ Updates Won/Lost/Pending for all bets
5. ✅ Fetches any new bets you placed
6. ✅ Calculates your updated P&L
7. ✅ Saves everything to `artifacts/betonline_bets.json`

### Step-by-Step

1. **Run the script:**
   ```bash
   python3 update_bets_weekly.py
   ```

2. **Browser opens automatically** - you'll see:
   ```
   ⏳ Waiting 30 seconds for you to log in and navigate to bet history...
   ```

3. **In the browser:**
   - Log in to BetOnline
   - Click "My Account" → "Bet History"
   - Wait for your bets to load on screen
   - The script will auto-extract after 30 seconds

4. **Script completes:**
   ```
   ✅ Extracted 352 bets from BetOnline
   📊 Summary:
      Total bets: 352
      Pending: 145 ($345.00)
      Won: 5 (+$125.50)
      Lost: 202 (-$202.00)
      Total P/L: $-76.50
   
   📈 Changes since last update:
      New bets: +15
      Status changes: 12 bets settled
      P/L change: $-15.50
   
   ✅ Saved to artifacts/betonline_bets.json
   ```

5. **Refresh your dashboard:**
   - Go to http://localhost:9876/bets
   - You'll see all updated bets with correct statuses!

### What Gets Updated

- ✅ **Bet Statuses**: Pending → Won or Lost
- ✅ **New Bets**: Any bets placed since last update
- ✅ **P&L**: Real-time profit/loss calculation
- ✅ **Win Rate**: Updated win percentage
- ✅ **Full Details**: All parlay legs and descriptions

### Troubleshooting

**Script says "Extracted 0 bets":**
- Make sure you're on the "Bet History" page
- Try scrolling down to load more bets
- Check that bets are visible on screen

**Browser closes too fast:**
- Edit `update_bets_weekly.py`
- Change `time.sleep(30)` to `time.sleep(60)` for more time

**Want to run it manually:**
- After the browser opens, you can take as long as you need
- Press Ctrl+C to cancel if needed
- Just re-run the script

### Frequency

**Recommended:** Run this script once per week after games finish

**Best Time:** Monday morning after Sunday/Monday Night Football

### Data Safety

- ✅ Old data is backed up before updating
- ✅ Script never deletes bets, only updates statuses
- ✅ All data stored locally in `artifacts/betonline_bets.json`

---

## Quick Commands

```bash
# Update bets
python3 update_bets_weekly.py

# View bets in dashboard
open http://localhost:9876/bets

# Check current data
cat artifacts/betonline_bets.json | grep -A 5 summary
```

---

**That's it!** Your bets will always be up-to-date with the latest statuses and P&L! 🎰

