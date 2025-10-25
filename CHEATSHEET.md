# 🏈 NFL Edge Dashboard - Quick Reference

## 🚀 Starting & Stopping

### Start Dashboard
```bash
./run_dashboard.sh
# Then open: http://localhost:9876
```

### Stop Dashboard
```bash
./stop_dashboard.sh
# Or press Ctrl+C if running in terminal
```

### Restart Dashboard
```bash
./stop_dashboard.sh && ./run_dashboard.sh
```

## 📊 Current Apps

| App | URL | Status |
|-----|-----|--------|
| **Flask (NEW Tabler)** | http://localhost:9876 | ✅ Recommended |
| Streamlit (OLD) | http://localhost:8501 | Still works |

## 🔄 Update Predictions

```bash
# Generate new predictions
python3 run_week.py

# Update analytics index
python3 run_analytics.py

# Refresh browser - dashboard auto-loads latest data
```

## 🔍 Check Status

```bash
# See what's running
ps aux | grep -E "app_flask|streamlit" | grep -v grep

# Check if port 9876 is in use
lsof -i :9876

# Test if dashboard is responding
curl http://localhost:9876
```

## 🛠️ Common Tasks

### Stop Old Streamlit Only
```bash
pkill -f "streamlit run app.py"
```

### Run Flask in Background
```bash
nohup python3 app_flask.py > dashboard.log 2>&1 &
```

### View Logs
```bash
# If running in background
tail -f dashboard.log

# If running in terminal, logs show there
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app_flask.py` | Flask backend |
| `templates/` | Tabler HTML templates |
| `artifacts/week_*.csv` | Prediction data |
| `run_dashboard.sh` | Start script |
| `stop_dashboard.sh` | Stop script |

## 🎯 Workflow

1. **Generate predictions**: `python3 run_week.py`
2. **Start dashboard**: `./run_dashboard.sh`
3. **View in browser**: http://localhost:9876
4. **Make changes**: Edit code (auto-reloads)
5. **Stop when done**: `Ctrl+C` or `./stop_dashboard.sh`

## 💡 Pro Tips

- Flask auto-reloads when you edit code
- Keep terminal open to see logs
- Refresh browser after running `run_week.py`
- Use `./stop_dashboard.sh` to clean up both dashboards
- API available at `/api/games`, `/api/best-bets`, `/api/aii`

---

**Need help?** See `TABLER_DASHBOARD.md` for full documentation.

