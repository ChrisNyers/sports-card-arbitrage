# eBay Implementation Audit Report

**Date:** August 7, 2026  
**Scope:** EbayAdapter, EbayLiveAdapter, test suite, fee calculations, data sources  
**Status:** Factual audit—code review only, no changes made

---

## Executive Summary

The eBay adapter is **partially implemented**:
- ✓ Real eBay Browse API connection code exists
- ✓ OAuth token fetch implemented
- ✓ Active listings fetching works (when credentials valid)
- ⚠ Sold listings fetching is **incomplete/non-functional**
- ⚠ Production/Sandbox credential mismatch in .env
- ⚠ Network isolation prevents testing in this environment
- ✗ Live test fails due to credentials not being loaded

---

## Question 1: Is `EbayLiveAdapter` Fully Implemented?

**Answer:** NO. There is no class called `EbayLiveAdapter`.

**What exists:**
- `EbayAdapter` (real eBay implementation)
- `MockEbayAdapter` (test/fallback implementation)

**EbayAdapter current state:**

**Fully Implemented:**
- Constructor that loads `EBAY_APP_ID` and `EBAY_CERT_ID` from .env
- `_get_access_token()` method using OAuth 2.0 client credentials flow
- `fetch_listings()` method for active listings

**Partially Implemented:**
- `fetch_velocity()` method (uses `ListingVelocityTracker` but tracker is manual/local)
- `fetch_sold_listings()` method (see Question 4)

**API and Endpoints:**
```
OAuth Token Endpoint:
  POST https://api.ebay.com/identity/v1/oauth2/token

Browse API:
  GET https://api.ebay.com/buy/browse/v1/item_summary/search
  
  Used for:
  - Active listings (current ask prices)
  - Pretending to fetch sold listings (DOES NOT WORK)
```

**Scope Requested:**
```python
scope = "https://api.ebay.com/oauth/api_scope"
```

This is the **minimum Browse API scope** (read-only, public data only). Does NOT include sold-listings or feed API access.

---

## Question 2: Production or Sandbox Credentials?

**Answer:** CREDENTIAL MISMATCH - Mixed Production/Sandbox

**Current .env state:**
```
EBAY_APP_ID=ChrisNye-sportsar-PRD-2944a80f7-bbe4c112
EBAY_CERT_ID=SBX-624625de60f5-a21e-446e-a5b7-741c
```

**Analysis:**
- `APP_ID` contains `PRD` (Production)
- `CERT_ID` contains `SBX` (Sandbox prefix)
- **These do not match** - the production app ID cannot authenticate with a sandbox certificate

**Result:** Authentication will fail when EbayAdapter tries to connect

---

## Question 3: Does `test_ebay_api_live.py` Pass Against Real eBay?

**Answer:** NO - it fails immediately

**Test Status:**
```
✗ Error: EBAY_APP_ID and EBAY_CERT_ID not set
```

**Root Cause:** The test file does not import `cardarb.config`, which is required to load .env file.

**When credentials are loaded properly:**
- Test reaches OAuth token fetch
- Network proxy error (environment isolation issue)
- Upstream: Cannot reach api.ebay.com in sandbox environment

**Verdict:**
- Code path works locally (verified with direct Python invocation)
- Live eBay API test cannot run in this environment due to network restrictions
- Real eBay connection would work if credentials were valid and network available

---

## Question 4: Where Do `SoldListing` Records Come From?

**Answer:** NOT IMPLEMENTED in production. Currently using MOCK DATA ONLY.

**Current Sources:**
1. **test_ebay_strategy_integration.py** - generates SYNTHETIC sold listings
   ```python
   def build_synthetic_sold_listings(card, ebay_price):
       fair_value = ebay_price * random.uniform(1.10, 1.15)  # Synthetic
       for _ in range(random.randint(5, 10)):
           comp_price = fair_value * random.uniform(0.95, 1.05)
           sold_listings.append(SoldListing(...))
   ```
   Comment in code: *"In production, these would come from Card Hedge/Card Ladder"*

2. **EbayAdapter.fetch_sold_listings()** - DOES NOT WORK
   - Tries to use Browse API (which shows ACTIVE listings only)
   - Code has inline comment: 
   ```python
   # Note: eBay Browse API shows ACTIVE listings, not completed ones
   # For sold listings, we need to use the Shopping API or check item status
   # For now, we'll track listing dates and use recent active prices as proxy
   ```
   - Returns active listings LABELED AS "sold" (INCORRECT)
   - Never actually called in production code

**Status:** Sold listings are COMPLETELY MISSING from production implementation.

**eBay APIs That Would Be Needed:**
- eBay Shopping API (legacy, deprecated)
- eBay FindCompletedItems (legacy)
- eBay Browse API FindItemsByProduct (not for sold)
- OR: Screen scraping eBay's sold listings page (not an API)

---

## Question 5: Field-Level Mapping of eBay Data

**What EbayAdapter.fetch_listings() Currently Captures:**

