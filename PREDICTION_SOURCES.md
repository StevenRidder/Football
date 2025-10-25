# NFL Prediction Sources & APIs

## 🆓 FREE Sources (Recommended to Add)

### 1. ESPN FPI (Football Power Index) ✅ USING
- **What**: ESPN's proprietary power ranking and win probability system
- **Data**: Win probabilities, game projections, team rankings
- **API**: Already using ESPN - just need to extract FPI data
- **Cost**: FREE (public API)
- **Accuracy**: Generally 55-60% ATS

### 2. FiveThirtyEight ELO Ratings 🔄 PARTIAL
- **What**: ELO-based NFL predictions (like chess ratings)
- **Data**: Win probabilities, QB adjustments, ELO ratings
- **API**: https://projects.fivethirtyeight.com/nfl-api/nfl_elo_latest.csv
- **Cost**: FREE (public CSV)
- **Accuracy**: ~58% straight-up wins

### 3. TheOddsAPI Implied Probabilities ✅ USING
- **What**: Convert betting lines to win probabilities
- **Data**: Spread/ML odds → implied win %
- **API**: Already using for lines
- **Cost**: 500 requests/month FREE
- **Accuracy**: Vegas consensus (typically 52-53% ATS)

### 4. PFF (Pro Football Focus) Predictions 🆓 LIMITED
- **What**: Analytics-based predictions
- **Data**: Limited free predictions on their site
- **API**: No free API (need to scrape or pay $50/mo)
- **Cost**: FREE (web scraping) or $50/mo (API)
- **Accuracy**: ~60% overall

## 💰 PAID Sources (High Quality)

### 5. SportsData.io ($49-$199/mo)
- **What**: Comprehensive NFL data + predictions
- **Data**: Game predictions, player props, injuries, stats
- **API**: REST API with SDKs
- **Plans**:
  - Trial: $0 (1,000 calls)
  - Starter: $49/mo (10K calls)
  - Pro: $199/mo (100K calls)
- **Accuracy**: ~58-62%

### 6. RunDown API ($99-$299/mo)
- **What**: Real-time odds + consensus predictions
- **Data**: Multiple sportsbook lines, injuries, trends
- **API**: WebSocket + REST
- **Plans**:
  - Basic: $99/mo
  - Pro: $199/mo
  - Enterprise: $299/mo
- **Accuracy**: Consensus-based (varies)

### 7. API-Football ($0-$120/mo)
- **What**: Alternative sports data provider
- **Data**: Predictions, odds, standings, fixtures
- **API**: REST API
- **Plans**:
  - Free: 100 calls/day
  - Basic: $15/mo (5K calls)
  - Pro: $60/mo (30K calls)
  - Ultra: $120/mo (unlimited)
- **Accuracy**: ~55-58%

## 🔄 SCRAPING Options (Not Recommended but Possible)

### 8. CBS Sports Expert Picks
- **Source**: https://www.cbssports.com/nfl/picks/
- **Data**: Expert consensus picks
- **Method**: Web scraping (BeautifulSoup)
- **Issues**: No API, against ToS, fragile

### 9. USA Today Expert Picks
- **Source**: https://www.usatoday.com/sports/nfl/
- **Data**: Staff predictions
- **Method**: Web scraping
- **Issues**: No API, legal concerns

### 10. NFL.com Predictions
- **Source**: https://www.nfl.com/
- **Data**: Official NFL predictions (limited)
- **Method**: Web scraping
- **Issues**: No public API

### 11. NBC Sports Predictions
- **Source**: https://www.nbcsports.com/nfl
- **Data**: Analyst picks
- **Method**: Web scraping
- **Issues**: No API

### 12. Opta Supercomputer 📊
- **Source**: https://www.optasports.com/ (via The Analyst)
- **Data**: Advanced analytics predictions
- **Method**: No public API (need to scrape The Analyst site)
- **Issues**: Data shown on The Analyst website, no direct API

## 🎯 RECOMMENDED IMPLEMENTATION PLAN

### Phase 1: Add FREE Sources (This Weekend)
1. ✅ ESPN FPI - Extract from existing ESPN API calls
2. ✅ 538 ELO - Already attempted, refine implementation
3. ✅ TheOddsAPI - Convert to implied probabilities
4. 🆕 Add consensus calculation from multiple books

### Phase 2: Consider ONE Paid Source (If Budget Allows)
**Best Value**: SportsData.io ($49/mo)
- Comprehensive data
- Includes predictions + injuries + props
- Good documentation
- 10K calls/month is plenty

**Alternative**: API-Football FREE tier
- 100 calls/day = enough for weekly updates
- Test before committing to paid

### Phase 3: Compare Your Model
Create a comparison dashboard showing:
- Your Model
- ESPN FPI
- 538 ELO
- Vegas Consensus (TheOddsAPI)
- (Optional) SportsData.io

Track accuracy over weeks:
- Straight-up wins
- Against the spread
- Over/Under accuracy
- Confidence-weighted Brier score

## 🏆 MODEL ACCURACY BENCHMARKS

| Model | Straight-Up | ATS | O/U |
|-------|------------|-----|-----|
| Vegas Lines | N/A | 52.4% | 49.8% |
| ESPN FPI | 55-60% | 52-55% | ~50% |
| FiveThirtyEight | ~58% | ~53% | N/A |
| PFF | ~60% | 54-56% | ~51% |
| **Your Goal** | **60%+** | **55%+** | **52%+** |

## 📊 WHAT EACH SOURCE IS BEST FOR

- **ESPN**: Quick win probabilities, mainstream appeal
- **538**: Statistical rigor, transparent methodology
- **Vegas**: Crowd wisdom, sharp money
- **SportsData.io**: Comprehensive package, best for serious betting
- **Your Model**: Custom calibration, specific edges

## 🚀 NEXT STEPS

1. I'll add ESPN FPI extraction (5 min)
2. Fix 538 integration (10 min)
3. Add implied probabilities from odds (5 min)
4. Create comparison table in UI (30 min)
5. Track accuracy week-over-week (20 min)

Total: ~70 minutes to add 3 free prediction sources!

Want me to implement Phase 1 now?

