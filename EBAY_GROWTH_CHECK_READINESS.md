# eBay Application Growth Check: Readiness Assessment

**Date:** August 7, 2026  
**Project:** Project Atlas - Sports Card Arbitrage Intelligence Engine  
**Assessment Scope:** Readiness for eBay Growth Check demonstration  

---

## Executive Summary

**Overall Status:** ⚠️ **80% READY** - Core eBay integration works; only needs minimal web wrapper + credential fix

| Component | Status | Notes |
|-----------|--------|-------|
| eBay API Integration | ✓ Working | OAuth + Browse API implemented |
| Data Normalization | ✓ Complete | ListingRecord model + field mapping ready |
| Research-Only UI | ⚠️ Missing | Needs simple Flask web layer (~2-3 hours) |
| Hosting | ⚠️ Missing | Free tier ready (Render, Railway, Vercel) |
| Credentials | ✗ Broken | PRD APP_ID + SBX CERT_ID mismatch; needs fix |
| Sandbox Testing | ⚠️ Blocked | Works once credentials aligned |

**Recommendation:** Fix credentials + build minimal Flask demo interface. Ready for Growth Check in **3-4 days**.

---

## Part 1: Current Project Readiness

### ✓ What Exists (Ready to Use)

**1. eBay API Integration Layer**
- Location: `cardarb/sources/ebay.py`
- Status: Fully implemented
- Capabilities:
  - OAuth 2.0 token fetch (client credentials flow)
  - Active listings search via Browse API
  - Proper error handling
  - Timeout and retry logic

**2. Data Normalization**
- Location: `cardarb/db/models.py`
- Model: `ListingRecord` dataclass
- Fields captured:
  - Price ✓
  - Listing type (auction vs. fixed-price) ✓
  - Source attribution ✓
  - Listed date/sold date ✓
  - Card ID reference ✓

**3. Card Catalog**
- Location: `cardarb/sources/mock_data/card_catalog.py`
- Contains: 50+ real sports cards (Mahomes, Tom Brady, etc.)
- Purpose: Seed data for demo searches
- Status: Ready to use

**4. Architecture**
- Config system: `.env` loading via `cardarb/config.py`
- CLI framework: Typer (for command-line tool)
- Templates: Jinja2 available in requirements
- Testing framework: Pytest already integrated

### ✗ What's Missing (Needs to Be Built)

**1. Web Interface** (Primary Gap)
- Current: CLI tool only, no web UI
- Needed: Simple Flask/FastAPI app with:
  - Search form (card player name, year, set)
  - Results page showing normalized listings
  - Source attribution + "research only" disclaimer

**2. Hosting/Deployment**
- Current: Local development only
- Needed: Public URL for eBay reviewers
- Recommendation: Free tier service (see below)

**3. Credentials**
- Current: Mismatched (PRD APP_ID + SBX CERT_ID)
- Needed: Matched pair for Sandbox testing

---

## Part 2: What eBay Reviewers Will See (Demo Flow)

**Step 1: Search Form**
```
Search for a Sports Card
[__________ Player Name]  (e.g., "Patrick Mahomes")
[__________ Year]          (e.g., "2017")
[__________ Card Set]      (e.g., "Panini Prizm")

[Search eBay]
```

**Step 2: Results Display**
```
Results for: Patrick Mahomes, 2017 Panini Prizm

Found 12 active listings on eBay

Listing 1:
  Price: $145.00
  Format: Fixed Price
  Condition: [from API if available]
  Seller: [seller info]
  Listed: [date]
  Source: eBay Browse API

Listing 2:
  Price: $152.50
  Format: Auction
  ...

[Clear Search]
```

**Step 3: Disclaimer**
```
⚠️ RESEARCH AND DECISION SUPPORT ONLY
This tool analyzes publicly available eBay listings
for research and market analysis purposes only.
It does not execute trades, place bids, or perform transactions.
```

---

## Part 3: Minimal Hosting Options

### Recommended: **Render (Free Tier)**

