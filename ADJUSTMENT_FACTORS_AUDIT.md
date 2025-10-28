# 🔍 ADJUSTMENT FACTORS AUDIT

**Current Status:** Limited factors - Missing key situational edges

---

## ✅ FACTORS WE'RE CURRENTLY USING

### 1. **Weather** (Open-Meteo API)
**Applied to:** Total (reduces scoring)

| Factor | Threshold | Impact | Applied? |
|--------|-----------|--------|----------|
| Wind Speed | ≥20 MPH | -3.0 pts | ✅ Yes |
| Wind Speed | 15-20 MPH | -1.5 pts | ✅ Yes |
| Wind Speed | 10-15 MPH | -0.7 pts | ✅ Yes |
| Heavy Rain | ≥3.0 mm/hr | -1.0 pts | ✅ Yes |
| Moderate Rain | 1.0-3.0 mm/hr | -0.5 pts | ✅ Yes |
| Dome/Roof | Yes | Wind × 0.25 | ✅ Yes |

**Example:** MIN @ DET - No weather impact (dome)

---

### 2. **QB Injuries** (LLM Detection via OpenAI)
**Applied to:** Both spread and total

| Factor | Impact | Applied? |
|--------|--------|----------|
| Starter → Backup | -8.0 pts to offense | ✅ Yes |
| Starter → 3rd String | -8.0 pts to offense | ✅ Yes |
| QB Questionable | Not applied | ❌ No |

**Example:** MIN @ DET
- Carson Wentz OUT → -8.0 pts to MIN
- Adjusted: MIN 20 → 16, DET 28 → 24
- Total: 47.5 → 39.5 (BET UNDER)

---

### 3. **OL Injuries** (LLM Detection via OpenAI)
**Applied to:** Both spread and total

| Factor | Impact | Applied? |
|--------|--------|----------|
| Starting OL Out | -2.0 pts per player | ✅ Yes |
| OL Questionable | Not applied | ❌ No |
| OL Continuity (new combos) | Not tracked | ❌ No |

**Example:** MIN @ DET
- Brian O'Neill (OT) OUT → -2.0 pts to MIN
- Combined with Wentz: -10.0 pts total

---

### 4. **Other Position Injuries** (LLM Detection)
**Applied to:** Total only

| Factor | Impact | Applied? |
|--------|--------|----------|
| WR1 Out (High Impact) | -2.5 pts | ✅ Yes |
| WR1 Out (Medium Impact) | -1.5 pts | ✅ Yes |
| WR1 Out (Low Impact) | -0.5 pts | ✅ Yes |
| RB1 Out | -0.5 to -2.5 pts | ✅ Yes |
| TE1 Out | -0.5 to -2.5 pts | ✅ Yes |
| Defensive Players | Not applied | ❌ No |

---

## ❌ FACTORS WE'RE **NOT** USING (BUT SHOULD)

### 1. **Home/Away Splits** ⚠️ **CRITICAL MISSING**
**Your Example:** BAL always loses away games this year

| Factor | Impact | Currently Applied? |
|--------|--------|-------------------|
| Team's Away Record | ❌ No | **SHOULD BE -1.0 to -2.0 pts** |
| Team's Home Record | ❌ No | **SHOULD BE +0.5 to +1.5 pts** |
| Away Win % vs Expected | ❌ No | **SHOULD BE -1.0 to -2.0 pts** |
| Home Win % vs Expected | ❌ No | **SHOULD BE +0.5 to +1.5 pts** |

**Example - BAL @ MIA:**
- BAL 2025 Away Record: 0-4 (or similar)
- Expected Away Win%: ~40%
- Actual Away Win%: 0%
- **Adjustment: -1.5 to -2.0 pts to BAL**
- **Current System: NO ADJUSTMENT** ❌

---

### 2. **Travel & Rest**
| Factor | Impact | Currently Applied? |
|--------|--------|-------------------|
| Cross-Country Travel (3+ time zones) | -1.0 to -1.5 pts | ❌ No |
| Short Rest (Thu/Mon game) | -1.0 pts | ❌ No |
| Extra Rest (Bye week) | +1.0 to +1.5 pts | ❌ No |
| Back-to-back road games | -0.5 pts | ❌ No |

---

### 3. **Pace & Script Tendencies**
| Factor | Impact | Currently Applied? |
|--------|--------|-------------------|
| Fast Pace Team (>65 plays/game) | +2.0 to +3.0 pts to total | ❌ No |
| Slow Pace Team (<58 plays/game) | -2.0 to -3.0 pts to total | ❌ No |
| Run-Heavy When Leading | -1.0 to -2.0 pts to total | ❌ No |
| Pass-Heavy When Trailing | +1.0 to +2.0 pts to total | ❌ No |

