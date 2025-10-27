# ESPN API - All Available Data

## What We Currently Use ✅

1. **Team Performance Stats** (from nflverse)
   - Offensive EPA per play
   - Defensive EPA per play
   - Offensive Success Rate
   - Defensive Success Rate
   - Points For/Against
   - Turnover Differential

2. **Weather Data** (from Open-Meteo)
   - Wind speed (in kph)
   - Temperature
   - Precipitation
   - Indoor/Dome flag

3. **Injury Data** (from nflverse)
   - Injury index by position
   - Out/Doubtful/Questionable status

4. **Situational Features**
   - Rest days
   - Travel distance
   - Timezone changes
   - Divisional/Conference flags

5. **Market Lines** (from Odds API)
   - Spread
   - Total (over/under)

## What ESPN Provides (NOT Currently Used)

### Game-Level Data
- **Attendance** - actual crowd size
- **Venue Details** - grass vs turf, indoor/outdoor
- **Weather** (more detailed than Open-Meteo):
  - Temperature (current, high, low)
  - Condition ID (cloudy, rainy, etc.)
  - Wind gust speed
  - Precipitation percentage
- **Broadcasts** - which networks are showing the game
- **Game Time** - exact kickoff time

### Team-Level Data
- **Injuries** (real-time):
  - Player name
  - Position
  - Status (Out, Doubtful, Questionable, Probable)
  - Details (knee, ankle, etc.)
- **Team Records**:
  - Overall record
  - Home/Away splits
  - Division record
  - Conference record
  - Last 5 games
- **Standings** - current playoff position

### Advanced Game Data (from Game Detail API)
- **Win Probability** - ESPN's live win probability model
- **Predictor** - ESPN's pre-game predictions
- **Against the Spread (ATS)** - historical ATS records
- **Last Five Games** - recent performance trends
- **Leaders** - top performers (passing, rushing, receiving)
- **Boxscore** - detailed game statistics
- **News** - recent team news articles

### Odds/Betting Data
- **Multiple Sportsbooks** - consensus lines
- **Moneyline** - win probability implied by odds
- **Point Spread** - with odds for each side
- **Total** - with over/under odds
- **Featured Bets** - popular prop bets

## What We DON'T Have Access To

### Officiating Data ❌
- **Referee Crews** - Not available in ESPN API
- **Historical Crew Stats** - Would need to scrape from other sources
- **Penalty Tendencies** - Not publicly available

### Advanced Metrics ❌
- **Player Tracking Data** - NFL Next Gen Stats (requires paid access)
- **Coaching Tendencies** - Not quantified anywhere
- **Play-by-Play Sequences** - Available but not in real-time
- **Snap Counts** - Not in ESPN API

### Betting Market Inefficiencies ❌
- **Sharp vs Public Money** - Requires paid betting data services
- **Line Movement** - Would need to track over time
- **Steam Moves** - Requires real-time monitoring

## Should We Add More Data?

### High Value, Easy to Add ✅
1. **ESPN Weather** (instead of Open-Meteo)
   - More accurate for game-time conditions
   - Includes precipitation percentage
   - **Recommendation: YES, switch to ESPN weather**

2. **Home/Away Splits**
   - Some teams perform much better at home
   - Easy to calculate from existing data
   - **Recommendation: YES, add home/away performance splits**

3. **Last 5 Games Trend**
   - Momentum matters (hot/cold streaks)
   - ESPN provides this directly
   - **Recommendation: YES, add recent form indicator**

### Medium Value, Medium Effort 🤔
4. **Grass vs Turf**
   - Some teams/players perform differently on turf
   - Available in venue data
   - **Recommendation: MAYBE, if we see evidence it matters**

5. **Prime Time Games**
   - Some teams underperform in prime time
   - Easy to detect from broadcast data
   - **Recommendation: MAYBE, could be a small edge**

6. **Altitude**
   - Denver games are known to be different
   - Would need to add stadium elevation data
   - **Recommendation: MAYBE, but only affects 1-2 teams**

### Low Value or Too Complex ❌
7. **Referee Crews**
   - Not available in ESPN API
   - Would need to scrape from other sources
   - Historical impact is debatable
   - **Recommendation: NO, too much work for uncertain value**

8. **Player Tracking Data**
   - Requires paid NFL Next Gen Stats access
   - Very expensive
   - **Recommendation: NO, not worth the cost**

9. **Sharp Money Tracking**
   - Requires paid betting data services
   - Would make model dependent on external data
   - **Recommendation: NO, keep model independent**

## Final Recommendations

### Add These (High ROI):
1. ✅ Switch to ESPN weather API (more accurate)
2. ✅ Add home/away performance splits
3. ✅ Add "last 5 games" momentum indicator

### Skip These (Low ROI or Too Complex):
1. ❌ Referee crews (not available, uncertain value)
2. ❌ Player tracking data (too expensive)
3. ❌ Sharp money tracking (makes model dependent)
4. ❌ Grass vs turf (minimal impact)

### Current Model is Already Using:
- ✅ Injuries (from nflverse)
- ✅ Weather (from Open-Meteo, could upgrade to ESPN)
- ✅ Rest days, travel, divisional games
- ✅ EPA, success rate, turnover differential

**Bottom Line:** We're already using most of the valuable data. The biggest gains would come from better model calibration (which we just did with recency weight and EPA caps) rather than adding more data sources.