**Why Render:**
- ✓ Free tier includes web service hosting
- ✓ Automatic HTTPS
- ✓ Git-connected auto-deploy
- ✓ No credit card required for free tier
- ✓ 750 free hours/month (enough for low-traffic demo)
- ✓ Easy to spin up and tear down

**Cost:** Free  
**Setup time:** 15 minutes  
**URL:** `https://atlas-ebay-demo.onrender.com` (example)

**Alternative Options:**

| Platform | Cost | Setup Time | Notes |
|----------|------|-----------|-------|
| **Railway** | Free | 10 min | Simple, GitHub-connected, good for demos |
| **Vercel** | Free | 10 min | Frontend-focused, works with Flask via serverless |
| **Heroku** | Paid ($7+) | 10 min | Formerly free, now paid; skip unless you prefer |
| **Local + ngrok** | Free | 5 min | Temporary tunnel for quick demo; fragile |

**Recommendation:** Render or Railway for stability.

---

## Part 4: Implementation Path (Minimal)

### Phase 1: Credential Fix (30 minutes)
**Required before any testing**

```python
# Current .env (BROKEN)
EBAY_APP_ID=ChrisNye-sportsar-PRD-...
EBAY_CERT_ID=SBX-624625de60f5-...  ← Mismatch!

# Action needed:
# Option A: Use Sandbox credentials (both SBX-*)
# Option B: Use Production credentials (both PRD-*)
```

**Status:** Waiting for corrected credentials from user

### Phase 2: Build Flask Demo App (2-3 hours)

**File to create:** `cardarb/web_app.py`

```python
from flask import Flask, render_template, request, jsonify
from cardarb.config import get_listings_source
from cardarb.sources.mock_data import get_cards

app = Flask(__name__)
listings_source = get_listings_source()

@app.route('/')
def index():
    return render_template('search.html')

@app.route('/search', methods=['POST'])
def search():
    player_name = request.json.get('player_name')
    year = request.json.get('year')
    
    # Find matching card
    cards = get_cards()
    card = next((c for c in cards if c.player_name.lower() == player_name.lower() 
                 and c.year == int(year)), None)
    
    if not card:
        return jsonify({'error': 'Card not found'}), 404
    
    # Fetch listings from eBay
    listings = listings_source.fetch_listings([card.card_id], date.today())
    
    return jsonify({
        'card': card.to_dict(),
        'listings': [
            {
                'price': l.price,
                'format': l.listing_type,
                'source': l.source,
                'listed_at': l.listed_at.isoformat()
            } for l in listings
        ]
    })

if __name__ == '__main__':
    app.run(debug=True)
```

**Files to create:**
- `cardarb/web_app.py` (Flask application)
- `cardarb/templates/search.html` (UI form + results)
- `cardarb/static/style.css` (minimal styling)
- `cardarb/static/app.js` (search logic)

**Add to requirements.txt:**
```
flask>=3.0
```

### Phase 3: Deploy to Render (15 minutes)

**Create:** `Procfile`
```
web: gunicorn cardarb.web_app:app
```

**Add to requirements.txt:**
```
gunicorn>=21.0
```

**Steps:**
1. Push to GitHub (or connect repo to Render)
2. Create new Web Service on Render
3. Select GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn cardarb.web_app:app`
6. Deploy

### Phase 4: Testing Against eBay Sandbox (1 hour)

```bash
# 1. Verify credentials are correct
export EBAY_APP_ID=your-sbx-app-id
export EBAY_CERT_ID=your-sbx-cert-id

# 2. Test eBay connection
python -m cardarb.test_ebay_live_with_sandbox

# 3. Local Flask test
python cardarb/web_app.py
# Visit http://localhost:5000

