# Cross-Market Strategy - Detailed Review

## Step 2: Comparable Sales Analysis (Why 3+?)

**Question**: How do we know 3+ is the right threshold? What's better?

### The Math

From `_confidence_score()` in comparables.py:

```python
if sample_count < 2:
    sample_score = 0.0        # 0% confidence
elif sample_count < 3:
    sample_score = 0.15       # 15% confidence
elif sample_count < 5:
    sample_score = 0.25       # 25% confidence
elif sample_count < 10:
    sample_score = 0.35       # 35% confidence
else:
    sample_score = 0.40       # 40% (max)
```

### Why 3+ Is The Threshold

**Statistical requirement**: Need 3+ data points to:
- Calculate median (position matters with 3+)
- Calculate standard deviation (need n>1, meaningless until n>=3)
- Remove outliers reliably (IQR method requires quartiles)
- Distinguish signal from noise

**Example**:
```
1 comp: $100 (can't tell if fair or outlier)
2 comps: $100, $200 (median $150, but huge spread)
3 comps: $100, $150, $200 (median $150, more credible)
10 comps: Better (higher confidence)
```

### Better Thresholds (Context Dependent)

| Scenario | Threshold | Reasoning |
|----------|-----------|-----------|
| High-volume card (>10 sales/month) | 5+ comps | More data available, can be pickier |
| Medium volume (2-10 sales/month) | 3+ comps | Balanced approach (MVP uses this) |
| Low volume (<2 sales/month) | 2+ comps | Rare cards, accept lower confidence |
| Illiquid penny stocks | 1+ comp | Take what you can get |

### Confidence Calculation

Total confidence (0-1.0) = sample_score + dispersion_score + recency_score

```
3 recent comps with tight spread:
  Sample: 0.25 (3 comps)
  Dispersion: 0.3 (tight <10%)
  Recency: 0.3 (all <14 days old)
  ────────────────
  Total: 0.85 (HIGH confidence)

2 old comps with wide spread:
  Sample: 0.15 (2 comps)
  Dispersion: 0.1 (wide 20%+)
  Recency: 0.1 (all >30 days old)
  ────────────────
  Total: 0.35 (LOW confidence)
```

**Rule**: Strategy rejects any opportunity with <0.70 confidence (guardrail Check 3).

---

## Step 3: Economics Calculation - All-In Costs

**Question**: Review to ensure all-in costs are defined

### AcquisitionCost Breakdown

```python
@dataclass
class AcquisitionCost:
    purchase_price: float          # What you pay
    sales_tax: float               # Local sales tax (~8%)
    inbound_shipping: float        # Shipping TO you (~$5)
    inbound_insurance: float       # Insurance on receipt (~1% value)
    grading_cost: float = 0.0      # If you grade (cross-market uses graded, so 0)
    authentication_cost: float = 0.0
    other_costs: float = 0.0
    
    @property
    def total_cost(self) -> float:
        return sum of all above
```

### Mahomes Example (eBay Purchase)

| Item | Amount | Notes |
|------|--------|-------|
| Purchase price | $95.50 | Lowest ask |
| Sales tax (8%) | $7.64 | State tax (varies) |
| Inbound shipping | $5.00 | Estimate via UPS |
| Inbound insurance (1%) | $1.02 | Seller insurance or self-insure |
| | | |
| **ALL-IN COST** | **$109.16** | What you're actually out of pocket |

**Note**: Cross-market strategy uses already-graded cards, so grading_cost = $0.

### SaleProceeds Breakdown

```python
@dataclass
class SaleProceeds:
    sale_price: float              # Selling price
    platform_fee: float            # Marketplace fee (eBay 12.5%, PWCC 15%)
    outbound_shipping: float       # Shipping FROM you (~$5)
    outbound_insurance: float      # Insurance if buyer uses it (~1%)
    return_and_cancellation_reserve: float  # 2% reserve (held for 30 days)
    consignment_fee: float = 0.0   # For auction houses
    other_deductions: float = 0.0
    
    @property
    def net_proceeds(self) -> float:
        return sale_price - total_deductions
```

### Mahomes Example (PWCC Sale)

