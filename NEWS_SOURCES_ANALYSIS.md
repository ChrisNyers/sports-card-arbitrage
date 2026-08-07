# News Sources Strategy: Building Real-Time Model Signals

**Purpose:** Evaluate current news sources for real-time model training and identify critical gaps.

---

## Current Setup: Google News API Only

### What We Have
```
Google News API (NewsAPI.org)
├── Coverage: General sports + player mentions
├── Latency: 6-12 hours behind events
├── Queries: "{player_name} sports"
├── Sentiment: 13 keywords (record, injury, trade, etc.)
└── Cache: 24-hour reuse (90% reduction in API calls)
```

### Current Sentiment Keywords
**Positive (Bullish):** record, milestone, trade, contract, signed, deal  
**Negative (Bearish):** injury, retired, decline, miss, suspend

---

## 🚨 Critical Gaps Identified

### Gap #1: Latency Problem
**Issue:** Google News averages 6-12 hour delay from actual event  
**Example:** 
- 9:00 AM: Player suffers injury in game
- 3:00 PM: News breaks on ESPN/Twitter
- 9:00 PM+: Reaches Google News → Your system detects it
- **Result:** Card already repricing for 6+ hours, you're late**

**Impact:** Loses 40-60% of the "first mover" advantage

### Gap #2: Coverage Blindness
**Issue:** Google News misses/buries beat reporter alerts  
**Missing:**
- Team injury reports (official sources)
- Beat reporter threads (first real-time confirmation)
- Waiver wire moves (NBA player transactions)
- Minor league call-ups (baseball)
- Draft pick details (NFL)
- Trade rumors (before official announcement)

**Impact:** You never see the rumor phase—only the confirmed news phase

### Gap #3: Sentiment Scoring Too Simple
**Current:** Count positive/negative keywords  
**Problems:**
- Misses nuance ("injury concern" vs "injury confirmed")
- No context ("traded UP vs traded DOWN")
- No weighting ("career-ending injury" vs "finger sprain")
- No source credibility ("ESPN report" vs random blog)

**Example:**
- Headline: "Star player likely to miss rest of season"
  - Current scoring: +0.1 (contains "miss") → BULLISH WRONG
  - Should be: 0.2 (confirm missing games) → BEARISH CORRECT

### Gap #4: No Real-Time Alerts
**Issue:** You check news once per day (`daily-run`)  
**Reality:** Events happen 24/7  
- Player gets injured during game (10 AM)
- You run daily-run (3 PM) — already 5 hours behind
- Card already down 20%

---

## 📰 Recommended News Source Stack

### **TIER 1: Real-Time Event Detection** (0-2 hour latency)

#### 1. **ESPN API / ESPN Alerts** ⭐⭐⭐
**What:** Official injury reports, roster moves, game updates  
**Why:** First source of truth for player status  
**Latency:** 15-30 minutes (fastest)  
**Coverage:** All major sports (NFL, NBA, MLB, NHL, MLS)  
**Cost:** Free (unofficial scraping) or $500/month (official)

**Signals to track:**
- Injury status (OUT, DAY_TO_DAY, QUESTIONABLE, PROBABLE)
- Return date updates
- Trade confirmations
- Contract news

**Integration:**
```python
class ESPNAdapter:
    """ESPN injury reports + roster moves"""
    
    def fetch_events(self, card_ids, as_of_date):
        # Check ESPN injury reports
        for player in card_ids:
            injury = scrape_espn_injuries(player)
            if injury.status_changed:
                yield EventRecord(
                    event_type="injury",
                    severity=injury.severity,
                    impact="NEGATIVE",
                    latency="15-30 min"
                )
```

**Cost:** Free (scraper) | $500/mo (official)  
**Effort:** Medium (web scraper)  
**ROI:** CRITICAL — catches injuries before market reacts

---

#### 2. **Beat Reporters (Twitter/Reddit monitoring)** ⭐⭐⭐
**What:** Team-specific journalists breaking news first  
**Why:** They often report 30-60 mins before ESPN confirms  
**Latency:** 30-60 minutes (second fastest)  
**Coverage:** All sports (by beat reporter following)  
**Cost:** Free (monitor public feeds)

