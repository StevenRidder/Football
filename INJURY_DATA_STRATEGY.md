# NFL Injury Data Strategy - Authoritative Sources

## The Problem You Identified

**Current approach has issues:**
1. ❌ Scraping NFL.com HTML is fragile (structure changes break it)
2. ❌ OpenAI's training data is stale (cutoff date)
3. ❌ No guarantee of consistency week-to-week
4. ❌ No single source of truth

**What we need:**
- ✅ Authoritative, structured API (not HTML scraping)
- ✅ Real-time updates (Wednesday-Sunday injury reports)
- ✅ Consistent schema week-over-week
- ✅ Reliable, professional-grade data

---

## Recommended Solution: Multi-Tier Approach

### **Tier 1: ESPN API (Free, Official)**

**Best for:** Real-time injury status, depth charts

**Endpoint:**
```
https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}
```

**Why ESPN:**
- ✅ Official NFL partner
- ✅ Free, no API key needed
- ✅ Structured JSON (not HTML)
- ✅ Updates multiple times per day
- ✅ Includes injury status (Out, Doubtful, Questionable, Probable)
- ✅ Has depth chart data (starter vs backup)

**Current Issue:** The API structure changed or we're not parsing correctly.

**Fix:** Let me rebuild the ESPN parser with proper error handling.

---

### **Tier 2: SportsData.io (Paid, $19/month)**

**Best for:** Backup when ESPN fails, historical data

**Endpoint:**
```
https://api.sportsdata.io/v3/nfl/scores/json/Injuries/{season}
```

**Why SportsData.io:**
- ✅ Professional-grade API
- ✅ Guaranteed uptime (SLA)
- ✅ Consistent schema
- ✅ Includes injury details (body part, practice status)
- ✅ Historical injury data for backtesting

**Cost:** $19/month for 1,000 calls/day (more than enough)

**When to use:** If ESPN API fails or for production deployment

---

### **Tier 3: LLM as Last Resort (OpenAI)**

**Best for:** Breaking news, edge cases, verification

**When to use:**
- ESPN API is down
- SportsData.io doesn't have latest update
- Need to parse unstructured injury news (Twitter, press conferences)

**Cost:** ~$0.01 per game (14 games = $0.14/week)

---

## Proposed Architecture

### **Weekly Injury Update Pipeline**

```
┌─────────────────────────────────────────────────────────┐
│  WEDNESDAY 9AM ET - Initial Injury Report               │
└─────────────────────────────────────────────────────────┘
                          ↓
         ┌────────────────────────────────┐
         │  1. Fetch ESPN API (all teams) │
         │     - Parse injury status      │
         │     - Parse depth charts       │
         │     - Identify QB/OL changes   │
         └────────────────────────────────┘
                          ↓
              ┌──────────────────┐
              │  ESPN Success?   │
              └──────────────────┘
                 ↓           ↓
              YES           NO
                 ↓           ↓
         ┌──────────┐   ┌──────────────────┐
         │  Cache   │   │  Fallback to     │
         │  Results │   │  SportsData.io   │
         └──────────┘   └──────────────────┘
                              ↓
                    ┌──────────────────┐
                    │  Still Failed?   │
                    └──────────────────┘
                              ↓
                    ┌──────────────────┐
                    │  Use LLM to      │
                    │  scrape news     │
                    └──────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  Store in Database with Timestamp  │
         │  - injury_reports table            │
         │  - source: 'espn' | 'sportsdata'   │
         │  - collected_at: timestamp         │
         └────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  FRIDAY 4PM ET - Updated Injury Report                  │
│  (Repeat above process)                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  SUNDAY 11AM ET - Final Injury Report (90 min before)  │
│  (Repeat above process)                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### **Phase 1: Fix ESPN API Parser (Today)**

**File:** `edge_hunt/espn_injury_api.py`

**What to fix:**
1. Update team ID mapping (all 32 teams)
2. Handle new API response structure
3. Add retry logic with exponential backoff
4. Add detailed error logging
5. Validate response schema

**Expected result:** Reliable ESPN injury data

---

### **Phase 2: Add SportsData.io Backup (Optional)**

**File:** `edge_hunt/sportsdata_injury_api.py`

**When:** If ESPN proves unreliable in production

**Cost:** $19/month (worth it for production)

---

### **Phase 3: Add Database Storage (Recommended)**

**File:** `edge_hunt/injury_database.py`

**Schema:**
```sql
CREATE TABLE injury_reports (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(50),
    team VARCHAR(10),
    player_name VARCHAR(100),
    position VARCHAR(10),
    injury_type VARCHAR(50),
    status VARCHAR(20),  -- OUT, DOUBTFUL, QUESTIONABLE, PROBABLE
    practice_status VARCHAR(50),  -- DNP, LIMITED, FULL
    source VARCHAR(20),  -- espn, sportsdata, llm
    collected_at TIMESTAMP,
    week INT,
    season INT
);