---

### 4. **Defense Matchup**
| Factor | Impact | Currently Applied? |
|--------|--------|-------------------|
| Elite Pass Defense vs Pass-Heavy Offense | -2.0 pts to offense | ❌ No |
| Elite Run Defense vs Run-Heavy Offense | -1.5 pts to offense | ❌ No |
| Pressure Rate vs OL Quality | -1.0 to -2.0 pts | ❌ No |
| Red Zone Defense vs Red Zone Offense | -1.0 pts to total | ❌ No |

---

### 5. **Recent Form & Momentum**
| Factor | Impact | Currently Applied? |
|--------|--------|-------------------|
| Team on 3+ game win streak | +0.5 pts | ❌ No |
| Team on 3+ game losing streak | -0.5 pts | ❌ No |
| Coming off blowout win (>14 pts) | +0.5 pts | ❌ No |
| Coming off blowout loss (>14 pts) | -0.5 pts | ❌ No |

---

### 6. **Coaching & Situational**
| Factor | Impact | Currently Applied? |
|--------|--------|-------------------|
| Coach vs Specific Opponent (historical edge) | +0.5 to +1.0 pts | ❌ No |
| Divisional Game (more conservative) | -1.0 to -2.0 pts to total | ❌ No |
| Primetime Game (different performance) | +/- 0.5 pts | ❌ No |

---

### 7. **Market Movement**
| Factor | Impact | Currently Applied? |
|--------|--------|-------------------|
| Line moved >2 pts since open | Sharp money indicator | ❌ No |
| Reverse line movement | Public vs sharp disagreement | ❌ No |
| Steam moves (rapid line changes) | Follow the sharp money | ❌ No |

---

## 🎯 PRIORITY ADDITIONS

### **HIGH PRIORITY** (Add This Week)

#### 1. **Home/Away Splits** ⭐⭐⭐
**Why:** BAL example - clear situational edge
**How to Add:**
```python
# In edge_hunt/home_away_splits.py
def get_home_away_adjustment(team: str, is_home: bool, season: int = 2025) -> float:
    """
    Calculate adjustment based on team's home/away performance.
    
    Returns:
        Adjustment in points (negative = team worse than expected)
    """
    # Fetch team's actual home/away record
    # Compare to expected win% based on strength
    # Return adjustment
    
    # Example: BAL away
    if team == "BAL" and not is_home:
        # BAL 0-4 away, expected ~40% win rate
        return -1.5  # Underperforming away
    
    return 0.0
```

**Impact:** Would have adjusted BAL @ MIA by -1.5 to -2.0 pts

---

#### 2. **Travel Distance** ⭐⭐
**Why:** Cross-country travel affects performance
**How to Add:**
```python
# In edge_hunt/travel_rest_features.py (already exists, needs integration!)
def get_travel_adjustment(away_team: str, home_team: str) -> float:
    """
    Calculate adjustment based on travel distance and time zones.
    
    Returns:
        Adjustment in points (negative = fatigue penalty)
    """
    # Calculate distance between stadiums
    # Count timezone changes
    # Return adjustment
    
    # Example: SEA → MIA (3 time zones)
    if away_team == "SEA" and home_team == "MIA":
        return -1.0  # Cross-country travel
    
    return 0.0
```

---

#### 3. **Divisional Game Flag** ⭐⭐
**Why:** Divisional games are more conservative, lower scoring
**How to Add:**
```python
def is_divisional_game(away: str, home: str) -> bool:
    DIVISIONS = {
        'AFC_EAST': ['BUF', 'MIA', 'NE', 'NYJ'],
        'AFC_NORTH': ['BAL', 'CIN', 'CLE', 'PIT'],
        # ... etc
    }
    
    for division in DIVISIONS.values():
        if away in division and home in division:
            return True
    return False

# If divisional: total_adjustment -= 2.0
```

---

### **MEDIUM PRIORITY** (Add Next Week)

4. **Pace Adjustments** - Fast/slow teams affect totals
5. **Recent Form** - Win/loss streaks
6. **Defense Matchups** - Elite D vs specific offensive styles

---

### **LOW PRIORITY** (Add Later)

7. **Coaching Edges** - Historical matchup performance
8. **Market Movement Tracking** - Follow sharp money
9. **Primetime Adjustments** - Performance in night games

---

## 📊 CURRENT ADJUSTMENT FLOW

```
1. Start with Market-Implied Score
   ↓
2. Apply Weather Adjustments (if any)
   ↓
3. Apply QB Injury Adjustments (if any)
   ↓
4. Apply OL Injury Adjustments (if any)
   ↓
5. Apply Other Position Injuries (if any)
   ↓
6. Calculate Adjusted Score
   ↓
7. Compare to Market → Generate Bet
```