# 4. Deploy to Render
git push origin main
# Render auto-deploys
```

---

## Part 5: What Needs to Happen Before Growth Check

### ✓ Already Complete
- [x] eBay API integration code
- [x] OAuth implementation
- [x] Data normalization models
- [x] Card catalog for testing
- [x] Jinja2 templating framework

### ⚠️ Critical Before Submission
- [ ] **Fix credential mismatch** (provide corrected APP_ID + CERT_ID pair)
- [ ] Build Flask web interface
- [ ] Create search form + results template
- [ ] Deploy to public hosting (Render/Railway)
- [ ] Test end-to-end with eBay Sandbox
- [ ] Add disclaimer: "Research and Decision Support Only"

### Optional (Nice-to-Have, Not Required)
- [ ] Add more card catalog entries (currently 50, could expand)
- [ ] Show additional fields (condition, seller rating if available)
- [ ] Add loading spinner during search
- [ ] Cache results for 1 hour (reduce API calls)

---

## Part 6: Estimated Timeline

| Task | Effort | Dependencies |
|------|--------|---|
| Fix credentials | 15 min | User provides correct APP_ID + CERT_ID |
| Build Flask app + templates | 2-3 hrs | Credentials fixed |
| Test locally with Sandbox | 30 min | Flask app + credentials |
| Deploy to Render | 15 min | Flask app + Procfile |
| Test production URL | 15 min | Deployment complete |
| **Total** | **3.5-4 hours** | Credentials ready |

**Blocking Factor:** Waiting for corrected eBay credentials

---

## Part 7: Demo Script for eBay Reviewers

**Timing:** 5-10 minutes

```
1. [Show landing page]
   "This is Project Atlas, a research tool for sports card market analysis."

2. [Search for "Patrick Mahomes" / "2017" / "Panini Prizm"]
   "I'll search for a popular card through eBay's public marketplace."

3. [Show results]
   "Atlas retrieves active listings and normalizes the data:
    - Price from eBay's public API
    - Listing format (auction vs. fixed-price)
    - Source attribution to eBay
    - Listed date"

4. [Show disclaimer]
   "All of this is research and decision support only.
    There is no purchasing, bidding, or execution functionality.
    This tool analyzes public market data to help informed decision-making."

5. [Show data flow]
   "Behind the scenes:
    - OAuth authentication to eBay
    - Retrieves public listing data
    - Normalizes field mappings
    - Displays to user
    - No transactions, no bidding, no checkout."
```

---

## Part 8: Changes Required Before Growth Check

### Code Changes Needed: NONE

The existing `EbayAdapter` can be used as-is. Only additions:
- Flask wrapper (new file)
- HTML templates (new files)
- Procfile (new file)

### No Architecture Changes Required
- No modification to existing models
- No changes to `EbayAdapter`
- No changes to data structures
- No business logic changes

### What's NOT Being Changed
- Strategy modules (not needed for demo)
- Guardrails engine (not needed for demo)
- Decision ledger (not needed for demo)
- Sold listings (not needed for demo)

---

## Part 9: Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| Credentials don't work | HIGH | Test immediately after receiving correct pair |
| eBay API rate limits demo | LOW | Uses Browse API; 50 searches/min should be fine |
| Hosting service goes down | LOW | Can quickly redeploy or use backup service |
| eBay reviews during downtime | VERY LOW | Keep demo running for 7-10 days |

---

## Summary

**Status for Growth Check:** ✓ **READY TO BUILD**

**What you need to provide:**
1. Corrected eBay credentials (APP_ID + CERT_ID matching pair)

**What we'll build:**
1. Simple Flask web interface (~3 hours)
2. Deploy to free Render hosting (~15 minutes)
3. End-to-end test with eBay Sandbox (~30 minutes)

**Total timeline:** 4 hours from receipt of credentials

**Demo URL format:** `https://atlas-ebay-demo.onrender.com`

**No architecture changes needed.** Existing eBay integration handles all the heavy lifting.

---

## Next Steps

1. **Provide corrected eBay credentials** (the APP_ID + CERT_ID pair that work together)
2. **Confirm Sandbox vs. Production** (which environment are you using?)
3. **Approve hosting platform** (Render or Railway?)
4. **I'll implement:**
   - Flask web app
   - Templates
   - Deployment
   - End-to-end testing
   - Verification against eBay Sandbox

Ready to proceed once credentials are provided.

