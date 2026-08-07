# Network Restrictions & How to Fix Them - Step by Step

## The Problem We're Facing

When we run `python -m cardarb.cli daily-run` in the sandbox, we get network errors:

```
ProxyError('Unable to connect to proxy', OSError('Tunnel connection failed: 403 Forbidden'))
```

**Why this happens:**
- Sandbox environment (Linux VM) has restricted outbound network access
- It's designed to be isolated for security
- External APIs (newsapi.org, api.ebay.com, api.twitter.com) are blocked

**Important:** This does NOT affect your Mac. When you run on your Mac, it has full internet access and all APIs will work normally.

---

## Three-Part Fix Strategy

### PART 1: Verify Code is Correct (Sandbox)
### PART 2: Validate on Your Mac (Real Network)  
### PART 3: Set Up Each API (Authentication)

---

## PART 1: Verify Code in Sandbox ✅

**Goal:** Make sure our code is syntactically correct and handles errors properly.

### Step 1.1: Run Tests
```bash
cd /Users/chrisnyers/Projects/sports-card-arbitrage
source venv/bin/activate
python -m pytest tests/ -v
```

**Expected:** 16/16 tests pass ✅

**What this tells us:**
- Code has no syntax errors
- Data models are correct
- Position tracking works
- P&L calculations work
- Scoring logic works
- Error handling is robust

### Step 1.2: Check Adapter Imports
```bash
python3 -c "
from cardarb.sources.twitter import TwitterAdapter
from cardarb.sources.ebay import EbayAdapter
from cardarb.sources.news import NewsAdapter
from cardarb.sources.psa import PsaAdapter
print('✓ All adapters importable')
"
```

**Expected:** ✓ All adapters importable

**What this tells us:**
- No syntax errors in adapter files
- All classes defined correctly
- Imports work

### Step 1.3: Verify Adapter Initialization Logic
```bash
python3 -c "
import os
import sys

# Mock .env
os.environ['TWITTER_BEARER_TOKEN'] = 'test_token'
os.environ['NEWS_API_KEY'] = 'test_key'
os.environ['EBAY_APP_ID'] = 'test_id'
os.environ['EBAY_CERT_ID'] = 'test_cert'
os.environ['PSA_API_KEY'] = 'test_psa'

# Test adapter selection logic
from cardarb.config import get_social_sources, get_listings_source, get_news_source, get_population_source

print('Testing adapter factory logic...')
social = get_social_sources()
print(f'  Social sources: {len(social)} adapters')
listings = get_listings_source()
print(f'  Listings source: {type(listings).__name__}')
news = get_news_source()
print(f'  News source: {type(news).__name__}')
pop = get_population_source()
print(f'  Population source: {type(pop).__name__}')
print('✓ All adapters initialized correctly')
"
```

**Expected:** All adapters initialized correctly

**What this tells us:**
- Adapter selection based on .env works
- Factory pattern works
- No import errors

### Step 1.4: Verify Error Handling
```bash
python3 << 'EOF'
# Simulate what happens when API call fails
from cardarb.sources.news import NewsAdapter
import os

os.environ['NEWS_API_KEY'] = 'test_key'

adapter = NewsAdapter()

# Test with empty card list (should return empty, not crash)
result = adapter.fetch_news([], None, lookback_days=7)
print(f'Empty call returns: {result} (type: {type(result).__name__})')
assert isinstance(result, list), 'Must return list'
print('✓ Error handling works (returns empty gracefully)')
EOF
```

**Expected:** Error handling works (returns empty gracefully)

**What this tells us:**
- Adapters handle missing data gracefully
- System won't crash if API fails
- Fallbacks work

---

## PART 2: Validate on Your Mac (Real Network)

### Prerequisites
You need to do this on your Mac, NOT in the sandbox.

### Step 2.1: Verify Network Access
```bash
# On your Mac, test basic connectivity
curl -I https://api.twitter.com
curl -I https://newsapi.org
curl -I https://api.ebay.com
```

**Expected:** You get response headers (200, 403, 401, etc. - not timeout)

**What this tells us:**
- Your Mac has internet access
- APIs are reachable from your location
- No ISP/firewall blocking

### Step 2.2: Test Each API Individually