**What's Missing:**
- ❌ Home/Away splits
- ❌ Travel/rest
- ❌ Divisional game flag
- ❌ Pace adjustments
- ❌ Defense matchups
- ❌ Recent form

---

## 🔧 HOW TO ADD HOME/AWAY SPLITS (EXAMPLE)

### Step 1: Create Module
```python
# edge_hunt/home_away_splits.py
import pandas as pd
import nfl_data_py as nfl

def get_2025_home_away_performance(team: str) -> dict:
    """Fetch team's 2025 home/away record."""
    games = nfl.import_schedules([2025])
    games = games[games['week'] <= 8]  # Only completed games
    
    # Away games
    away_games = games[games['away_team'] == team]
    away_wins = (away_games['away_score'] > away_games['home_score']).sum()
    away_total = len(away_games)
    
    # Home games
    home_games = games[games['home_team'] == team]
    home_wins = (home_games['home_score'] > home_games['away_score']).sum()
    home_total = len(home_games)
    
    return {
        'away_record': f"{away_wins}-{away_total - away_wins}",
        'away_win_pct': away_wins / away_total if away_total > 0 else 0.5,
        'home_record': f"{home_wins}-{home_total - home_wins}",
        'home_win_pct': home_wins / home_total if home_total > 0 else 0.5,
    }

def calculate_home_away_adjustment(team: str, is_home: bool) -> float:
    """
    Calculate adjustment based on home/away performance vs expectation.
    
    Returns:
        Points adjustment (negative = team underperforming)
    """
    perf = get_2025_home_away_performance(team)
    
    if is_home:
        win_pct = perf['home_win_pct']
        expected = 0.55  # Home teams win ~55% on average
    else:
        win_pct = perf['away_win_pct']
        expected = 0.45  # Away teams win ~45% on average
    
    # If significantly underperforming
    if win_pct < expected - 0.15:  # e.g., 0% away vs 45% expected
        return -1.5
    elif win_pct < expected - 0.10:
        return -1.0
    elif win_pct > expected + 0.15:
        return +1.0
    
    return 0.0
```

### Step 2: Integrate into `get_edge_hunt_signals`
```python
# In edge_hunt/integrate_signals.py

from edge_hunt.home_away_splits import calculate_home_away_adjustment

def get_edge_hunt_signals(...):
    # ... existing code ...
    
    # 3. Check home/away splits
    away_ha_adj = calculate_home_away_adjustment(away, is_home=False)
    home_ha_adj = calculate_home_away_adjustment(home, is_home=True)
    
    # Apply to spread (favors team with better split)
    spread_adj += (away_ha_adj - home_ha_adj)
    
    # Apply to total (both teams)
    total_adj += (away_ha_adj + home_ha_adj)
    
    if abs(away_ha_adj) >= 1.0:
        signals.append({
            'type': 'situational',
            'icon': '✈️',
            'badge': 'AWAY STRUGGLES',
            'badge_color': 'warning',
            'severity': 'medium',
            'bet_type': 'spread',
            'bet_side': 'home',
            'edge_pts': abs(away_ha_adj),
            'explanation': f"{away} has struggled on the road this season. Historical splits show {abs(away_ha_adj):.1f} point disadvantage away from home.",
            'details': [
                f"Team: {away} (Away)",
                f"2025 Away Record: {get_2025_home_away_performance(away)['away_record']}",
                f"Expected Impact: {away_ha_adj:.1f} points",
                f"Recommended: BET {home} {open_spread:+.1f}"
            ],
            'confidence': 'MEDIUM'
        })
```

---

## 📝 SUMMARY

### Currently Using (5 factors):
1. ✅ Weather (wind, rain)
2. ✅ QB injuries
3. ✅ OL injuries
4. ✅ WR/RB/TE injuries
5. ✅ Dome/roof flag

### Missing (12+ factors):
1. ❌ **Home/Away splits** ← YOUR EXAMPLE (BAL away)
2. ❌ Travel distance
3. ❌ Rest days
4. ❌ Divisional games
5. ❌ Pace (plays per game)
6. ❌ Defense matchups
7. ❌ Recent form
8. ❌ Coaching edges
9. ❌ Primetime adjustments
10. ❌ Market movement
11. ❌ OL continuity (new combinations)
12. ❌ Weather temperature extremes

---

## 🎯 NEXT STEPS

1. **Add Home/Away Splits** (addresses your BAL example)
2. **Add Travel/Rest** (already have module, just need to integrate)
3. **Add Divisional Game Flag** (simple boolean check)
4. **Test with BAL @ MIA** (should now show -1.5 to -2.0 pts adjustment)

**Would you like me to implement the Home/Away splits module now?**

