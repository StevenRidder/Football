# 🎮 Game Detail View - Feature Guide

## ✅ What's New

**You can now click any game to see detailed stats for eyeballing matchups!**

## 🎯 How to Use

1. Go to main dashboard: **http://localhost:9876**
2. Scroll to "All Games" table
3. **Click ANY game row** (notice the cursor changes to pointer on hover)
4. See comprehensive breakdown with all the stats you need

### Example:
Click "MIN @ LAC" to see: http://localhost:9876/game/MIN/LAC

---

## 📊 What You'll See

### 1. Game Header
Large visual showing:
```
   MIN        @        LAC
  (Away)             (Home)
```

### 2. Model Prediction Cards (4 metrics)
- **Predicted Score**: "23.9-22.7"
- **Home Win %**: 45.5%
- **Spread**: LAC -3.0
- **Total**: 44.5

### 3. Betting Recommendation (Highlighted)
- Best bet with full details
- Expected Value %
- Recommended stake $

### 4. Season Statistics Table

Complete side-by-side comparison:

| Stat | MIN | LAC |
|------|-----|-----|
| Games Played | 7 | 7 |
| **Points Per Game (PPG)** | 24.3 | 23.1 |
| **Points Allowed Per Game** | 22.9 | 21.4 |
| Offensive EPA | 0.15 | 0.12 |
| Defensive EPA | -0.08 | -0.10 |
| Passing EPA/play | 0.18 | 0.15 |
| Rushing EPA/play | -0.02 | -0.01 |
| Def Passing EPA/play | 0.05 | 0.03 |
| Def Rushing EPA/play | -0.12 | -0.08 |
| **Turnovers (Total)** | 8 | 6 |
| **Takeaways (Total)** | 10 | 12 |
| Last 5 Games PPG | 25.2 | 22.8 |
| Last 5 Games PA | 21.4 | 20.6 |

**Color-coded rows:**
- 🟦 Blue: Scoring stats
- 🟥 Red: Defensive stats
- 🟨 Yellow: Turnovers
- 🟩 Green: Takeaways

### 5. Recent Form (Last 3 Games)

**MIN - Last 3 Games:**
| Week | Opponent | PF | PA | Result |
|------|----------|----|----|--------|
| Week 7 | vs DAL | 28 | 24 | W |
| Week 6 | vs TB | 21 | 27 | L |
| Week 5 | vs CHI | 24 | 17 | W |

**LAC - Last 3 Games:**
| Week | Opponent | PF | PA | Result |
|------|----------|----|----|--------|
| Week 7 | vs SEA | 31 | 28 | W |
| Week 6 | vs DEN | 17 | 20 | L |
| Week 5 | vs KC | 24 | 27 | L |

### 6. Predictions from Other Sites

Comparison table showing:

| Source | MIN Win % | LAC Win % | Spread | Total |
|--------|-----------|-----------|--------|-------|
| **Your Model** | 54.5% | 45.5% | LAC -3.0 | 44.5 |
| Opta Supercomputer | 54.5% | 45.5% | MIN -3.0 | 44.5 |
| ESPN | 52.0% | 48.0% | MIN -2.5 | 45.0 |
| FPI | 56.0% | 44.0% | MIN -3.5 | 44.0 |

---

## 🎨 Official Tabler Components Used

All components follow official Tabler patterns:

### Layout Components:
- `card`, `card-lg` - Card containers
- `card-header`, `card-body` - Card sections
- `row`, `col-*` - Bootstrap grid
- `row-deck row-cards` - Card grid layout

### Typography:
- `display-1` - Extra large text (team names)
- `h1`, `h2`, `h3` - Headings
- `subheader` - Tabler subheader class
- `text-center`, `text-end`, `text-muted` - Text utilities

### Tables:
- `table` - Base table
- `table-vcenter` - Vertically centered cells
- `table-hover` - Hover effects
- `table-sm` - Compact table
- `table-primary`, `table-danger`, `table-warning`, `table-success` - Colored rows

### Badges:
- `badge` - Base badge
- `badge-outline` - Outlined badges
- `bg-success`, `bg-danger` - Background colors
- `text-info`, `text-danger`, `text-success` - Text colors

### Interactive:
- `cursor: pointer` - Clickable cursor
- `table-active` - Active row state
- `addEventListener` - Standard JS events