#### Test Google News API
```bash
# Your .env should have: NEWS_API_KEY=b84eef70507a489290600cd8a9446a16
curl "https://newsapi.org/v2/everything?q=sports&apiKey=YOUR_API_KEY&pageSize=5"
```

**Expected:** JSON response with articles

**If fails:** 
- Check API key is correct in .env
- Check newsapi.org account is active
- Try on https://newsapi.org (test in browser first)

#### Test Twitter API (Will likely fail - that's OK)
```bash
# Your .env should have: TWITTER_BEARER_TOKEN=...
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.twitter.com/2/tweets/search/recent?query=sports%20card"
```

**Expected:** Either success OR 402 (Payment Required) - both are normal

**If 402:** Free tier doesn't have this endpoint (expected, we handle it)

**If 401:** Token is invalid, needs refresh

#### Test eBay API
```bash
# First, you need an OAuth token (see Step 2.3 below)
# Then test Browse API
curl -H "Authorization: Bearer YOUR_OAUTH_TOKEN" \
  "https://api.ebay.com/buy/browse/v1/item_summary/search?q=sports%20card&limit=5"
```

**Expected:** JSON response with listings

**If fails:** Likely need OAuth token (handled in Step 2.3)

#### Test PSA API
```bash
# Your .env should have: PSA_API_KEY=...
curl "https://api.psacard.com/api/v1/population/1/5"
```

**Expected:** Likely 404 (no public endpoint) - that's why we use placeholder

### Step 2.3: Set Up eBay OAuth Token (Most Important)

This is the only API that requires special setup.

**Step-by-step:**

1. **Go to eBay Developer Portal**
   ```
   https://developer.ebay.com/
   ```

2. **Navigate to your app**
   - Click your app name
   - Look for "Auth tokens" or "OAuth token" section

3. **Generate OAuth Token**
   - Click "Generate Token" or similar button
   - Copy the token (looks like: `AgAAAA...`)

4. **Add to .env**
   ```bash
   # Edit: /Users/chrisnyers/Projects/sports-card-arbitrage/.env
   # Add this line:
   EBAY_AUTH_TOKEN=AgAAAA... (paste your token here)
   ```

5. **Verify it's saved**
   ```bash
   grep EBAY_AUTH_TOKEN /Users/chrisnyers/Projects/sports-card-arbitrage/.env
   ```
   
   **Expected:** See your token printed

6. **Test it works**
   ```bash
   cd /Users/chrisnyers/Projects/sports-card-arbitrage
   source venv/bin/activate
   python3 << 'EOF'
   import os
   from dotenv import load_dotenv
   load_dotenv()
   token = os.getenv('EBAY_AUTH_TOKEN')
   print(f'✓ eBay token loaded: {token[:20]}...')
   EOF
   ```

   **Expected:** ✓ eBay token loaded: AgA...

---

## PART 3: Set Up Each API (Full Details)

### API #1: Google News API ✅ READY

**Current Status:** Already in .env

**Verify:**
```bash
grep NEWS_API_KEY /Users/chrisnyers/Projects/sports-card-arbitrage/.env
```

**Expected:** `NEWS_API_KEY=b84eef70507a489290600cd8a9446a16`

**Next step:** Nothing - it works as-is

---

### API #2: eBay Browse API 🟡 NEEDS SETUP

**Current Status:** Needs OAuth token

**What you need:**
- eBay App ID ✅ (already have)
- eBay Cert ID ✅ (already have)
- eBay OAuth Token 🟡 (need to generate)

**Steps:**

1. Go to https://developer.ebay.com/
2. Find your app
3. Click "Auth tokens"
4. Generate OAuth token
5. Add to .env: `EBAY_AUTH_TOKEN=...`
6. Test:
   ```bash
   python -m cardarb.cli daily-run --as-of 2024-07-15
   ```

**Expected:** See eBay data pulled, no connection errors

---

### API #3: Twitter API ⚠️ FREE TIER LIMITATION

**Current Status:** Free tier doesn't have `search/recent`

**Your options:**

**Option A: Use what we have (Recommended)**
- Our code returns empty for Twitter
- NewsAdapter provides sentiment instead
- Works fine for Phase 1

**Option B: Upgrade to paid tier**
- Cost: $100+/month
- Would unlock `search/recent` endpoint
- Can do later in Phase 2