**Key accounts to monitor:**
```
NFL:
- @AdamSchefter (ESPN - trade master)
- @RapSheet (Ian Rapoport - breaking news)
- Team beat reporters (team-specific)

NBA:
- @ShamsCharania (ESPN/The Athletic)
- @Adrian Wojnarowski (ESPN)
- Team beat reporters

MLB:
- @MLBersSays 
- @Buster_ESPN (Buster Olney)
- Team beat reporters

Each sport/team has 5-10 beat reporters worth following
```

**Signals:**
- "Player X ruled out for season" (live tweet)
- "Trade agreed: Player to Team" (15 min before official)
- "Coach confirms injury timeline: 4-6 weeks"

**Integration:**
```python
class BeatReporterAdapter:
    """Monitor beat reporters for breaking news"""
    
    def fetch_events(self, card_ids, as_of_date):
        # Monitor specific Twitter accounts
        accounts = get_beat_reporters(card_ids)
        
        for account in accounts:
            tweets = fetch_recent_tweets(account, last_2_hours)
            
            for tweet in tweets:
                if matches_any_player(tweet, card_ids):
                    event = parse_event_from_tweet(tweet)
                    yield event
```

**Cost:** Free (Twitter API v2, $100/mo for paid tier)  
**Effort:** Medium (need Twitter scraper)  
**ROI:** CRITICAL — 2-4 hours ahead of Google News

---

#### 3. **Official Team/League Sources** ⭐⭐
**What:** Direct team announcements (injury reports, roster moves)  
**Why:** Authoritative source, sometimes first to announce  
**Latency:** Varies (30 min - 2 hours)  
**Coverage:** All teams (need to monitor each)  
**Cost:** Free (public announcements)

**Channels:**
- NFL: NFL.com injury reports, team official sites
- NBA: NBA.com official injury list
- MLB: MLB.com transactions, team press releases
- RSS feeds from each team

**Integration:**
```python
class OfficialSourcAdapter:
    """Monitor official team/league sources"""
    
    def fetch_events(self, card_ids, as_of_date):
        # Check NBA.com official injury list
        injuries = scrape_nba_injuries()
        
        # Check NFL.com official transaction list
        transactions = scrape_nfl_transactions()
        
        # Parse for card_ids
        for injury in injuries:
            if injury.player_id in card_ids:
                yield EventRecord(...)
```

**Cost:** Free  
**Effort:** Medium (multiple scrapers)  
**ROI:** HIGH — official confirmation

---

### **TIER 2: Context & Analysis** (2-6 hour latency)

#### 4. **The Athletic / Paywalled Sports Journalism** ⭐⭐
**What:** Expert analysis + breaking news from credible journalists  
**Why:** Deeper context (trade implications, career outlook)  
**Latency:** 1-4 hours (before mainstream)  
**Coverage:** All sports  
**Cost:** $150/year

**Signals:**
- "This injury ends [player]'s season" (expert take)
- "Trade market heating up for [player]" (scoop)
- "Rookie sensation ready to break out" (positive signal)

**Integration:** Custom scraper or API

**Cost:** $150/year subscription  
**Effort:** High (need scraper + auth)  
**ROI:** MEDIUM — context matters, but late

---

#### 5. **Reddit (r/sportscards + team subreddits)** ⭐⭐
**What:** Community discussion, expert opinions from collectors/dealers  
**Why:** Dealers/graders discuss trends early; early sentiment shift  
**Latency:** 1-6 hours (discussion lags but precedes Google News)  
**Coverage:** All sports + commentary  
**Cost:** Free (PRAW API)

**Subreddits to monitor:**
```
r/sportscards (general)
r/cardgrading (grading trends)
r/nba, r/baseball, r/nfl, r/hockey (team-specific)
r/investing (investment angle)
```

**Example signals:**
- "Everyone flipping PSA 8s of [player], supply drying up"
- "I'm dumping my [player] cards before injury news gets worse"
- "Just bought 100 copies, expecting [event] to drive demand"
- "Professional dealers selling off [era]—expecting market shift"