| Item | Amount | Notes |
|------|--------|-------|
| Sale price | $162.29 | Fair value estimate |
| Platform fee (10%) | $16.23 | PWCC typical |
| Outbound shipping | $5.00 | To buyer |
| Outbound insurance (1%) | $1.62 | Buyer protection |
| Return reserve (2%) | $3.25 | Held 30 days |
| | | |
| **TOTAL DEDUCTIONS** | $26.10 | |
| **NET PROCEEDS** | $136.19 | What actually hits your account |

### Complete Economics

```
All-in cost:    $109.16
Net proceeds:   $136.19
───────────────────────
Net profit:     $27.03
ROIC:           27.03 / 109.16 = 24.8%
```

### What's Included vs. Not Included

✅ **Included** (accounted for):
- Purchase price
- All platform/transaction fees
- Shipping both directions
- Insurance
- Return reserves
- Sales tax

❌ **NOT included** (assumed negligible or handled separately):
- Storage/holding costs (minimal, <$1/month)
- Payment processor fees (already in platform fee)
- Restocking costs (cards don't degrade)
- Regulatory/compliance costs (handled at portfolio level)
- Opportunity cost of capital (ROIC metric handles this)

---

## Step 4: Liquidity Assessment - What & How

**Question**: What does this mean and how is this defined?

### Definition

**Liquidity** = How quickly and easily you can sell the card at fair value without major discounts.

High liquidity = Fast sale, predictable price  
Low liquidity = Slow sale, price volatility

### LiquidityProfile Metrics

```python
@dataclass
class LiquidityProfile:
    # Historical sales activity
    sales_30_days: int              # How many sold in last 30 days?
    sales_60_days: int
    sales_90_days: int
    
    # Timing
    median_days_on_market: float    # Typical listing duration before sale
    median_days_between_sales: float # Time between successive sales
    
    # Current supply
    active_listings: int            # How many for sale right now
    active_sellers: int             # How many different sellers
    
    # Market depth
    sell_through_rate: float        # % of listed cards that sell
    listing_price_dispersion: float # Price variation (std dev %)
    
    # Probability of sale
    prob_sell_7_days: float         # 0.0-1.0 (e.g., 0.45 = 45%)
    prob_sell_14_days: float
    prob_sell_30_days: float
    prob_sell_90_days: float
    
    liquidity_score: int            # 0-100 composite
```

### Mahomes Liquidity Example

```
Sales history (eBay):
  30 days: 6 sales
  60 days: 11 sales
  90 days: 16 sales

Timing:
  Median days on market: 7 days (fast!)
  Days between sales: 5 days (very active)

Current market (PWCC):
  Active listings: 4
  Active sellers: 4
  Sell-through: 60% (good)
  Price dispersion: 3.8% (tight, competitive)

Probability of sale:
  Within 7 days: 45%
  Within 14 days: 70%
  Within 30 days: 88%
  Within 90 days: 95%

Liquidity score: 78/100 (LIQUID)
```

### Liquidity Score Calculation

From `_compute_liquidity_score()`:

```
Base score starts at 0:
+ Sales frequency (0-30 points)
  30+ sales in 90 days = +30
  10-30 sales = +20
  2-10 sales = +10
  <2 sales = +0

+ Active listings (0-25 points)
  10+ active = +25
  5-10 active = +18
  2-5 active = +10
  1 active = +5
  0 active = +0

+ Sell-through (0-25 points)
  >70% = +25
  50-70% = +15
  30-50% = +10
  <30% = +0

+ Price stability (0-20 points)
  Dispersion <5% = +20
  Dispersion 5-10% = +15
  Dispersion 10-20% = +8
  Dispersion >20% = +0

─────────────────
Total score: 0-100
```

### Why Liquidity Matters for Strategy

**Holding cost** depends on liquidity:
```python
def _estimate_holding_days(active_listings):
    if active_listings >= 5:
        return 7       # Quick sale
    elif active_listings >= 3:
        return 14      # Medium
    elif active_listings >= 1:
        return 21      # Slow
    else:
        return 30      # Very slow
```

**Why?**
- More active listings = more buyer demand = faster sale
- Faster sale = lower holding costs = higher ROIC
- Slower sale = higher holding cost burden
- Must account for this in profit calculation

---

## Step 5: The 12 Guardrails & Why Each

**Question**: What are these 12 risk gates and why?

### Complete List with Thresholds

| # | Gate | Threshold | Purpose | Consequence if Fail |
|---|------|-----------|---------|-------------------|
| 1 | **Identity Confidence** | >95% | Ensure card match is certain | Wrong card = catastrophic loss |
| 2 | **Comparable Count** | ≥3 | Enough data for statistics | Can't calculate fair value |
| 3 | **Fair Value Confidence** | ≥70% | Fair value estimate is credible | Buying/selling at wrong price |
| 4 | **Liquidity Score** | ≥40/100 | Can sell in reasonable time | Get stuck holding illiquid card |
| 5 | **30-Day Sales Volume** | ≥2 sales | Market has recent activity | Market may be dead |
| 6 | **Holding Period** | ≤90 days | Won't be locked up too long | Capital tied up too long |
| 7 | **Expected ROIC** | ≥5% | Minimum return threshold | Risk-reward doesn't justify trade |
| 8 | **Expected Profit** | ≥$10 | Minimum profit in dollars | Execution/slippage risk too high |
| 9 | **Position Size** | ≤$200 | Max per individual card | Over-concentration in one card |
| 10 | **Player Exposure** | ≤$1,000 | Max for any player | Over-concentration in one player |
| 11 | **Sport Exposure** | ≤$5,000 | Max per sport | Over-concentration in one sport |
| 12 | **Set Exposure** | ≤$2,000 | Max per product/year combo | Over-concentration in one set |

### Why These Specific 12?

**Tier 1: Data Quality (Gates 1-5)**
```
If data is wrong, recommendation is wrong.
These gates ensure we're analyzing the right card
with the right fair value.
```

**Tier 2: Trade Quality (Gates 6-8)**
```
Even with good data, trade might not be worth it.
These gates ensure profit is real and holding period manageable.
```

**Tier 3: Portfolio Management (Gates 9-12)**
```
Even good trades can hurt portfolio if over-weighted.
These gates prevent concentration risk.
```

### How They Interact

```
FAIL Gate 1 (bad card identity)
  ↓
STOP - Don't even calculate economics

FAIL Gate 2-5 (data insufficient)
  ↓
STOP - Can't trust fair value estimate

PASS Gates 1-5, FAIL Gate 7 (profit too low)
  ↓
PASS (recommendation rejected but marked for monitoring)

PASS Gates 1-8, FAIL Gate 9 (position too large)
  ↓
PASS (opportunity is good but portfolio can't absorb it right now)

PASS ALL 12
  ↓
BUY ✅
```

### Mahomes Against All 12

```
Gate 1: Confidence 98.5% > 95% ✅
Gate 2: 6 comps > 3 ✅
Gate 3: Fair value confidence 85% > 70% ✅
Gate 4: Liquidity score 78 > 40 ✅
Gate 5: 6 sales in 30 days > 2 ✅
Gate 6: Holding 14 days < 90 ✅
Gate 7: ROIC 24.8% > 5% ✅
Gate 8: Profit $27.03 > $10 ✅
Gate 9: Position $109.16 < $200 ✅
Gate 10: Player exposure $109.16 < $1K ✅
Gate 11: Sport exposure $109.16 < $5K ✅
Gate 12: Set exposure $109.16 < $2K ✅

All 12 pass → BUY ✅
```

### Why Conservative (All-or-Nothing)?

**One failure = PASS** because:
- Trading is margin-based (small edge matters)
- Any single gate failure = margin elimination
- Better to pass 90% of opportunities and win on 10%
- Than pass 50% of opportunities and lose on half

Example: Profit $27, but holding 120 days (fails Gate 6)
```
Holding cost: $1/week × 17 weeks = $17
Net profit: $27 - $17 = $10
ROIC drops from 24.8% to 9.2% (but still passes 5% gate)

HOWEVER: If we're regularly wrong on holding time,
this compounds. Better to skip illiquid cards entirely.
```

---

## Summary

| Step | Decision | Threshold | Mahomes | Mahomes Result |
|------|----------|-----------|---------|---|
| 2 | Use 3+ comps | Stat requirement | 6 comps | ✅ High confidence |
| 3 | Profit after ALL costs | $109.16 cost, $136 proceeds | $27 net | ✅ Real profit |
| 4 | Can sell in reasonable time | Liquidity 40+, 14-day sale | 78 score, 7-day median | ✅ Very liquid |
| 5 | All 12 gates pass | All-or-nothing | 12/12 pass | ✅ BUY |