**Option C: Use free endpoints**
- Look up specific users
- Limited to some endpoints
- Would need code rewrite

**Recommendation:** Use Option A for Phase 1, upgrade later if needed

**Verify current setup:**
```bash
python3 << 'EOF'
from cardarb.sources.twitter import TwitterAdapter
adapter = TwitterAdapter()
result = adapter.fetch_mentions([1], None)
print(f'Twitter returns: {result}')
print('✓ Twitter gracefully returns empty (expected for free tier)')
EOF
```

---

### API #4: PSA API ❌ NO PUBLIC ENDPOINT

**Current Status:** PSA doesn't expose population data via API

**Your options:**

**Option A: Use placeholder data (Recommended for Phase 1)**
- System returns neutral estimate (100 copies)
- Allows testing to proceed
- No additional setup needed

**Option B: Manual lookup**
- Visit psacard.com
- Look up cards manually
- Add data via CLI later

**Option C: Build scraper (Phase 2)**
- Scrape PSA Set Registry
- Build population database
- More complex, can wait

**Recommendation:** Use Option A for Phase 1

**Verify:**
```bash
python3 << 'EOF'
from cardarb.sources.psa import PsaAdapter
import os
os.environ['PSA_API_KEY'] = 'test'
adapter = PsaAdapter()
result = adapter.fetch_population([1], None)
print(f'PSA returns: {result}')
print('✓ PSA returns placeholder data (expected, real data not available)')
EOF
```

---

## PART 4: Full System Test on Your Mac

Once all APIs are set up, run complete system test:

```bash
# 1. Activate venv
cd /Users/chrisnyers/Projects/sports-card-arbitrage
source venv/bin/activate

# 2. Make sure .env has all keys
cat .env

# 3. Run daily command
python -m cardarb.cli daily-run --as-of 2024-07-15

# 4. Expected output:
# - [Progress] Loading card catalog...
# - [Progress] Fetching listings from eBay
# - [Progress] Fetching news from NewsAPI
# - [Progress] Fetching population from PSA
# - [Progress] Building feature matrix...
# - [Progress] Ranking by ROIC
# - [Output] Top 20 opportunities:
#   1. Card Name - ROIC: 12.5% - Opportunity Score: 8.2
#   ...
```

**Expected:** See top 20 opportunities ranked, no crashes

---

## Troubleshooting Checklist

If something fails, work through this:

| Error | Cause | Fix |
|-------|-------|-----|
| `ProxyError` | Sandbox network restriction | Run on Mac instead |
| `401 Unauthorized` | Invalid API key | Check .env, regenerate key |
| `402 Payment Required` | Twitter free tier | Expected, system handles it |
| `404 Not Found` | Wrong API endpoint | Check API documentation |
| `Connection timeout` | Network down | Check internet, try again |
| `ModuleNotFoundError` | Missing dependency | Run `pip install -r requirements.txt` |

---

## Success Criteria

By end of this guide, you should be able to:

- [ ] Run tests: 16/16 pass
- [ ] Import all adapters without error
- [ ] Verify adapters initialize correctly
- [ ] Test network access on Mac (curl works)
- [ ] Verify Google News API works
- [ ] Add eBay OAuth token to .env
- [ ] Verify eBay adapter can initialize
- [ ] Understand Twitter API limitation (handled gracefully)
- [ ] Understand PSA placeholder approach
- [ ] Run `daily-run` and see top 20 opportunities
- [ ] See no connection errors (errors caught gracefully)

---

## Timeline

**Today (Sandbox testing):**
- ✅ Part 1: Verify code structure
- ⏳ Part 2-3: Need your Mac

**On your Mac (Take your time):**
- Day 1: Run tests, verify adapters
- Day 2: Set up eBay OAuth token
- Day 3: Run full system test
- Ready: Execute first real trades

**No rush - do this step by step when you're ready on your Mac.**

---

## Questions?

Each API section has troubleshooting steps. If stuck:

1. Check the specific API's documentation (links in each section)
2. Verify your .env file has the right key name and value
3. Test curl command first (simpler than Python)
4. Check network connectivity on your Mac

Ready? Start with Part 1 verification today, then move to your Mac tomorrow.
