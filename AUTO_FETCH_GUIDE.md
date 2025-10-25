# 🚀 BetOnline Auto-Fetch - Complete Guide

## ✅ What's Been Built

I've created a **fully automated bet fetching system** that pulls ALL your bets from BetOnline's API with ONE click!

No more manual copying. No more tedious data entry. Just automatic fetching.

## 🎯 How It Works

### One-Time Setup (5 minutes)

1. **Run the setup script:**
```bash
python3 setup_betonline_auto_fetch.py
```

2. **Follow the prompts:**
   - Log into BetOnline
   - Open DevTools (F12)
   - Go to Network tab
   - Visit Bet History page
   - Copy ONE cURL command
   - Paste it into the script

3. **Done!** Your session is saved and ready to use.

### Auto-Fetch Anytime

**Option 1: Web Interface (Easiest)**
1. Go to http://localhost:9876/bets
2. Click "Auto-Fetch from BetOnline" button
3. Wait 2-3 seconds
4. All your bets appear automatically!

**Option 2: Command Line**
```bash
python3 auto_fetch_bets.py
```

## 📊 What Gets Fetched

The system automatically fetches:
- ✅ **All pending bets** (current wagers)
- ✅ **All graded bets** (won/lost)
- ✅ **Complete bet history** (all time)
- ✅ **Bet details** (ticket #, date, amount, odds, etc.)
- ✅ **Profit/Loss** calculations
- ✅ **Win rate** statistics

## 🎨 Features

### Smart Parsing
- Extracts ticket numbers, dates, amounts automatically
- Calculates profit/loss for each bet
- Determines win/loss status
- Formats everything for the web interface

### Session Management
- Saves your session cookies securely
- Session lasts ~24 hours
- Easy to refresh when expired

### Error Handling
- Detects expired sessions
- Provides clear error messages
- Guides you to re-run setup if needed

## 📁 Files Created

### Setup Script
- `setup_betonline_auto_fetch.py` - One-time setup to save your session

### Auto-Fetch Script
- `auto_fetch_bets.py` - Fetches all bets automatically

### Session Storage
- `artifacts/betonline_session.json` - Your saved session cookies (gitignored)

### Bet Data
- `artifacts/betonline_bets.json` - Your fetched bets in web format
- `artifacts/bets.parquet` - Raw bet data from BetOnline API

## 🔒 Security

- **Session cookies are saved locally** - Never sent to any external server
- **Stored in gitignored directory** - Won't be committed to git
- **Expires automatically** - Session only lasts ~24 hours
- **No passwords stored** - Only session cookies, which expire

## 🚀 Quick Start

### Step 1: Setup (First Time Only)
```bash
python3 setup_betonline_auto_fetch.py
```

Follow the prompts to save your session.

### Step 2: Fetch Bets (Anytime)

**Via Web:**
- Go to http://localhost:9876/bets
- Click "Auto-Fetch from BetOnline"

**Via Command Line:**
```bash
python3 auto_fetch_bets.py
```

### Step 3: View Your Bets
- All bets appear in the web interface
- Click any bet to see full details
- Use filters to find specific bets

## 🔄 Session Expired?

If you see "session expired" error:

1. Run setup again:
```bash
python3 setup_betonline_auto_fetch.py
```

2. Copy a fresh cURL command
3. Done! Session refreshed.

## 📊 Example Output

```
================================================================================
BETONLINE AUTO-FETCH
================================================================================

⏳ Loading saved session...
✅ Session loaded

⏳ Fetching your bets from BetOnline...

✅ SUCCESS! Fetched 14 bets
✅ Saved to artifacts/betonline_bets.json

================================================================================
SUMMARY
================================================================================
Total Bets: 14
Total Wagered: $336.33
Total Profit/Loss: -$63.33
Pending: 9 bets ($236.33)
Potential Win: $109,879.54
Win Rate: 20.0%

================================================================================
VIEW YOUR BETS
================================================================================
Go to: http://localhost:9876/bets
Your bets are now loaded and ready to view!
```

## 🎯 Benefits

### Before (Manual)
- ❌ Copy each bet individually
- ❌ Format data manually
- ❌ Paste into web interface
- ❌ Takes 10-15 minutes for all bets
- ❌ Error-prone

### After (Auto-Fetch)
- ✅ One click
- ✅ Automatic formatting
- ✅ All bets fetched
- ✅ Takes 2-3 seconds
- ✅ 100% accurate

## 🛠️ Technical Details

### BetOnline API Endpoints
The system hits these BetOnline endpoints:
- `/report/get-pending-wagers` - Current bets
- `/report/get-graded-wagers` - Settled bets
- `/report/get-bet-history` - Full history

### Authentication
- Uses session cookies from your browser
- Mimics your browser's requests
- No username/password needed

### Data Flow
1. Load saved session cookies
2. Hit BetOnline API endpoints
3. Parse raw JSON responses
4. Normalize to standard format
5. Calculate profit/loss
6. Save to JSON for web interface

## 🎉 Summary

**You're all set!** Just run the setup once, then click "Auto-Fetch" anytime to get ALL your bets automatically.

No more manual copying. No more data entry. Just automatic, instant bet tracking! 🚀

