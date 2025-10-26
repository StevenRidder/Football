# BetOnline Data Fetcher - Chrome Extension

**This Chrome extension bypasses CORS to fetch ALL your bets from BetOnline.**

## Why This Works

- Chrome extensions can make cross-origin requests without CORS restrictions
- Uses your existing authenticated browser session
- Fetches all 404 bets in chunks of 100
- No Cloudflare blocking because it's running in the real browser

## Installation

1. **Open Chrome**

2. **Go to:** `chrome://extensions/`

3. **Enable "Developer mode"** (toggle in top right)

4. **Click "Load unpacked"**

5. **Select this folder:** `/Users/steveridder/Git/Football/betonline-fetcher`

6. **The extension icon will appear** in your toolbar

## Usage

1. **Go to BetOnline** (any page, must be logged in)

2. **Click the extension icon** in your toolbar

3. **Click "Fetch All 404 Bets"**

4. **Wait ~2-3 seconds** while it fetches all pages

5. **It will auto-download:** `all_404_bets_complete.json`

6. **Run the import script:**
   ```bash
   cd /Users/steveridder/Git/Football
   python3 import_all_404_bets.py
   ```

## What It Does

1. Fetches positions 0-100, 100-200, 200-300, 300-400, 400-500
2. Deduplicates bets
3. Shows stats (total, pending, stake, to win)
4. Downloads JSON file
5. You import to database

## Why This Works When Nothing Else Did

- ✅ **No CORS** - Extensions have special permissions
- ✅ **No Cloudflare blocking** - Uses real browser session
- ✅ **Gets ALL 404 bets** - Fetches all pages programmatically
- ✅ **Simple** - One click, done

---

**This is the solution ChatGPT-5 would have suggested.**