CREATE INDEX idx_injury_game ON injury_reports(game_id, collected_at);
CREATE INDEX idx_injury_team_week ON injury_reports(team, week, season);
```

**Benefits:**
- ✅ Historical injury tracking
- ✅ Compare Wednesday vs Friday vs Sunday reports
- ✅ Measure CLV by injury timing
- ✅ Audit trail (know exactly what data we had when)

---

### **Phase 4: Automated Cron Jobs**

**Schedule:**
```bash
# Wednesday 9:00 AM ET - Initial injury report
0 13 * * 3 /usr/bin/python3 /path/to/fetch_injuries.py --day wednesday

# Friday 4:00 PM ET - Updated injury report  
0 20 * * 5 /usr/bin/python3 /path/to/fetch_injuries.py --day friday

# Sunday 11:00 AM ET - Final injury report (90 min before 12:30 kickoff)
0 15 * * 0 /usr/bin/python3 /path/to/fetch_injuries.py --day sunday
```

**What it does:**
1. Fetches injuries from ESPN (or fallback)
2. Stores in database with timestamp
3. Updates predictions cache
4. Sends alert if critical injury detected (QB, WR1, etc.)

---

## Data Consistency Guarantees

### **1. Single Source of Truth per Week**

**Rule:** Once we fetch data for a game, we lock the source.

```python
# Example
if injury_report.source == 'espn':
    # Always use ESPN for this game this week
    use_espn_for_updates()
elif injury_report.source == 'sportsdata':
    # Always use SportsData for this game this week
    use_sportsdata_for_updates()
```

### **2. Timestamp Everything**

Every injury report includes:
- `collected_at`: When we fetched it
- `report_date`: When NFL published it (Wednesday/Friday/Sunday)
- `source`: Where it came from

### **3. Version Control**

Track changes:
```python
# If injury status changes, log it
if previous_status == 'QUESTIONABLE' and new_status == 'OUT':
    log_injury_change(player, old='QUESTIONABLE', new='OUT', 
                     timestamp=now, source='espn')
```

### **4. Validation Rules**

Before using injury data:
```python
def validate_injury_data(injury_report):
    # Must be from last 24 hours
    if injury_report.collected_at < now - timedelta(hours=24):
        return False
    
    # Must have required fields
    if not all([injury_report.player_name, 
                injury_report.status, 
                injury_report.team]):
        return False
    
    # Status must be valid
    if injury_report.status not in ['OUT', 'DOUBTFUL', 'QUESTIONABLE', 'PROBABLE']:
        return False
    
    return True
```

---

## Real-Time Updates During Game Week

### **How to Stay Current:**

**Option 1: Scheduled Updates (Recommended)**
- Run injury fetch 3x per week (Wed/Fri/Sun)
- Cache results for 24 hours
- Manual refresh button in UI for breaking news

**Option 2: Webhook Notifications (Advanced)**
- Subscribe to NFL injury alerts
- Update database immediately
- Invalidate prediction cache
- Push notification to users

**Option 3: Continuous Polling (Expensive)**
- Poll ESPN API every 30 minutes
- Only during game week (Wed-Sun)
- Stop after games start

**Recommended:** Start with Option 1, add Option 2 later if needed.

---

## Cost Comparison

### **Free Tier (ESPN Only)**
- Cost: $0/month
- Reliability: 90% (API can be flaky)
- Best for: Development, testing

### **Paid Tier (ESPN + SportsData.io)**
- Cost: $19/month
- Reliability: 99.9% (SLA guaranteed)
- Best for: Production, real money betting

### **LLM Fallback (OpenAI)**
- Cost: ~$0.50/month (only when ESPN fails)
- Reliability: 95% (depends on news availability)
- Best for: Edge cases, breaking news

**Total recommended cost: $19.50/month for bulletproof injury data**

---

## Next Steps

### **Immediate (Today):**
1. ✅ Fix ESPN API parser
2. ✅ Test with all 32 teams
3. ✅ Verify MIN @ DET shows Wentz injury

### **This Week:**
1. Add database storage for injury history
2. Set up Wednesday/Friday/Sunday cron jobs
3. Add validation and error handling

### **Next Week:**
1. Consider SportsData.io for production
2. Add injury change alerts
3. Track CLV by injury timing

---

## Question: Which approach do you prefer?

**Option A: Free (ESPN + LLM fallback)**
- $0/month
- Good enough for most weeks
- May miss occasional updates

**Option B: Paid (ESPN + SportsData.io + LLM)**
- $19/month
- Professional-grade reliability
- Never miss an injury

**Option C: Build our own scraper**
- $0/month but high maintenance
- Breaks when websites change
- Not recommended

**My recommendation: Start with Option A, upgrade to Option B when you're betting real money.**

---

## Let me fix the ESPN API parser now

Want me to:
1. Rebuild the ESPN parser with proper error handling
2. Test it on all 32 teams
3. Verify it catches the Wentz injury
4. Add database storage for injury history

**This will give you a reliable, consistent source of injury data that updates 3x per week automatically.**