**Source:** https://preview.tabler.io

---

## 💡 Features

✅ **Clickable Rows**: All game rows are clickable (hover shows pointer)  
✅ **Hover Effects**: Rows highlight when you hover over them  
✅ **Back Button**: Easy return to main dashboard  
✅ **Mobile Responsive**: Works on all screen sizes (Tabler default)  
✅ **Live Data**: All stats from real nflverse data  
✅ **Side-by-Side**: Easy comparison of both teams  
✅ **Color Coding**: Important stats highlighted with colors  
✅ **Recent Form**: See momentum with last 3 games  
✅ **External Predictions**: Compare your model to others  

---

## 🔧 Technical Details

### Route:
```
GET /game/<away>/<home>
```

### Example URLs:
- http://localhost:9876/game/MIN/LAC
- http://localhost:9876/game/DAL/DEN
- http://localhost:9876/game/KC/WAS

### Data Sources:
1. **Your Model**: `artifacts/week_*_projections.csv`
2. **Team Stats**: nflverse API (live data)
3. **External Predictions**: Placeholder (integrate real APIs)

### Files Modified:
- `app_flask.py`: Added `/game/<away>/<home>` route and data fetching
- `templates/game_detail.html`: New detailed view template (NEW)
- `templates/index.html`: Made game rows clickable

---

## 🌐 Adding Real External Predictions

Currently showing placeholders. To add real data:

### 1. Edit `app_flask.py` (lines 242-261)

Replace placeholder with real API calls:

```python
# Example: Fetch real Opta data
import requests

opta_response = requests.get(f"https://opta-api.com/predictions/{away}/{home}")
opta_data = opta_response.json()

external_predictions = {
    'opta': {
        'away_win': opta_data['away_win_pct'],
        'home_win': opta_data['home_win_pct'],
        'spread': opta_data['spread'],
        'total': opta_data['total']
    },
    # Add ESPN, FPI, etc.
}
```

### 2. API Sources:
- **Opta**: Contact Opta for API access
- **ESPN**: ESPN Fantasy API or FPI scraping
- **FPI**: ESPN's Football Power Index
- **538**: FiveThirtyEight NFL predictions
- **The Action Network**: Sports betting analytics

---

## 📚 Stats Reference

### EPA (Expected Points Added):
Measures efficiency - how many points a play adds to expected score.
- **Positive EPA**: Good (offense adds points, defense prevents points)
- **Negative EPA**: Bad (offense loses value, defense allows points)

### PPG (Points Per Game):
Average points scored per game (season-to-date).

### PA (Points Allowed):
Average points allowed per game (season-to-date).

### Last 5 Games:
Recent form - more recent games weighted to show momentum.

### Turnovers vs Takeaways:
- **Turnovers**: How many times team gave up the ball
- **Takeaways**: How many times team forced turnovers

---

## 🎯 Use Cases

### For Betting:
1. Click game you're interested in
2. Check if both teams' stats support your model
3. Look at recent form (hot/cold streaks)
4. Compare with other predictions
5. Make informed decision

### For Analysis:
1. See if model prediction makes sense given stats
2. Identify mismatches (e.g., good offense vs weak defense)
3. Check turnover trends (key to game outcomes)
4. Validate your eyeball test against data

### For Learning:
1. Understand what drives model predictions
2. See which stats correlate with wins
3. Learn EPA and advanced metrics
4. Compare your intuition to models

---

## ✅ Verification

**Test it now:**

1. Open: http://localhost:9876
2. Look for "Click any game for detailed stats" hint
3. Click any game row
4. You should see comprehensive breakdown

**If it's not working:**
```bash
# Check Flask is running
ps aux | grep app_flask

# Restart if needed
./stop_dashboard.sh && ./run_dashboard.sh
```

---

## 🚀 Future Enhancements

Potential additions (all using official Tabler patterns):

- [ ] Player stats (injuries, key players)
- [ ] Weather impact
- [ ] Historical head-to-head
- [ ] Betting line movement charts
- [ ] Real-time odds from multiple books
- [ ] Save favorite games
- [ ] Export game report to PDF
- [ ] Add notes/comments per game
- [ ] Compare to Vegas consensus

---

**Enjoy your enhanced eyeball test with real data! 🏈**

