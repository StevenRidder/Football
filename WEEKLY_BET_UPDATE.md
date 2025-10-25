# Weekly Bet Update Guide

## Quick Start

Every week, run this simple command to update your bets:

```bash
cd /Users/steveridder/Git/Football
python3 fetch_bets_from_browser.py
```

## What It Does

The script will:

1. 🌐 **Open a browser** to BetOnline
2. 🔐 **Wait for you to log in** (if needed)
3. 📊 **Extract all your bets** automatically
4. 💾 **Save them** to `artifacts/betonline_bets.json`
5. ✅ **Show you a summary** of what was loaded

## Step-by-Step

1. **Run the script:**
   ```bash
   python3 fetch_bets_from_browser.py
   ```

2. **Log in to BetOnline** in the browser window that opens (if you're not already logged in)

3. **Wait for your bets to load** on the page

4. **Press Enter** in the terminal when you see your bets

5. **Done!** The script will extract everything and save it

## What You'll See

```
🚀 BetOnline Bet Fetcher
==================================================
🌐 Opening browser...
📍 Navigating to BetOnline...

⏳ Waiting for page to load...
   If you need to log in, please do so now.
   Once you see your bets, press Enter to continue...

📊 Extracting bet data from page...
✅ Found 1503 bet entries
🔍 Parsing bet entries...
✅ Parsed 316 unique bets

==================================================
✅ Successfully loaded bets!
📊 Summary:
   Total Bets: 316
   Pending: 314
   Won: 1
   Lost: 1
   Total Risked: $561.33
   Total To Win: $118,688.24

💾 Saved to artifacts/betonline_bets.json
🌐 View at: http://localhost:9876/bets
```

## Viewing Your Bets

After running the script, view your bets in the dashboard:

```bash
# Start the dashboard (if not already running)
python3 app_flask.py

# Open in browser
open http://localhost:9876/bets
```

## Troubleshooting

### "playwright not found"

Install Playwright:
```bash
pip3 install playwright
playwright install chromium
```

### "Browser won't open"

Make sure you have Chrome or Chromium installed.

### "No bets found"

1. Make sure you're logged in to BetOnline
2. Navigate to the "Pending Bets" or "Bet History" page
3. Wait for the bets to fully load
4. Then press Enter in the terminal

## Automation (Optional)

If you want to run this automatically every week, you can set up a cron job or just run it manually on Sunday mornings before games start.

## Notes

- The script extracts **all visible bets** (pending, won, lost)
- It automatically removes duplicates
- Your session cookies are used (no need to save credentials)
- The browser window closes automatically when done
- All data is saved locally to `artifacts/betonline_bets.json`

