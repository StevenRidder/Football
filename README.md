# 🏈 NFL Edge - Betting Intelligence Dashboard

Professional NFL betting analysis system with predictive modeling, Monte Carlo simulation, and Kelly criterion bet sizing.

## 🎯 Features

- **Predictive Model**: 61.3% historical accuracy on spreads
- **Monte Carlo Simulation**: 20,000 trials per game for probability estimation
- **Kelly Criterion**: Optimal bet sizing based on edge and bankroll
- **Analytics Intensity Index (AII)**: Independent model measuring team analytics adoption
- **Professional Dashboard**: Flask + Tabler UI with official components
- **Detailed Game Analysis**: Click any game for comprehensive stats breakdown
- **REST API**: JSON endpoints for external integrations
- **Backtesting Framework**: Validate model performance on historical data

## 📊 Dashboard

- **Main View**: All games with predictions, EV, and recommendations
- **Best Bets**: Sorted by expected value with stake sizing
- **Game Details**: Click any game for in-depth stats (PPG, EPA, recent form, etc.)
- **Analytics Index**: Team rankings by analytics sophistication

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API key
export ODDS_API_KEY="your_key_here"

# Generate predictions
python3 run_week.py

# Start dashboard
./run_dashboard.sh

# Open browser
open http://localhost:9876
```

## 🛠️ Tech Stack

- **Backend**: Flask, Python 3.9+
- **Frontend**: Tabler (Bootstrap 5)
- **Data**: nflverse, TheOddsAPI
- **ML**: scikit-learn (Ridge regression)
- **Simulation**: NumPy Monte Carlo

## 📁 Project Structure

```
Football/
├── app_flask.py              # Flask dashboard
├── templates/                # Tabler UI templates
├── nfl_edge/                 # Prediction engine
│   ├── data_ingest.py       # Data fetching
│   ├── features.py          # Feature engineering
│   ├── model.py             # ML model
│   ├── simulate.py          # Monte Carlo
│   ├── kelly.py             # Bet sizing
│   └── analytics_index.py   # AII model
├── run_week.py              # Generate predictions
├── run_analytics.py         # Generate AII data
├── backtest_runner.py       # Model validation
├── config.yaml              # Configuration
└── artifacts/               # Predictions & results
```

## 🎮 Usage

### Generate Weekly Predictions
```bash
python3 run_week.py
```

### Run Analytics Index
```bash
python3 run_analytics.py
```

### Backtest Model
```bash
python3 backtest_runner.py
```

### View Dashboard
```bash
./run_dashboard.sh
# or
python3 app_flask.py
```

## 📊 Model Performance

- **Spread Accuracy**: 61.3% (Week 5-7, 2025)
- **Total Accuracy**: 58.7%
- **Expected ROI**: +17% on recommended bets
- **Calibration**: 0.69 factor for conservative predictions

## 📚 Documentation

- **[TABLER_DASHBOARD.md](TABLER_DASHBOARD.md)**: Complete dashboard guide
- **[GAME_DETAILS_FEATURE.md](GAME_DETAILS_FEATURE.md)**: Game detail view documentation
- **[CHEATSHEET.md](CHEATSHEET.md)**: Quick reference commands
- **[BACKTEST_SUMMARY.md](BACKTEST_SUMMARY.md)**: Model validation results
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System design and data flow

## 🔧 Configuration

Edit `config.yaml`:

```yaml
# Model settings
score_calibration_factor: 0.69  # Conservative predictions

# Betting parameters
bankroll: 10000        # Total bankroll
min_ev: 0.02          # Minimum EV threshold (2%)
kelly_fraction: 0.25  # Fractional Kelly sizing
```

## 🌐 API Endpoints

- `GET /api/games` - All game predictions
- `GET /api/best-bets` - Recommended bets sorted by EV
- `GET /api/aii` - Analytics Intensity Index rankings
- `GET /game/<away>/<home>` - Detailed game view

## 🎯 Betting Strategy

1. **Kelly Sizing**: Optimal stake based on edge and probability
2. **EV Threshold**: Only bet when EV > 2%
3. **Bankroll Management**: 25% fractional Kelly for safety
4. **Diversification**: Spread bets across multiple games

## ⚠️ Disclaimer

This is for **educational and entertainment purposes only**. Sports betting involves risk. Past performance does not guarantee future results. Always gamble responsibly within your means.

## 📝 License

Private repository - All rights reserved.

## 🤝 Contributing

Private project - not accepting external contributions.

---

**Built with ❤️ and data**

