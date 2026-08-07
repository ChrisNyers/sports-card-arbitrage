# Sports Card Arbitrage System: Framework v1.1

**Version:** 1.1 (Production Architecture)  
**Date:** August 6, 2026  
**Status:** PROTOTYPE UPGRADE - Shadow Mode  
**Focus:** Real transaction economics, not model accuracy  
**Phase 1:** Generate 100+ recommendations, test execution, measure real P&L

---

## ⚠️ Important: v1.0 → v1.1 Transition

**v1.0 was a prototype.** It:
- Used placeholder data
- Combined strategies into one model
- Reported accuracy (67.7%, 72-74%) without real validation
- Made recommendations based on sentiment, not transaction economics
- Lacked complete cost accounting
- Did not track actual execution

**v1.1 is production architecture.** It will:
- Use real data with complete provenance
- Separate strategy modules with explicit targets
- Report precision, profit factor, and actual P&L
- Make recommendations based on transaction economics
- Calculate complete acquisition and sale costs
- Track execution and real outcomes
- Begin in shadow mode (observe, don't trade)

**Do not represent v1.1 as validated until:**
- 100+ recommendations generated and tracked
- Real sold-comparable data collected
- Chronological out-of-sample testing complete
- Actual execution tested (small trades)
- Complete net-profit reporting available

---

## 1. Strategy Modules (Not One Model)

### Module 1: Same-Card Cross-Market Arbitrage (PRIORITY)

**Objective:** Buy identical card at market A, sell at market B for profit after costs.

**Transaction:**
```
PURCHASE (Market A):
├─ List price: $100
├─ Sales tax (8%): $8
├─ Inbound shipping: $5
├─ Insurance: $2
├─ Acquisition cost: $115

SELL (Market B):
├─ Expected sale price: $145
├─ Platform fees (12%): $17.40
├─ Shipping: $5
├─ Insurance: $2
├─ Net proceeds: $120.60

ECONOMICS:
├─ Gross spread: $45 ($145 - $100)
├─ All-in profit: $5.60
├─ Net ROIC: 4.9%
├─ Holding period: 7-10 days
└─ Valid? YES (above minimum return)
```

**Execution:**
1. Identify identical card (same card identity)
2. Query both markets for current prices
3. Validate card identity confidence > threshold
4. Calculate all-in costs on both sides
5. Check liquidity (can actually sell?)
6. Check guardrails (position size, etc.)
7. Generate recommendation with data snapshot
8. If approved, execute and track

**Target Metrics:**
- Precision among top 10 recommendations
- Average net profit per trade
- % of trades achieving expected return
- Days to sale vs. predicted

### Module 2: Auction-to-Fixed-Price Arbitrage (PRIORITY)

**Objective:** Buy card at auction before sale closes, sell at fixed-price market.

**Transaction:**
```
AUCTION (Buy now):
├─ Current bid: $80
├─ Estimated final price: $95-115
├─ Estimated reserve met: YES
├─ Platform fees (12%): $12-14
├─ All-in cost: $107-129

FIXED-PRICE MARKET (Sell):
├─ Current listings: 3
├─ Prices: $140, $145, $150
├─ Median: $145
├─ Valid comparables (30-day): 12
├─ Confidence: HIGH
├─ Fair value: $140-150

ECONOMICS (Mid-case):
├─ Acquisition cost: $118
├─ Expected sale: $145
├─ Net profit: $27
├─ ROIC: 22.9%
├─ Holding: 2-3 weeks
└─ Valid? YES
```

**Execution:**
1. Monitor active auctions
2. Predict final auction price (bidding activity, reserve status)
3. Query sold comparables
4. Calculate break-even vs. expected returns
5. Generate recommendation 24-48 hours before auction closes
6. If approved, place maximum buy price bid
7. Track execution and sale

**Target Metrics:**
- Win rate on auction bids
- Accuracy of final-price prediction
- Average profit vs. bid commitment
- Time to sale from auction win

### Module 3: Relative-Value Arbitrage

**Objective:** Card trading at discount to similar cards (same player, era, condition).

**Example:**
```
Card A (target):
├─ Player: Patrick Mahomes
├─ Year: 2020
├─ Grade: PSA 8
├─ Asking price: $120
├─ Market frequency: 2/month

Comparables (same player, similar cards):
├─ Card B (2020, PSA 8): $140 (sold 15 days ago)
├─ Card C (2020, PSA 8): $135 (sold 8 days ago)
├─ Card D (2020, PSA 8): $138 (ask)
├─ Median: $137.50

ECONOMICS:
├─ Buy A at: $120
├─ Expected sell: $135
├─ Net profit: $15
├─ ROIC: 12.5%
└─ Holding: 20-30 days
```

**Execution:**
1. Identify basis comparables (same player, era, grade, condition)
2. Calculate median/trimmed mean price
3. Identify outliers (underpriced cards)
4. Check liquidity (enough sales to support estimate?)
5. Calculate expected return with realistic holding period
6. Generate recommendation

**Target Metrics:**
- Precision of comparable-value estimates
- Holding period vs. liquidity
- Profit factor across recommendations

### Module 4: Raw-to-Graded Arbitrage

**Objective:** Buy raw card, grade it, sell graded card for profit.

**Transaction:**
```
BUY RAW:
├─ Raw card asking price: $50
├─ Inbound shipping: $3
├─ Insurance: $1
├─ All-in cost: $54

GRADE:
├─ Grading service cost: $15
├─ Turnaround: 30 days

SELL GRADED:
├─ Expected grade: 7-8 (based on condition assessment)
├─ If grade 7:
│  ├─ Comparable sales: 0/30 days (illiquid)
│  └─ SKIP (no market)
├─ If grade 8:
│  ├─ Comparable sales: 5/30 days
│  ├─ Median price: $85
│  ├─ Expected proceeds: $72
│  └─ Expected profit: $18
│     (Net of platform fees $13)

ECONOMICS:
├─ Holding: 30-40 days
├─ Break-even grade: 6 ($69 sale needed)
├─ Expected ROIC (if grade 8): 33%
├─ Risk: Grade uncertainty
└─ Valid? CONDITIONAL (only if high-confidence grade)
```

**Execution:**
1. Identify candidates (undergraded raw cards)
2. Assess condition (photo analysis + comps)
3. Estimate likely grade with confidence interval
4. Query sold comps at likely grades
5. Calculate expected return at each grade scenario
6. Assess grading cost and timing
7. Generate recommendation with grade confidence

**Target Metrics:**
- Accuracy of grade prediction
- Profit vs. actual grade received
- Holding period accuracy
- Downside scenarios (unexpected grades)

### Module 5: Event-Driven Directional Trading

**Objective:** SECONDARY. Only if event creates measurable market opportunity.

**Note:** Events (injuries, records, trades) are signals, not recommendations. Trade only if:
- Historical data shows cards UP after event
- Liquidity exists to execute in timeframe
- Expected return exceeds minimum threshold

**Example:**
```
EVENT: Player breaks franchise record

ANALYSIS:
├─ Historical: Cards of this player up 8-15% in 7 days after record
├─ Sample size: 3 similar events (small sample)
├─ Volatility: High (range: -5% to +25%)

CURRENT MARKET:
├─ Recent sales: 6 in 30 days
├─ Current price: $100
├─ Days to expected peak: 5-7 days
├─ Expected price at peak: $105-115
├─ Probability of +10%: 45%
├─ Probability of -5%: 15%

ECONOMICS (Mid-case):
├─ Buy at: $100
├─ Expected sell: $110
├─ Net profit: $8
├─ ROIC: 7.8%
├─ Holding: 5-10 days
└─ Risk: Event priced in already? Event impact declining?

RECOMMENDATION:
├─ Valid? CONDITIONAL
├─ Issue: Low sample size, high volatility
├─ Action: SKIP unless event is unusual/major
```

**Execution:**
1. Measure historical price reaction to event type
2. Assess current market sentiment (are comps already up?)
3. Calculate risk-adjusted return
4. Only recommend if expected return exceeds 5% and holding ≤ 30 days

**Target Metrics:**
- Win rate on event predictions (what % went up?)
- Average return vs. expected
- Return to holding-period ratio

---

## 2. Canonical Card Identity Schema

**Every recommendation must include a card identity with confidence scoring.**

```python
@dataclass
class CardIdentity:
    # Sport & Player
    sport: str  # "football", "baseball", "basketball", "hockey"
    player_name: str
    player_birth_date: Optional[date]
    player_position: Optional[str]
    player_id: Optional[str]  # External ID (mlb.com, nfl.com, etc.)
    
    # Card Details
    year: int  # Issue year
    manufacturer: str  # "Panini", "Topps", "Upper Deck", etc.
    product: str  # "Donruss", "Prizm", "Bowman", etc.
    product_type: str  # "Base", "Hobby", "Retail", etc.
    set_name: str  # Specific set within product
    card_number: str  # Card number within set
    
    # Variants & Special Versions
    parallel: Optional[str]  # "Chrome", "Numbered", "Gold", etc.
    parallel_count: Optional[int]  # /999, /50, etc.
    variation: Optional[str]  # "Photo variation", "Error card", etc.
    is_rookie: bool  # Rookie card designation
    is_autograph: bool  # Signed card
    autograph_type: Optional[str]  # "On-card", "Sticker"
    is_relic: bool  # Game-worn, jersey, patch
    relic_type: Optional[str]  # "Jersey", "Patch", "Bat", etc.
    
    # Grading (if graded)
    grading_company: Optional[str]  # "PSA", "BGS", "SGC", "CGC"
    grade: Optional[float]  # 1.0-10.0
    grade_qualifiers: Optional[list[str]]  # "OC", "MC", etc.
    cert_number: Optional[str]  # Certification number
    
    # Status
    is_raw: bool  # True if ungraded
    is_graded: bool  # True if graded
    
    # Identity Confidence
    identity_confidence: float  # 0.0-1.0
    confidence_notes: str  # Why confident/uncertain?
    last_verified: datetime  # When identity was confirmed
    
    # Image Verification
    image_fingerprint: Optional[str]  # Hash for duplicate detection
    image_urls: list[str]  # Source images
    
    def is_valid(self) -> bool:
        """Can this identity be used for price comparison?"""
        return self.identity_confidence > 0.95
```

**Confidence Scoring:**
- 0.99-1.00: Exact match (certified card, same cert number)
- 0.95-0.99: High confidence (same player, year, product, grade, parallel)
- 0.85-0.95: Good confidence (minor variations, possible alternate parallel)
- 0.70-0.85: Moderate confidence (might be alternate or slight variation)
- <0.70: Do not compare prices

**Do not generate a price-based recommendation if confidence < 0.95.**

---

## 3. Real Data with Complete Provenance

**Every data point must include:**

```python
@dataclass
class DataRecord:
    value: Any  # The actual data point
    source: str  # Where it came from
    source_url: Optional[str]  # URL for verification
    collection_timestamp: datetime  # When we fetched it
    data_age_minutes: int  # How old is the data source?
    is_current: bool  # Is this fresh enough to use?
    confidence: float  # How reliable is this value?
    notes: Optional[str]  # Any special context
```

**Example:**

```python
# Sale price data
sold_price = DataRecord(
    value=145.00,
    source="eBay (sold listing)",
    source_url="https://ebay.com/itm/...",
    collection_timestamp=datetime(2026, 8, 6, 14, 23),
    data_age_minutes=4,
    is_current=True,
    confidence=0.98,
    notes="Fixed-price sale, no auction, buyer feedback 5-star"
)

# Population data
population = DataRecord(
    value=342,
    source="PSA Set Registry",
    source_url="https://www.psacard.com/...",
    collection_timestamp=datetime(2026, 8, 5, 12, 0),
    data_age_minutes=26 * 60,  # 26 hours old
    is_current=False,  # Older than 24 hours
    confidence=0.85,
    notes="Population snapshot from yesterday; may have changed"
)

# Listing data
listing = DataRecord(
    value=150.00,  # Asking price
    source="eBay (active listing)",
    source_url="https://ebay.com/itm/...",
    collection_timestamp=datetime(2026, 8, 6, 15, 0),
    data_age_minutes=3,
    is_current=True,
    confidence=0.99,
    notes="BIN price, free shipping, seller has 10K+ sales"
)
```

**Rule: Never recommend without current data.**

```python
def can_recommend(data_snapshot):
    """Do we have fresh enough data to make a recommendation?"""
    
    # Must have current comparable sales
    if not data_snapshot["sold_prices"]:
        return False, "No sold comparables available"
    
    # Sales must be recent enough
    if min(r.data_age_minutes for r in data_snapshot["sold_prices"]) > 30*24*60:
        return False, "Sold data older than 30 days"
    
    # Must have current listing data
    if not data_snapshot["current_listings"]:
        return False, "No active listings to establish price"
    
    # Population data helpful but not critical
    if data_snapshot.get("population"):
        if data_snapshot["population"].data_age_minutes > 7*24*60:
            return False, "Population data older than 7 days"
    
    return True, "All data current and sufficient"
```

---

## 4. Sold-Comparable Engine

**Build a robust comparable-sales database that:**

### 4.1 Remove Incorrect Matches

```python
def validate_comparable(listing_sold, target_card):
    """Ensure sold listing actually matches target card."""
    
    checks = {
        "exact_player": listing_sold.player_id == target_card.player_id,
        "year_match": listing_sold.year == target_card.year,
        "product_match": listing_sold.product == target_card.product,
        "set_match": listing_sold.set_name == target_card.set_name,
        "card_number_match": listing_sold.card_number == target_card.card_number,
        "grade_match": abs(listing_sold.grade - target_card.grade) < 0.5,
        "parallel_match": listing_sold.parallel == target_card.parallel,
    }
    
    # All checks must pass
    if all(checks.values()):
        return True, "Exact match"
    
    # Partial match is possible but requires manual review
    passed = sum(1 for v in checks.values() if v)
    if passed >= 6:
        return "REVIEW", f"Near-match: {passed}/7 checks passed"
    
    return False, "Not a comparable"
```

### 4.2 Remove Duplicates

```python
def remove_duplicate_transactions(sales_list):
    """Eliminate duplicate sales of the same card."""
    
    seen_transactions = {}
    unique_sales = []
    
    for sale in sales_list:
        # Create signature: player + card number + grade + date
        signature = (
            sale.player_id,
            sale.card_number,
            sale.grade,
            sale.sold_date.date()
        )
        
        if signature not in seen_transactions:
            seen_transactions[signature] = sale
            unique_sales.append(sale)
        else:
            # If we see same card twice in one day, keep the most recent/reliable
            existing = seen_transactions[signature]
            if sale.source_reliability > existing.source_reliability:
                unique_sales.remove(existing)
                unique_sales.append(sale)
    
    return unique_sales
```

### 4.3 Separate Auction vs. Fixed-Price

```python
@dataclass
class SoldComparable:
    price: float
    sale_type: str  # "auction" or "fixed-price"
    sold_date: datetime
    transaction_id: str
    seller_profile: SellerProfile
    quantity: int  # Usually 1
    
def separate_by_sale_type(comparables):
    """Auction and fixed-price sales may behave differently."""
    
    auctions = [s for s in comparables if s.sale_type == "auction"]
    fixed = [s for s in comparables if s.sale_type == "fixed-price"]
    
    return {
        "auctions": {
            "count": len(auctions),
            "prices": [s.price for s in auctions],
            "median": statistics.median([s.price for s in auctions]) if auctions else None,
        },
        "fixed_price": {
            "count": len(fixed),
            "prices": [s.price for s in fixed],
            "median": statistics.median([s.price for s in fixed]) if fixed else None,
        }
    }
```

### 4.4 Identify & Handle Outliers

```python
def identify_outliers(prices):
    """Flag unusually high/low sales (errors, special versions, etc.)."""
    
    if len(prices) < 3:
        return prices, []  # Need at least 3 for IQR
    
    sorted_prices = sorted(prices)
    q1 = sorted_prices[len(sorted_prices) // 4]
    q3 = sorted_prices[3 * len(sorted_prices) // 4]
    iqr = q3 - q1
    
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    normal_prices = [p for p in prices if lower_bound <= p <= upper_bound]
    outliers = [p for p in prices if p < lower_bound or p > upper_bound]
    
    return normal_prices, outliers
```

### 4.5 Weight Recent Sales More Heavily

```python
def calculate_weighted_average(comparables):
    """Recent sales carry more weight than old sales."""
    
    today = datetime.now()
    weights = []
    prices = []
    
    for sale in sorted(comparables, key=lambda s: s.sold_date, reverse=True):
        days_ago = (today - sale.sold_date).days
        
        # Exponential decay: last 7 days = 1.0x, 30 days = 0.5x, 90+ days = 0.2x
        if days_ago <= 7:
            weight = 1.0
        elif days_ago <= 30:
            weight = 0.5 + 0.5 * (30 - days_ago) / 23
        elif days_ago <= 90:
            weight = 0.2 + 0.3 * (90 - days_ago) / 60
        else:
            weight = 0.1
        
        weights.append(weight)
        prices.append(sale.price)
    
    # Weighted average
    if not prices:
        return None
    
    weighted_price = sum(p * w for p, w in zip(prices, weights)) / sum(weights)
    return weighted_price
```

### 4.6 Calculate Multiple Measures

```python
@dataclass
class ComparableSalesAnalysis:
    median_price: float
    trimmed_mean: float  # Remove top/bottom 10%
    price_range: tuple[float, float]  # (low, high)
    dispersion: float  # Standard deviation as % of median
    sample_count: int  # How many valid comps?
    auction_count: int
    fixed_price_count: int
    outlier_count: int
    recency_score: float  # 1.0 = all last 7 days, lower = older
    confidence: float  # Based on sample size and recency
    uncertainty_estimate: float  # ±$ estimate of price uncertainty

def analyze_sold_comparables(comparables):
    """Build complete comparable-sales picture."""
    
    if len(comparables) < 2:
        return None  # Need at least 2 comps
    
    prices = [c.price for c in comparables]
    
    # Identify outliers
    normal_prices, outlier_prices = identify_outliers(prices)
    
    # Separate sale types
    auctions = [c for c in comparables if c.sale_type == "auction"]
    fixed_price = [c for c in comparables if c.sale_type == "fixed-price"]
    
    # Calculate measures
    median = statistics.median(normal_prices)
    trimmed_mean = statistics.mean(
        sorted(normal_prices)[len(normal_prices)//10 : -len(normal_prices)//10]
    ) if len(normal_prices) >= 10 else statistics.mean(normal_prices)
    
    dispersion = (statistics.stdev(normal_prices) / median * 100) if len(normal_prices) > 1 else 0
    
    # Estimate uncertainty
    # Rule: fewer samples or higher dispersion = higher uncertainty
    uncertainty = (dispersion / 100) * median * (10 / len(normal_prices))
    
    # Recency score
    days_old = [(datetime.now() - c.sold_date).days for c in comparables]
    avg_days_old = statistics.mean(days_old)
    recency_score = max(0.1, 1.0 - (avg_days_old / 90))
    
    # Confidence
    confidence = min(0.99, (len(normal_prices) / 10) * recency_score)
    
    return ComparableSalesAnalysis(
        median_price=median,
        trimmed_mean=trimmed_mean,
        price_range=(min(normal_prices), max(normal_prices)),
        dispersion=dispersion,
        sample_count=len(comparables),
        auction_count=len(auctions),
        fixed_price_count=len(fixed_price),
        outlier_count=len(outlier_prices),
        recency_score=recency_score,
        confidence=confidence,
        uncertainty_estimate=uncertainty,
    )
```

---

## 5. Complete Transaction Economics

**Calculate every cost, every fee, every assumption.**

### 5.1 All-In Acquisition Cost

```python
@dataclass
class AcquisitionCost:
    purchase_price: float
    sales_tax: float  # Often 8-10%
    inbound_shipping: float
    inbound_insurance: float
    authentication_or_grading: Optional[float]  # If purchased raw and graded
    other_costs: float  # Authentication, verification, etc.
    
    @property
    def total_cost(self) -> float:
        return sum([
            self.purchase_price,
            self.sales_tax,
            self.inbound_shipping,
            self.inbound_insurance,
            self.authentication_or_grading or 0,
            self.other_costs,
        ])

def calculate_acquisition_cost(purchase_scenario):
    """Calculate true all-in cost to own the card."""
    
    # Platform-specific
    if purchase_scenario.platform == "ebay":
        sales_tax = purchase_scenario.purchase_price * 0.08  # Varies by state
        inbound_shipping = purchase_scenario.shipping_cost
        inbound_insurance = purchase_scenario.insured_value * 0.01
    elif purchase_scenario.platform == "pwcc":
        sales_tax = purchase_scenario.purchase_price * 0.065
        inbound_shipping = 25.0  # PWCC typical
        inbound_insurance = purchase_scenario.insured_value * 0.015
    else:
        sales_tax = purchase_scenario.purchase_price * 0.07
        inbound_shipping = purchase_scenario.shipping_cost
        inbound_insurance = purchase_scenario.insured_value * 0.01
    
    return AcquisitionCost(
        purchase_price=purchase_scenario.purchase_price,
        sales_tax=sales_tax,
        inbound_shipping=inbound_shipping,
        inbound_insurance=inbound_insurance,
        authentication_or_grading=purchase_scenario.grading_cost or 0,
        other_costs=purchase_scenario.other_costs or 0,
    )
```

### 5.2 Expected Net Sale Proceeds

```python
@dataclass
class SaleProceeds:
    expected_sale_price: float
    platform_fees: float  # Usually 12-15%
    promotional_fees: float  # Optional feature to boost listing
    consignment_fees: Optional[float]  # If using consignment
    outbound_shipping: float
    outbound_insurance: float
    return_and_cancellation_reserve: float  # % of sale price held in reserve
    
    @property
    def total_deductions(self) -> float:
        return sum([
            self.platform_fees,
            self.promotional_fees,
            self.consignment_fees or 0,
            self.outbound_shipping,
            self.outbound_insurance,
            self.return_and_cancellation_reserve,
        ])
    
    @property
    def net_proceeds(self) -> float:
        return self.expected_sale_price - self.total_deductions

def calculate_sale_proceeds(sale_scenario, expected_price):
    """Calculate net proceeds from sale."""
    
    if sale_scenario.platform == "ebay":
        platform_fees = expected_price * 0.125  # 12.5% for auction
        promotional_fees = 0  # Usually not needed
    elif sale_scenario.platform == "pwcc":
        platform_fees = expected_price * 0.15  # 15% for auction
        promotional_fees = 0
    else:
        platform_fees = expected_price * 0.12  # Typical
        promotional_fees = sale_scenario.promotional_fee or 0
    
    outbound_shipping = 5.0  # Standard shipping
    outbound_insurance = (expected_price + 50) * 0.01  # Insurance for transit
    return_reserve = expected_price * 0.02  # 2% reserve for potential returns
    
    return SaleProceeds(
        expected_sale_price=expected_price,
        platform_fees=platform_fees,
        promotional_fees=promotional_fees,
        consignment_fees=sale_scenario.consignment_fee if sale_scenario.use_consignment else None,
        outbound_shipping=outbound_shipping,
        outbound_insurance=outbound_insurance,
        return_and_cancellation_reserve=return_reserve,
    )
```

### 5.3 Opportunity Economics

```python
@dataclass
class TradeOpportunity:
    card_identity: CardIdentity
    acquisition_cost: AcquisitionCost
    expected_sale_proceeds: SaleProceeds
    expected_holding_days: int
    
    # Key metrics
    @property
    def expected_gross_profit(self) -> float:
        return (self.expected_sale_proceeds.expected_sale_price - 
                self.acquisition_cost.purchase_price)
    
    @property
    def expected_net_profit(self) -> float:
        return (self.expected_sale_proceeds.net_proceeds - 
                self.acquisition_cost.total_cost)
    
    @property
    def expected_roic(self) -> float:
        if self.acquisition_cost.total_cost == 0:
            return 0
        return self.expected_net_profit / self.acquisition_cost.total_cost
    
    @property
    def annualized_return(self) -> float:
        days_per_year = 365
        if self.expected_holding_days == 0:
            return 0
        return self.expected_roic * (days_per_year / self.expected_holding_days)
    
    @property
    def maximum_buy_price(self) -> float:
        """Maximum we can pay to hit 5% minimum return."""
        target_return = 0.05
        max_cost = self.expected_sale_proceeds.net_proceeds / (1 + target_return)
        return max_cost - (self.acquisition_cost.sales_tax + 
                          self.acquisition_cost.inbound_shipping +
                          self.acquisition_cost.inbound_insurance)
    
    @property
    def break_even_sale_price(self) -> float:
        """What we need to sell for to break even."""
        return (self.acquisition_cost.total_cost + 
                self.expected_sale_proceeds.platform_fees +
                self.expected_sale_proceeds.outbound_shipping +
                self.expected_sale_proceeds.outbound_insurance)
    
    def calculate_downside_scenario(self, pessimistic_sale_price: float) -> float:
        """What's the loss if sale price is lower?"""
        pessimistic_proceeds = SaleProceeds(
            expected_sale_price=pessimistic_sale_price,
            platform_fees=pessimistic_sale_price * 0.125,
            promotional_fees=0,
            consignment_fees=None,
            outbound_shipping=5.0,
            outbound_insurance=(pessimistic_sale_price + 50) * 0.01,
            return_and_cancellation_reserve=pessimistic_sale_price * 0.02,
        )
        return pessimistic_proceeds.net_proceeds - self.acquisition_cost.total_cost
```

---

## 6. Liquidity Features

```python
@dataclass
class LiquidityProfile:
    # Historical sales activity
    sales_30_days: int
    sales_60_days: int
    sales_90_days: int
    
    # Timing metrics
    median_days_between_sales: float
    median_days_on_market: float  # How long active before sale
    
    # Current market
    active_listings: int
    active_sellers: int  # Count of distinct sellers
    
    # Market depth
    sell_through_rate: float  # % of listings that sell
    listing_price_dispersion: float  # Std dev of asking prices
    recent_price_reductions: int  # How many price cuts in last 7 days?
    
    # Activity signals
    auction_bid_activity: float  # Avg bids per auction (if available)
    
    # Prediction
    prob_sell_7_days: float  # 0.0-1.0
    prob_sell_30_days: float
    prob_sell_90_days: float
    
    # Score
    liquidity_score: float  # 0-100, higher = more liquid
    
    def is_liquid_enough(self, required_prob: float = 0.70) -> bool:
        """Is this card liquid enough to trade?"""
        return self.prob_sell_30_days >= required_prob

def analyze_liquidity(card_identity):
    """Assess how easily we can sell this card."""
    
    # Query historical sales
    sales_30 = query_sold_listings(card_identity, days_back=30)
    sales_60 = query_sold_listings(card_identity, days_back=60)
    sales_90 = query_sold_listings(card_identity, days_back=90)
    
    if len(sales_30) == 0:
        return LiquidityProfile(...)  # Illiquid card
    
    # Calculate timing metrics
    sold_dates = [s.sold_date for s in sales_30]
    days_between = [(sold_dates[i] - sold_dates[i+1]).days 
                    for i in range(len(sold_dates)-1)]
    median_days_between = statistics.median(days_between) if days_between else 30
    
    # Days on market
    market_durations = [(s.sold_date - s.listed_date).days for s in sales_30]
    median_dom = statistics.median(market_durations)
    
    # Current market snapshot
    active = query_active_listings(card_identity)
    active_count = len(active)
    seller_count = len(set(a.seller_id for a in active))
    
    # Price dispersion
    if active_count > 1:
        prices = [a.asking_price for a in active]
        dispersion = statistics.stdev(prices) / statistics.mean(prices)
    else:
        dispersion = 0
    
    # Recent price cuts
    price_cuts = sum(1 for a in active if a.price_reduced_7_days)
    
    # Probability of sale
    prob_7 = 1.0 - (1.0 - (7 / median_days_between)) ** (active_count / 5)
    prob_30 = min(1.0, (30 / median_days_between) * 0.9)
    prob_90 = min(1.0, (90 / median_days_between) * 0.95)
    
    # Liquidity score
    components = [
        (len(sales_30) > 2) * 20,  # Recent sales
        (len(sales_90) > 5) * 20,  # Consistent sales
        (median_dom < 14) * 20,  # Sells quickly
        (seller_count > 3) * 20,  # Multiple sellers
        (active_count > 2) * 20,  # Multiple listings
    ]
    liquidity_score = sum(components)
    
    return LiquidityProfile(
        sales_30_days=len(sales_30),
        sales_60_days=len(sales_60),
        sales_90_days=len(sales_90),
        median_days_between_sales=median_days_between,
        median_days_on_market=median_dom,
        active_listings=active_count,
        active_sellers=seller_count,
        sell_through_rate=len(sales_30) / (active_count + len(sales_30)) if active_count + len(sales_30) > 0 else 0,
        listing_price_dispersion=dispersion,
        recent_price_reductions=price_cuts,
        auction_bid_activity=0,  # To be calculated
        prob_sell_7_days=prob_7,
        prob_sell_30_days=prob_30,
        prob_sell_90_days=prob_90,
        liquidity_score=liquidity_score,
    )
```

---

## 7. Explicit Prediction Targets (Not Model Accuracy)

**Do not train a single model to predict "opportunity score" or "accuracy".**

**Instead, create separate predictive targets:**

```python
@dataclass
class ExplicitPredictionTargets:
    
    # Target 1: Probability of minimum net return
    prob_min_net_return: float
    min_net_return_threshold: float  # e.g., $10
    confidence_interval: float  # e.g., 85%
    
    # Target 2: Expected net sale price
    expected_net_sale_price: float
    sale_price_uncertainty: float  # Standard error estimate
    sale_price_range: tuple[float, float]  # (low, high)
    
    # Target 3: Expected net profit
    expected_net_profit: float
    profit_uncertainty: float
    
    # Target 4: Days to sale
    expected_days_to_sale: int
    days_to_sale_range: tuple[int, int]
    
    # Target 5: Downside risk
    prob_loss_over_10_pct: float
    expected_loss_if_downside: float

def predict_explicit_targets(acquisition_price, liquidity_profile, comparable_analysis):
    """Predict each target independently based on feature sets."""
    
    # These are separate models/heuristics, not one combined model
    
    # Target 1: Probability we hit minimum return
    min_return_threshold = 0.05  # 5%
    prob_min_return = calculate_prob_minimum_return(
        acquisition_price,
        comparable_analysis,
        liquidity_profile,
        target_return=min_return_threshold
    )
    
    # Target 2: Expected sale price
    expected_sale = comparable_analysis.median_price
    uncertainty = comparable_analysis.uncertainty_estimate
    low_bound = expected_sale - 2 * uncertainty
    high_bound = expected_sale + 2 * uncertainty
    
    # Target 3: Expected net profit
    expected_profit = expected_sale - acquisition_price - (expected_sale * 0.15)  # Assume 15% fees
    
    # Target 4: Days to sale
    expected_days = liquidity_profile.median_days_on_market * 1.2  # Add buffer
    
    # Target 5: Downside scenario
    downside_price = comparable_analysis.median_price * 0.90  # 10% haircut
    downside_profit = downside_price - acquisition_price - (downside_price * 0.15)
    prob_downside = 0.15  # Historical: 15% of cards sell below median
    
    return ExplicitPredictionTargets(
        prob_min_net_return=prob_min_return,
        min_net_return_threshold=min_return_threshold,
        confidence_interval=0.85,
        expected_net_sale_price=expected_sale,
        sale_price_uncertainty=uncertainty,
        sale_price_range=(low_bound, high_bound),
        expected_net_profit=expected_profit,
        profit_uncertainty=uncertainty * 0.85,
        expected_days_to_sale=int(expected_days),
        days_to_sale_range=(int(expected_days * 0.7), int(expected_days * 1.3)),
        prob_loss_over_10_pct=prob_downside,
        expected_loss_if_downside=downside_profit,
    )
```

---

## 8. Chronological Walk-Forward Testing

**Test with data that was available at decision time. Never use future data.**

```python
def walk_forward_backtest(trades, start_date, end_date):
    """Test trading recommendations chronologically."""
    
    results = []
    
    # Iterate day-by-day
    current_date = start_date
    while current_date <= end_date:
        
        # Generate recommendations using only data available today
        available_data = fetch_data_as_of(current_date)
        recommendations = generate_recommendations(available_data)
        
        # Store immutable snapshot of features for each recommendation
        for rec in recommendations:
            snapshot = {
                "recommendation_date": current_date,
                "card_identity": rec.card_identity,
                "acquisition_cost": rec.acquisition_cost,
                "expected_sale_price": rec.expected_sale_proceeds.expected_sale_price,
                "expected_profit": rec.expected_net_profit,
                "comparable_analysis": rec.comparable_sales,
                "liquidity_profile": rec.liquidity,
                "predictions": rec.targets,
                "features": rec.features,  # All input features
            }
            
            # Wait for outcome
            outcome = wait_for_outcome(rec.card_identity, end_date)
            
            results.append({
                "snapshot": snapshot,
                "actual_sale_price": outcome.sale_price,
                "actual_sale_date": outcome.sale_date,
                "actual_profit": outcome.net_profit,
                "outcome": "win" if outcome.net_profit > 0 else "loss",
            })
        
        current_date += timedelta(days=1)
    
    return results
```

---

## 9. Success Metrics (Not Accuracy)

**Report these, not "72% accuracy":**

```python
@dataclass
class PerformanceReport:
    # Precision & Hit Rate
    precision_top_10: float  # % of top-10 recommendations profitable
    precision_top_20: float
    hit_rate: float  # % of all recommendations profitable
    
    # Profit Metrics
    avg_net_profit: float  # Average profit per winning trade
    median_net_profit: float
    avg_loss: float  # Average loss on losing trades
    
    # Profit Factor
    total_wins: int
    total_losses: int
    profit_factor: float  # (Sum of wins) / (Sum of losses)
    
    # Return Metrics
    avg_roic: float
    annualized_return: float
    capital_turnover: float  # Times capital was deployed
    
    # Execution Metrics
    avg_days_to_sale: float
    pct_sold_within_predicted_days: float
    
    # Forecast Quality
    forecast_calibration: dict  # Actual vs predicted returns
    prediction_error: float  # RMSE of predictions
    
    # Risk Metrics
    max_drawdown: float
    pct_trades_exceeding_10_pct_loss: float

def calculate_performance_report(backtest_results):
    """Calculate comprehensive performance metrics."""
    
    # Separate winners and losers
    winners = [r for r in backtest_results if r["outcome"] == "win"]
    losers = [r for r in backtest_results if r["outcome"] == "loss"]
    
    top_10 = sorted(backtest_results, 
                    key=lambda r: r["snapshot"]["predictions"]["expected_net_profit"],
                    reverse=True)[:10]
    precision_top_10 = sum(1 for r in top_10 if r["outcome"] == "win") / len(top_10)
    
    profit_factor = (sum(w["actual_profit"] for w in winners) / 
                    abs(sum(l["actual_profit"] for l in losers))) if losers else float('inf')
    
    # Forecast calibration
    predictions = [r["snapshot"]["predictions"]["expected_net_profit"] 
                   for r in backtest_results]
    actuals = [r["actual_profit"] for r in backtest_results]
    calibration_error = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) ** 0.5
    
    # Days to sale
    days_to_sale = [(r["actual_sale_date"] - r["snapshot"]["recommendation_date"]).days
                    for r in backtest_results if r["actual_sale_date"]]
    
    return PerformanceReport(
        precision_top_10=precision_top_10,
        precision_top_20=sum(1 for r in backtest_results[:20] if r["outcome"] == "win") / min(20, len(backtest_results)),
        hit_rate=len(winners) / len(backtest_results),
        avg_net_profit=statistics.mean([r["actual_profit"] for r in winners]) if winners else 0,
        median_net_profit=statistics.median([r["actual_profit"] for r in winners]) if winners else 0,
        avg_loss=statistics.mean([r["actual_profit"] for r in losers]) if losers else 0,
        total_wins=len(winners),
        total_losses=len(losers),
        profit_factor=profit_factor,
        avg_roic=statistics.mean([r["actual_profit"] / r["snapshot"]["acquisition_cost"]["total_cost"]
                                 for r in backtest_results]),
        annualized_return=0,  # To calculate
        capital_turnover=len(backtest_results),
        avg_days_to_sale=statistics.mean(days_to_sale) if days_to_sale else 0,
        pct_sold_within_predicted_days=0,  # To calculate
        forecast_calibration={},  # To build
        prediction_error=calibration_error,
        max_drawdown=0,  # To calculate
        pct_trades_exceeding_10_pct_loss=sum(1 for r in backtest_results if r["actual_profit"] / r["snapshot"]["acquisition_cost"]["total_cost"] < -0.10) / len(backtest_results),
    )
```

---

## 10. Listing Lifecycle Tracking

**Replace velocity with full lifecycle:**

```python
@dataclass
class ListingLifecycle:
    listing_id: str  # Unique identifier
    card_identity: CardIdentity
    seller_id: str
    
    # Lifecycle events
    listed_date: datetime
    first_price: float
    
    # State changes
    price_changes: list[tuple[datetime, float]]  # When price changed
    relisted_dates: list[datetime]  # When relisted
    removed_dates: list[datetime]  # When removed without sale
    
    # Current state
    is_active: bool
    current_price: Optional[float]
    days_on_market: int  # Total active days
    
    # Final outcome
    sold_date: Optional[datetime]
    sold_price: Optional[float]
    sold_format: Optional[str]  # "auction" or "fixed-price"
    
    # Metrics
    price_reduction_count: int
    final_price_vs_initial: float  # % change
    list_to_sale_days: Optional[int]

def analyze_listing_lifecycle(listings_by_card):
    """Track what happens to each listing over time."""
    
    for card_id, listings in listings_by_card.items():
        for listing in listings:
            # Build complete lifecycle
            lifecycle = ListingLifecycle(
                listing_id=listing.id,
                card_identity=card_id,
                seller_id=listing.seller_id,
                listed_date=listing.listed_date,
                first_price=listing.initial_price,
                price_changes=[(p.date, p.price) for p in listing.price_history],
                relisted_dates=listing.relisted_dates,
                removed_dates=listing.removed_dates,
                is_active=listing.is_active,
                current_price=listing.current_price if listing.is_active else None,
                days_on_market=listing.days_on_market,
                sold_date=listing.sold_date if listing.status == "sold" else None,
                sold_price=listing.final_price if listing.status == "sold" else None,
                sold_format=listing.sale_format if listing.status == "sold" else None,
                price_reduction_count=len([p for p in listing.price_history if p.price < listing.initial_price]),
                final_price_vs_initial=(listing.final_price / listing.initial_price - 1) if listing.status == "sold" else None,
                list_to_sale_days=(listing.sold_date - listing.listed_date).days if listing.status == "sold" else None,
            )
            
            # Use lifecycle for market analysis
            market_trends = analyze_market_trends(lifecycle)
```

---

## 11. News as Secondary Feature

**Treat player events as signals to measure, not predictions:**

```python
def measure_event_impact(event, card_id):
    """Measure actual market reaction to event, not assume positive."""
    
    # Query before event
    week_before = query_sold_prices(card_id, days_back=14, before_date=event.date - timedelta(days=7))
    median_before = statistics.median([s.price for s in week_before]) if week_before else None
    
    # Query after event
    week_after = query_sold_prices(card_id, days_back=14, after_date=event.date)
    median_after = statistics.median([s.price for s in week_after]) if week_after else None
    
    if median_before and median_after:
        actual_impact = (median_after / median_before - 1)
    else:
        actual_impact = None
    
    return {
        "event": event,
        "card_id": card_id,
        "price_before": median_before,
        "price_after": median_after,
        "actual_impact": actual_impact,
        "sample_size_before": len(week_before),
        "sample_size_after": len(week_after),
    }

def only_recommend_if_event_moves_market(event, event_type):
    """Filter out events that don't actually move the market."""
    
    # Historical: which event types actually move prices?
    impacts = query_historical_event_impacts(event_type)
    
    if not impacts:
        return False  # No historical data
    
    avg_impact = statistics.mean([i["actual_impact"] for i in impacts if i["actual_impact"]])
    impact_consistency = statistics.stdev([i["actual_impact"] for i in impacts if i["actual_impact"]])
    
    # Only recommend if:
    # 1. Average impact > 5%
    # 2. Impact is consistent (low std dev)
    # 3. Sample size > 3
    
    if avg_impact > 0.05 and impact_consistency < 0.15 and len(impacts) > 3:
        return True
    
    return False
```

---

## 12. Execution Guardrails

```python
@dataclass
class ExecutionGuardrails:
    # Data quality
    min_comparable_sales: int = 3  # Reject if <3 recent comps
    min_data_freshness_hours: int = 24  # Data must be <24hrs old
    min_identity_confidence: float = 0.95  # Card identity must be 95%+ certain
    
    # Market conditions
    min_liquidity_score: int = 40  # 0-100 scale
    min_30day_sales: int = 2  # Need at least 2 sales in 30 days
    max_days_to_sale: int = 90  # Don't hold >90 days
    
    # Financial guardrails
    min_expected_roic: float = 0.05  # Minimum 5% return
    min_expected_profit: float = 10  # At least $10 profit
    max_downside_loss: float = -50  # Max loss on downside scenario: $50
    
    # Position management
    max_position_size: float = 200  # Max $200 per card
    max_player_exposure: float = 1000  # Max $1K on any player
    max_sport_exposure: float = 5000  # Max $5K on any sport
    max_set_exposure: float = 2000  # Max $2K on any set
    
    # Trade approval
    require_human_approval: bool = True  # Always require approval
    allow_multiple_strategies: bool = False  # Don't mix strategies

def check_guardrails(recommendation, current_positions):
    """Verify recommendation meets all guardrails."""
    
    checks = {
        "identity_confidence": recommendation.card_identity.identity_confidence > guardrails.min_identity_confidence,
        "comparable_sales": recommendation.comparable_sales.sample_count >= guardrails.min_comparable_sales,
        "data_freshness": all(r.data_age_minutes < guardrails.min_data_freshness_hours * 60 
                             for r in recommendation.data_records),
        "liquidity": recommendation.liquidity.liquidity_score >= guardrails.min_liquidity_score,
        "30day_sales": recommendation.liquidity.sales_30_days >= guardrails.min_30day_sales,
        "holding_period": recommendation.expected_holding_days <= guardrails.max_days_to_sale,
        "expected_roic": recommendation.expected_roic >= guardrails.min_expected_roic,
        "expected_profit": recommendation.expected_net_profit >= guardrails.min_expected_profit,
        "downside_loss": recommendation.downside_scenario >= guardrails.max_downside_loss,
        "position_size": recommendation.acquisition_cost.total_cost <= guardrails.max_position_size,
        "player_exposure": (current_positions.player_exposure(recommendation.player) + 
                          recommendation.acquisition_cost.total_cost) <= guardrails.max_player_exposure,
        "sport_exposure": (current_positions.sport_exposure(recommendation.sport) + 
                         recommendation.acquisition_cost.total_cost) <= guardrails.max_sport_exposure,
        "set_exposure": (current_positions.set_exposure(recommendation.set) + 
                        recommendation.acquisition_cost.total_cost) <= guardrails.max_set_exposure,
    }
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    return {
        "passed_guardrails": passed == total,
        "checks": checks,
        "failed_reasons": [k for k, v in checks.items() if not v],
    }
```

---

## 13. Recommendation Report

Every recommendation must include:

```python
@dataclass
class RecommendationReport:
    report_id: str  # Unique ID
    generation_date: datetime
    strategy_type: str  # "same-card-cross-market", "auction-to-fixed", etc.
    
    # Card Identity
    card: CardIdentity
    card_image_url: str
    identity_confidence: float
    
    # Opportunity
    buy_opportunity: BuyOpportunity
    market: str  # "eBay", "PWCC", etc.
    current_price: float
    
    # Analysis
    comparable_sales: ComparableSalesAnalysis
    fair_value_range: tuple[float, float]
    fair_value_confidence: float
    
    # Economics
    max_buy_price: float
    expected_sale_price: float
    acquisition_cost_detail: AcquisitionCost
    sale_proceeds_detail: SaleProceeds
    
    # Returns
    expected_net_profit: float
    expected_roic: float
    expected_holding_days: int
    annualized_return: float
    
    # Risk
    liquidity_score: float  # 0-100
    downside_scenario: float  # Loss if sell at 90% of fair value
    probability_of_loss: float
    
    # Data Quality
    data_freshness: dict  # When each data point was collected
    guardrails_status: dict  # Which guardrails passed/failed
    
    # Reasoning
    key_reasons: list[str]  # Why this is a good trade
    risk_factors: list[str]  # Reasons it could fail
    
    # Recommendation
    recommendation: str  # "BUY", "PASS", "HOLD"
    approval_required: bool = True

def generate_recommendation_report(card_id, buy_opportunity):
    """Create comprehensive recommendation with full transparency."""
    
    card = get_card_identity(card_id)
    comparables = fetch_sold_comparables(card)
    liquidity = analyze_liquidity(card)
    
    # Acquisition cost
    acq_cost = calculate_acquisition_cost(buy_opportunity)
    
    # Expected sale
    expected_sale = comparables.median_price
    sale_proceeds = calculate_sale_proceeds(expected_sale)
    
    # Predictions
    targets = predict_explicit_targets(acq_cost.total_cost, liquidity, comparables)
    
    # Guardrails check
    guardrail_check = check_guardrails(...)
    
    # Build report
    report = RecommendationReport(
        report_id=f"REC-{card_id}-{datetime.now().isoformat()}",
        generation_date=datetime.now(),
        strategy_type=identify_strategy_type(buy_opportunity),
        card=card,
        card_image_url=buy_opportunity.image_url,
        identity_confidence=card.identity_confidence,
        buy_opportunity=buy_opportunity,
        market=buy_opportunity.platform,
        current_price=buy_opportunity.price,
        comparable_sales=comparables,
        fair_value_range=(comparables.median_price * 0.95, comparables.median_price * 1.05),
        fair_value_confidence=comparables.confidence,
        max_buy_price=targets.expected_net_sale_price * 0.90,  # Need 10% margin
        expected_sale_price=expected_sale,
        acquisition_cost_detail=acq_cost,
        sale_proceeds_detail=sale_proceeds,
        expected_net_profit=targets.expected_net_profit,
        expected_roic=(targets.expected_net_profit / acq_cost.total_cost),
        expected_holding_days=targets.expected_days_to_sale,
        annualized_return=targets.expected_net_profit / acq_cost.total_cost * (365 / targets.expected_days_to_sale),
        liquidity_score=liquidity.liquidity_score,
        downside_scenario=targets.expected_loss_if_downside,
        probability_of_loss=1.0 - targets.prob_min_net_return,
        data_freshness=collect_data_freshness_info(...),
        guardrails_status=guardrail_check,
        key_reasons=[
            f"Fair value ${comparables.median_price:.2f} vs buy ${buy_opportunity.price:.2f}",
            f"{liquidity.sales_30_days} sales in 30 days (liquid market)",
            f"Expected {targets.expected_days_to_sale} days to sale",
            f"${targets.expected_net_profit:.2f} expected profit ({targets.expected_net_profit / acq_cost.total_cost * 100:.1f}% return)",
        ],
        risk_factors=[
            f"Downside scenario: {targets.expected_loss_if_downside:.2f}" if targets.expected_loss_if_downside < 0 else "No major downside",
            f"Price dispersion: {comparables.dispersion:.1%}" if comparables.dispersion > 0.10 else "Tight price range",
        ],
        recommendation="BUY" if guardrail_check["passed_guardrails"] else "PASS",
        approval_required=True,
    )
    
    return report
```

---

## 14. Shadow Mode Operation

**Before trading real capital:**

```
Phase 1 Shadow Mode (100+ Recommendations):
├─ Generate recommendations daily
├─ Track predictions vs actuals
├─ Assess data quality
├─ Test operational execution
├─ Build historical performance database
├─ Do NOT execute trades
└─ Duration: 1-2 months minimum

Validation Criteria:
├─ 100+ recommendations generated
├─ Precision top-20: >60%
├─ Forecast error <$50
├─ Data quality issues documented
├─ Operational workflow proven
└─ Then: Small trades ($100-500) to validate execution
```

---

## 15. Language Changes

**Remove these terms until v1.2+ with validated results:**

❌ "Production ready"  
❌ "72-74% accuracy"  
❌ "Validated"  
❌ "Statistical significance"  

✅ Replace with:

- "Prototype architecture"
- "Shadow mode testing"
- "Forecast precision: 65% top-20 (n=47)"
- "Average profit per win: $23.50"
- "Profit factor: 1.8:1"
- "Further testing required"
- "Results from 47 simulated trades, real performance TBD"

---

## Summary: v1.0 → v1.1 Transformation

| Aspect | v1.0 (Prototype) | v1.1 (Production Architecture) |
|--------|-----------------|-------------------------------|
| **Strategy** | One combined model | 5 separate strategy modules |
| **Card Identity** | Basic metadata | Canonical schema with confidence |
| **Data Quality** | Placeholder data | Real data with provenance |
| **Comparable Sales** | Simple average | Robust outlier removal, weighting |
| **Economics** | Revenue less fees | Complete acquisition + sale costs |
| **Liquidity** | Listing velocity | Full lifecycle tracking |
| **Events** | Positive news = buy | Measure actual market reaction |
| **Guardrails** | Position size only | 12+ data quality & position checks |
| **Reports** | Accuracy score | Precision, profit factor, ROI |
| **Testing** | Backtested on mock | Walk-forward, real data |
| **Validation** | 67.7% accuracy | Shadow mode 100+ trades first |
| **Execution** | Automatic | Always require human approval |

**Next Step:** Generate 100+ recommendations in shadow mode, measure actual results, then decide on live trading.

---

**Framework v1.1 Complete**  
**Status:** Ready for implementation  
**Do not claim validation or readiness until: 100+ shadowing trades + real P&L reporting**
