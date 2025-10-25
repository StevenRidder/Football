# 🧪 Test Your Dashboard

## ✅ Quick Test Commands

### 1. Check if Flask is running:
```bash
ps aux | grep app_flask | grep -v grep
```
**Expected:** Should show python3 app_flask.py process

### 2. Test main page:
```bash
curl -s http://localhost:9876 | grep "NFL Edge"
```
**Expected:** Should return HTML with "NFL Edge" title

### 3. Test API:
```bash
curl http://localhost:9876/api/games
```
**Expected:** JSON array with 13 games

### 4. Test best bets API:
```bash
curl http://localhost:9876/api/best-bets
```
**Expected:** JSON array with recommended bets

## 🌐 Visual Check

Open these URLs in your browser:

1. **Main Dashboard:** http://localhost:9876
   - Should see: Dark navbar, 4 stat cards, tables with games
   
2. **Analytics Index:** http://localhost:9876/analytics
   - Should see: Team rankings with AII scores

## 📊 What You Should See

### Main Dashboard (/)
```
╔════════════════════════════════════════════╗
║  🏈 NFL Edge                    Dashboard  ║
╠════════════════════════════════════════════╣
║                                            ║
║  Week 8 Predictions                        ║
║  NFL Betting Intelligence                  ║
║                                            ║
║  ┌──────────┬──────────┬──────────┬──────┐║
║  │Total Games│Rec Plays │Avg Edge  │Stake │║
║  │    13     │    11    │  +40.5%  │$2500 │║
║  └──────────┴──────────┴──────────┴──────┘║
║                                            ║
║  💰 Best Bets                              ║
║  ┌────────────────────────────────────────┐║
║  │ DAL @ DEN | SPREAD | DAL +3.5 | +73.5% │║
║  │ CHI @ BAL | SPREAD | CHI +6.5 | +63.8% │║
║  │ ...                                    │║
║  └────────────────────────────────────────┘║
║                                            ║
║  📊 All Games                              ║
║  ┌────────────────────────────────────────┐║
║  │ Away│Home│Score│Spread│Total│Win%│EV%  │║
║  │ MIN │LAC │23-22│ +3.0│44.5│45.5│+23.1%│║
║  │ ...                                    │║
║  └────────────────────────────────────────┘║
╚════════════════════════════════════════════╝
```

## ❌ Troubleshooting

### I see "This site can't be reached"
```bash
# Check if Flask is running
ps aux | grep app_flask

# If not running, start it
./run_dashboard.sh
```

### I see a blank page
```bash
# Check browser console (F12 → Console)
# Look for JavaScript errors

# Force refresh
Ctrl+Shift+R (or Cmd+Shift+R on Mac)
```

### Port 9876 is in use
```bash
# Find what's using it
lsof -i :9876

# Kill that process
kill <PID>

# Or change port in app_flask.py line 165
```

### No data showing
```bash
# Make sure predictions exist
ls -la artifacts/week_*_projections.csv

# If missing, generate them
python3 run_week.py
```

## ✅ Success Indicators

When working correctly, you'll see:

- ✅ Dark navbar at top with "🏈 NFL Edge"
- ✅ Four stat cards with numbers
- ✅ Best Bets table with recommendations
- ✅ All Games table with 13 rows (this week)
- ✅ No JavaScript errors in console
- ✅ Professional Tabler styling

## 🔗 All URLs

| Page | URL |
|------|-----|
| Main | http://localhost:9876 |
| Analytics | http://localhost:9876/analytics |
| API Games | http://localhost:9876/api/games |
| API Bets | http://localhost:9876/api/best-bets |
| API AII | http://localhost:9876/api/aii |

---

**Still having issues?** Check the terminal where Flask is running for error messages.
