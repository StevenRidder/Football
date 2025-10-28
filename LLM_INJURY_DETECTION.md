# LLM-Powered Injury Detection

## Problem

**You're right - we're missing critical injuries!**

Example: Vikings game (MIN @ DET)
- **Carson Wentz is out for the season** (shoulder surgery)
- **Sam Darnold is the starter** (backup quality)
- **Market hasn't fully adjusted** (-8.5 spread seems light)
- **Our system shows NO signals** ❌

**Root cause:** ESPN API is not returning injury data, or the structure has changed.

---

## Solution: Use LLMs with Real-Time Web Search

### **Why LLMs?**

1. **Real-time news access** - LLMs with web search can find breaking injury news
2. **Natural language understanding** - Can parse injury reports, tweets, press conferences
3. **Source citation** - Perplexity AI cites sources for verification
4. **Fast and cheap** - $0.20 per 1M tokens (Perplexity)
5. **Structured output** - Can return JSON for easy integration

### **Best Option: Perplexity AI**

**Perplexity AI** is purpose-built for this:
- Real-time web search built-in
- Cites sources (NFL.com, ESPN, team sites)
- Fast responses (< 3 seconds)
- Affordable ($0.20 per 1M tokens = ~$0.0002 per game)
- No separate search API needed

**Model:** `llama-3.1-sonar-small-128k-online`
- "sonar" = web search enabled
- "online" = real-time results
- "small" = fast and cheap

---

## Implementation

### **1. Get Perplexity API Key**

Visit: https://www.perplexity.ai/settings/api

Cost: $0.20 per 1M tokens
- ~1,000 tokens per game analysis
- ~$0.0002 per game
- ~$0.003 for full 14-game slate

### **2. Set Environment Variable**

```bash
export PERPLEXITY_API_KEY='your-key-here'
```

Or add to `.env` file:
```
PERPLEXITY_API_KEY=your-key-here
```

### **3. Test the Detector**

```bash
cd /Users/steveridder/Git/Football
python3 edge_hunt/llm_injury_detector.py
```

This will:
1. Search for injuries for MIN @ DET
2. Parse the results
3. Calculate point impacts
4. Display findings

### **4. Integrate into Edge Hunt**

Update `edge_hunt/integrate_signals.py` to:
1. Try ESPN API first (fast, free)
2. Fall back to LLM detector if ESPN fails
3. Cache results for 1 hour

---

## Expected Output

### **For MIN @ DET:**

```
Found 2 injuries:

  MIN - Carson Wentz (QB)
    Status: out
    Impact: high
    Source: nfl.com

  MIN - Sam Darnold (QB)
    Status: active (backup starting)
    Impact: medium
    Source: espn.com

📊 Point Impacts:
  MIN: -6.0 points
```

### **Betting Adjustment:**

**Market:** DET -8.5, Total 47.5
- Implied: MIN 20, DET 28

**Our Adjustment (with Wentz out):**
- MIN loses 6 points → MIN 14, DET 28
- New spread: DET -14
- New total: 42

**Recommendation:**
- ✅ **BET DET -8.5** (6-point edge!)
- ✅ **BET UNDER 47.5** (5-point edge!)

---

## Alternative APIs

If you don't want to use Perplexity, here are alternatives:

### **Option 2: OpenAI with Web Search**
- Use GPT-4 with Bing search plugin
- More expensive (~$0.03 per game)
- Requires separate Bing API key

### **Option 3: Anthropic Claude with Web Search**
- Use Claude with web search tool
- Similar cost to OpenAI
- Requires separate search API

### **Option 4: SportsData.io**
- Dedicated sports API
- $19/month for injury data
- More reliable than ESPN
- No LLM needed

### **Option 5: RapidAPI Sports**
- Multiple NFL APIs available
- $10-50/month depending on calls
- Structured data (easier to parse)

---

## Recommendation

**Start with Perplexity AI:**

**Pros:**
- ✅ Real-time news (catches breaking injuries)
- ✅ Cheap ($0.003 per week)
- ✅ Easy to integrate
- ✅ Cites sources for verification
- ✅ Handles edge cases (backup QB, 3rd string, etc.)

**Cons:**
- ❌ Requires API key
- ❌ Slightly slower than direct API (3s vs 0.5s)
- ❌ Needs JSON parsing

**Fallback:**
- Keep ESPN API as primary (free, fast)
- Use Perplexity when ESPN returns no data
- Cache results for 1 hour

---

## Integration Steps

### **Step 1: Add to `integrate_signals.py`**

```python
from edge_hunt.llm_injury_detector import detect_injuries_perplexity, calculate_injury_impact

def get_edge_hunt_signals(...):
    # ... existing weather code ...
    
    # Try LLM injury detection
    injuries = detect_injuries_perplexity(away, home)
    if injuries:
        impacts = calculate_injury_impact(injuries)
        
        away_impact = impacts.get(away, 0.0)
        home_impact = impacts.get(home, 0.0)
        
        # Apply to scores
        adjusted_away -= abs(away_impact)
        adjusted_home -= abs(home_impact)
        
        # Create signals for significant injuries
        if away_impact < -3.0:
            signals.append({
                'type': 'injury',
                'icon': '🏈',
                'badge': 'BACKUP QB',
                'edge_pts': abs(away_impact),
                ...
            })
```

### **Step 2: Update Pre-compute Script**

```python
# precompute_edge_hunt_signals.py
# Add at the top:
import os
os.environ['PERPLEXITY_API_KEY'] = 'your-key'  # Or load from .env
```

### **Step 3: Test**

```bash
python3 precompute_edge_hunt_signals.py
```

Should now show:
```
MIN @ DET: 🏈 BACKUP QB, 🌪️ HIGH WIND
```

---

## Cost Analysis

### **Per Week (14 games):**
- Perplexity API: $0.003
- Total: **$0.003 per week**

### **Per Season (18 weeks):**
- Total: **$0.054 per season**

**Conclusion:** Essentially free for the value it provides!

---

## Next Steps

1. **Get Perplexity API key** (5 minutes)
2. **Test the detector** (see if it finds Wentz injury)
3. **Integrate into Edge Hunt** (update `integrate_signals.py`)
4. **Re-run pre-compute** (regenerate signals with injuries)
5. **Verify on web app** (should see MIN @ DET signals)

**Want me to do steps 3-5 now?** Just provide your Perplexity API key and I'll integrate it!