**Integration:**
```python
class RedditAdapter:
    """Monitor Reddit for collector sentiment"""
    
    def fetch_sentiment(self, card_ids, as_of_date):
        subreddits = ["sportscards", "nba", "baseball", "cardgrading"]
        
        for subreddit in subreddits:
            posts = fetch_recent_posts(subreddit, last_6_hours)
            
            for post in posts:
                if mentions_any_player(post, card_ids):
                    sentiment = analyze_post_sentiment(post)
                    confidence = score_post_authority(post.author)
                    yield SentimentRecord(...)
```

**Cost:** Free (PRAW)  
**Effort:** Low-Medium (API wrapper exists)  
**ROI:** MEDIUM-HIGH — early sentiment shifts

---

### **TIER 3: Aggregation & Verification** (6-12 hour latency)

#### 6. **Google News** (Current) ⭐
**What:** General sports news aggregation  
**Why:** Good for confirmation, broad coverage  
**Latency:** 6-12 hours (lagging)  
**Coverage:** All sports  
**Cost:** Free

**Role:** Verification layer (confirm events already detected)

---

## 🎯 Recommended Implementation Strategy

### **Phase 1 MVP (Now)**
Keep: Google News (as verification layer)  
Add: Reddit monitoring (low effort, good sentiment)  

```python
# Add to daily-run
reddit_sentiment = RedditAdapter().fetch_sentiment(card_ids, as_of_date)
google_news = NewsAdapter().fetch_news(card_ids, as_of_date)

# Combine signals
combined = merge_signals(google_news, reddit_sentiment)
```

**Effort:** 3-4 hours  
**Impact:** +2-3% accuracy improvement  
**Latency improvement:** 2-4 hours earlier detection  

---

### **Phase 2 MVP** (Week 1-2)
Add: Beat reporter monitoring (Twitter scraper)  
Add: ESPN injury scraper  
Keep: Google News + Reddit

```python
# Real-time event detection
beat_reporters = BeatReporterAdapter().fetch_events(card_ids, as_of_date)
espn_injuries = ESPNAdapter().fetch_events(card_ids, as_of_date)

# Cross-validate events
events = validate_events(beat_reporters, espn_injuries)
```

**Effort:** 6-8 hours (scraper work)  
**Impact:** +5-8% accuracy improvement  
**Latency improvement:** 4-6 hours earlier detection  

---

### **Phase 3 Full Stack** (Month 2+)
Add: Official sources (team/league announcements)  
Add: The Athletic (expert analysis)  
Upgrade: Twitter API to paid tier  
Keep: Everything else

**Effort:** 12-16 hours  
**Impact:** +8-12% accuracy improvement  
**Latency improvement:** 6-8 hours earlier detection  

---

## 📊 News Source Comparison Matrix

| Source | Latency | Accuracy | Coverage | Cost | Effort | ROI |
|--------|---------|----------|----------|------|--------|-----|
| **Beat Reporters** | 30-60 min | High | 80% | Free | Medium | ⭐⭐⭐ |
| **ESPN** | 15-30 min | Very High | 95% | Free/500 | Medium | ⭐⭐⭐ |
| **Official Sources** | 30 min-2 hr | Very High | 100% | Free | Medium | ⭐⭐⭐ |
| **Reddit** | 1-6 hrs | Medium | 70% | Free | Low | ⭐⭐ |
| **The Athletic** | 1-4 hrs | High | 85% | $150/yr | High | ⭐⭐ |
| **Google News** | 6-12 hrs | Medium | 90% | Free | None | ⭐ |

---

## 🔄 Real-Time vs Batch Processing

### Current (Batch - Once per day)
```
3 PM: python -m cardarb.cli daily-run
      (Fetches news from last 24 hours)
      (Event already 6-12 hours old)
      → TOO LATE
```

### Recommended (Real-Time - Continuous)
```
Continuous monitoring:
- Beat reporters: Check every 15 minutes
- ESPN: Check every 30 minutes
- Reddit: Check every 30 minutes
- Google News: Check every 2 hours (verification)

→ Detects events 4-6 hours EARLIER
→ First-mover advantage in market mispricing
```