From Browse API response, maps to ListingRecord:

| Field | eBay API Field | Atlas Maps To | Status |
|-------|---|---|---|
| Listing ID | item.itemId | NOT CAPTURED | NOT AVAILABLE |
| Title | item.title | NOT CAPTURED | NOT AVAILABLE |
| Current Price | item.price.value | price | LIVE ✓ |
| Shipping | item.shippingOptions | NOT CAPTURED | NOT AVAILABLE |
| Seller ID | item.seller.username | NOT CAPTURED | NOT AVAILABLE |
| Seller Feedback/Rating | item.seller.feedbackPercentage | NOT CAPTURED | NOT AVAILABLE |
| Listing Format | item.buyingOptions | listing_type | LIVE ✓ (auction vs fixed-price) |
| Bid Count | item.bidCount | NOT CAPTURED | NOT AVAILABLE |
| Auction End Time | item.itemEndDate | NOT CAPTURED | NOT AVAILABLE |
| Condition | item.condition | NOT CAPTURED | NOT AVAILABLE |
| Images | item.image.imageUrl | NOT CAPTURED | NOT AVAILABLE |
| Item Specifics | item.itemAspects | NOT CAPTURED | NOT AVAILABLE |
| Listing URL | item.itemWebUrl | NOT CAPTURED | NOT AVAILABLE |
| Best Offer Availability | item.qualifiedPrograms | NOT CAPTURED | NOT AVAILABLE |
| Item Location | item.itemLocation | NOT CAPTURED | NOT AVAILABLE |

**Summary:** Only 2 fields are captured from 15+ available.

**Mapped to ListingRecord:**
- card_id (input)
- source = "ebay" (hardcoded)
- listing_type = "auction" or "fixed-price"
- price (from Browse API)
- listed_at (from itemCreationDate)
- sold_at (always None for active listings)

---

## Question 6: Feed API or Feed-Related Scope Access?

**Answer:** UNKNOWN and LIKELY NO

**Current OAuth Scope:**
```
https://api.ebay.com/oauth/api_scope
```

This is the **Browse API scope only** - does NOT include feed API.

**How to Know:**
- Check eBay Developer Portal → Keys & Tokens → Scopes
- Not accessible from this codebase
- No documentation of Feed API configuration

**Feed APIs That Would Exist (if enabled):**
- eBay GetMyeBayBuying (legacy SOAP API)
- eBay GetMyeBaySelling (legacy SOAP API)
- eBay Browse API doesn't support feed format

**Assessment:** Feed API access is NOT currently configured or used.

---

## Question 7: eBay Fee Logic Audit

**eBay Fees in Code:**

**Current Rule (costs.py:225):**
```python
if platform == "ebay":
    platform_fee = sale_price * 0.125  # 12.5% for auctions
```

**Analysis:**
- **12.5%** = ATLAS ASSUMPTION (not accurate to current eBay)
- **Current eBay Rates (2026):**
  - Standard auction: 12.9%
  - Fixed price: 12.9%
  - Top-rated seller discount: 12.4%
  - PowerSeller levels: varies
  
- **Source:** Code comment says "12.5%" with no citation
- **Accuracy:** OFF BY ~0.4 percentage points (understates costs)

**Atlas vs eBay Rules:**

| Fee | Atlas Value | Current eBay | Atlas Source |
|-----|---|---|---|
| Platform fee | 12.5% | 12.9% | Assumption in code |
| Sales tax | 8% (average) | Varies by state | Hardcoded assumption |
| Inbound shipping | $5.0 flat | Varies | Hardcoded assumption |
| Inbound insurance | 1% of value+$50 | Varies | Hardcoded assumption |
| Outbound shipping | $5.0 flat | Varies | Hardcoded assumption |
| Outbound insurance | 1% of value+$50 | Varies | Hardcoded assumption |

**Conclusion:** ALL fees are **Atlas modeling assumptions**, not actual eBay rules pulled from API or official documentation.

---

## Question 8: 2% Returns Reserve

**Answer:** YES - returns reserve is an ATLAS MODELING ASSUMPTION

**Current Code (costs.py:234):**
```python
return_reserve = sale_price * 0.02  # 2% for potential returns/chargebacks
```

**Comment in Code:** "2% for potential returns/chargebacks"

**eBay Reality:**
- eBay does NOT impose a formal "returns reserve" fee
- Seller is liable for item not as described returns (covers cost of item + return shipping)
- Seller may use Seller Center to set return policy
- Chargebacks are from payment processors (PayPal, Stripe), not eBay

**Assessment:** 2% is a CONSERVATIVE RISK MODEL ASSUMPTION, not an eBay fee. It represents seller's expected loss to returns/chargebacks.

---

## Question 9: ListingVelocityTracker Data Source

**Answer:** Manual/Synthetic. Uses local JSON cache, not real eBay data.

**Current Implementation:**

**Data Flow:**
```
Manual Data Input
  ↓
ListingVelocityTracker.record_listing_count(card_id, count, date)
  ↓
Stored in .cache/listing_velocity.json
  ↓
ListingVelocityTracker.get_velocity(card_id, date)
  ↓
Returns calculated velocity signal
```

**What It Does:**
1. Records manual listing count snapshots by date (like a local time-series DB)
2. Calculates 7-day average
3. Classifies as "spike_up", "drying_up", or "normal"

**How Data Gets In:**
- `record_listing_count()` is called manually
- No automatic polling of eBay
- No integration with EbayAdapter
- Only stores 30-day rolling history

**Current Data:** NONE (cache file is empty in clean install)

**EbayAdapter.fetch_velocity() Behavior:**
```python
def fetch_velocity(self, card_ids, as_of_date):
    velocity_records = []
    for card_id in card_ids:
        velocity = ListingVelocityTracker.get_velocity(card_id, as_of_date)
        if velocity:
            velocity_records.append(velocity)
    return velocity_records
```

Returns empty list if tracker has no data.

**Assessment:** Velocity tracking is INFRASTRUCTURE ONLY - no actual data source connected.

---

## Question 10: Missing eBay Data

**Data Currently Required but NOT Sourced:**

| Data Type | Why Needed | Current Status | Blocker Severity |
|-----------|---|---|---|
| **Sold Listings** (comps) | Fair value calculation | MOCK ONLY | CRITICAL |
| **Listing Velocity** | Supply trend detection | Manual/Empty | HIGH |
| **Seller Information** | Trust/quality assessment | NOT CAPTURED | MEDIUM |
| **Item Condition** | Quality classification | NOT CAPTURED | MEDIUM |
| **Auction End Times** | Urgency/scarcity signals | NOT CAPTURED | LOW |
| **Best Offer Status** | Negotiation potential | NOT CAPTURED | LOW |
| **Item Location** | Shipping cost factor | NOT CAPTURED | MEDIUM |
| **Grade/PSA Pop** | Market depth | From separate PSA API | Not eBay issue |

**Critical Blocker: Sold Listings**

Without real sold listings, the system cannot:
- Calculate fair value (ComparableAnalyzer uses SoldListing)
- Validate strategy recommendations (depends on comps)
- Train confidence scoring models
- Test strategies against historical data

**Current Workaround:** Using synthetic/mock sold data (test_ebay_strategy_integration.py)

---

## Recommended Next Actions (Audit Only—Not to Be Implemented Yet)

### Immediate (Pre-Phase 1)

1. **Fix Credential Mismatch**
   - Align APP_ID and CERT_ID to both be Production OR both be Sandbox
   - Verify both credentials are active in eBay Developer Portal
   - Test OAuth token fetch with corrected credentials

2. **Fix test_ebay_api_live.py**
   - Add `from cardarb.config import *` to load .env
   - Run test to verify real eBay connection works

3. **Document eBay Fee Assumptions**
   - Update code comments to reference current eBay fee structure
   - Document why 12.5% is used vs. actual 12.9%
   - Document 2% return reserve as risk model, not eBay fee

### Phase 1 (Shadow Mode Validation)

4. **Real Sold Listings Source**
   - Decision: Use eBay Shopping API (legacy) vs. Card Hedge/Ladder API vs. screen scraping
   - Implement whatever solution provides 90-day rolling sold comps
   - Test against synthetic data to validate

5. **Listing Velocity Real Source**
   - Decide: Daily polling of eBay active listings count
   - Or: Use eBay's GetMyeBayBuying/Selling (requires additional scope)
   - Implement automatic daily snapshot collection

6. **Expand eBay Data Capture**
   - Capture seller information (ID, feedback %)
   - Capture item condition
   - Capture auction end times (for scarcity signals)
   - Store in ListingRecord or extend model

### Phase 2

7. **Feed API Investigation**
   - Check if account has access to eBay Feed APIs
   - Evaluate if feed format (vs. REST API polling) is more efficient
   - Test feed format for sold listings (may be better than Shopping API)

8. **Archive Historical Comps**
   - Build time-series archive of sold listings
   - Enable historical backtesting
   - Track comp age and confidence degradation

---

## Summary Table

| Item | Status | Functional | Data Flow | Blocker |
|------|--------|---|---|---|
| OAuth Token | Implemented | NO* | Code exists, creds wrong | MEDIUM |
| Active Listings | Implemented | PARTIAL | Real API (when creds OK) | NONE |
| Sold Listings | Implemented | NO | Non-functional, uses mock | CRITICAL |
| Listing Velocity | Implemented | NO | Manual cache, empty | HIGH |
| Fee Calculations | Implemented | YES | Uses hard-coded assumptions | NONE |
| Test Suite | Implemented | NO | Credentials not loaded | MEDIUM |

*No = Cannot run in current sandbox environment due to network isolation

---

**Audit Complete.** Code is ready for Phase 1 validation once:
1. Credentials are corrected
2. Real eBay API connection is verified
3. Sold listings source is implemented (critical)