**For Phase 1 MVP:** Keep batch (daily-run) but add Reddit  
**For Phase 2+:** Implement streaming/hourly checks  

---

## 💡 Sentiment Enhancement Opportunities

### Current Sentiment Scoring (Too Simple)
```python
positive_keywords = ["record", "milestone", "trade", "contract", "signed", "deal"]
negative_keywords = ["injury", "retired", "decline", "miss", "suspend"]
sentiment = 0.5 + (pos_count - neg_count) * 0.1
```

**Problems:**
- "Injured" counts as -1 whether it's a paper cut or career-ending
- "Traded" counts as +1 whether it's an upgrade or downgrade
- No context weighting

### Recommended Enhancement
```python
SENTIMENT_RULES = [
    # Injuries (severity-weighted)
    (r"\bcareer-ending|permanent|never return\b", "injury", -0.8),
    (r"\bseason-ending|out for season\b", "injury", -0.6),
    (r"\bout indefinitely|long-term\b", "injury", -0.5),
    (r"\bout (\d+ weeks?|rest of season)\b", "injury", -0.4),
    (r"\bday-to-day|probable\b", "injury", -0.2),
    
    # Trades (context-dependent)
    (r"\btraded to (champion|contender|playoff team)\b", "trade", +0.5),
    (r"\btraded to (rebuilding|tanking)\b", "trade", -0.3),
    
    # Milestones (quality-weighted)
    (r"\bHall of Fame|1000th career\b", "milestone", +0.7),
    (r"\b(10th|20th) consecutive\b", "milestone", +0.4),
    (r"\brecord-breaking|new mark\b", "milestone", +0.5),
    
    # Actual Performance
    (r"\b(steals|blocks|assists|home runs) (leader|leading|record)\b", "performance", +0.6),
    (r"\b(slump|struggles|decline|regression)\b", "performance", -0.4),
]
```

---

## 🚨 What's Missing That Hurts Accuracy

1. **Injury Severity Not Encoded** — All injuries treated equal
   - Paper cut = Career ender? NO.
   - Solution: Parse injury descriptions for severity keywords

2. **No Recency Weighting** — 1-day-old news treated same as 6-hour-old
   - Solution: Decay sentiment over time (fresh news stronger signal)

3. **No Source Credibility** — ESPN = random blog?
   - Solution: Rank sources by accuracy track record

4. **No Cross-Source Validation** — Single report = automatic signal
   - Solution: Require 2+ sources confirming event

5. **No Market Reaction Context** — Is card repricing up or down yet?
   - Solution: Compare time of news vs time of price move

---

## 📋 Action Plan for Phase 1

### This Week
- [x] Keep Google News (verification)
- [ ] Add Reddit adapter (estimate: 2 hours)
- [ ] Enhance sentiment scoring (estimate: 1 hour)
- [ ] Test combined signals on historical data

### Next 2 Weeks
- [ ] Build beat reporter scraper (estimate: 4 hours)
- [ ] Add ESPN injury scraper (estimate: 4 hours)
- [ ] Implement event validation (2+ source confirmation)
- [ ] A/B test accuracy improvement

### Expected Result
- **Latency:** 6-12 hours → 2-4 hours (3-6x faster)
- **Accuracy:** 67.7% → 72-75% (5-8% improvement)
- **Win Rate:** 70%+ → 75%+ (compound advantage)

---

## Summary: Why News Sources Matter for Your Model

Your model's accuracy depends on **signal quality & latency**:

| Factor | Impact on Win Rate |
|--------|-------------------|
| Detect events 4 hours earlier | +5-8% (first-mover advantage) |
| Better sentiment encoding | +3-5% (less noise) |
| Beat reporters + ESPN | +4-6% (get ahead of Google News) |
| Source validation | +2-3% (avoid false signals) |

**Combined:** 67.7% → 75-80% accuracy possible with better news

---

**Next Step:** Should we build the Reddit adapter now, or focus on ESPN/beat reporter integration first?
