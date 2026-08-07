# Cross-Market Strategy Logic - Detailed Breakdown

## Overview

The CrossMarketStrategy finds profitable arbitrage opportunities by:
1. Buying a card at one marketplace (eBay)
2. Selling it at another marketplace (PWCC/Heritage)
3. Making profit after all transaction costs

**Key principle**: Find identical cards with different prices across markets, exploit the spread.

---

## 6-Step Analysis Pipeline

### **Step 1: Card Identity Validation**

**Purpose**: Ensure we're comparing the same card across markets

**Code** (lines 118-120):
```python
if not card.is_valid():
    return None  # Confidence too low
```

**What it checks**:
- Card identity confidence > 95%
- Sufficient data on: player, year, set, grade, cert#

**Example - Mahomes Card**:
```
Patrick Mahomes
  Year: 2020
  Set: Donruss
  Card #: 201
  Grading: PSA 8
  Grade cert #: 12345678
  Parallel: Red /100

Confidence: 98.5% ✅ PASS
```

**Why it matters**: 
- Match accuracy directly impacts profit
- A 1-grade difference = 20-40% price difference
- Misidentifying parallel/variant = catastrophic loss

---

### **Step 2: Comparable Sales Analysis**

**Purpose**: Establish fair value to validate the opportunity

**Code** (lines 122-133):
```python
comparable = ComparableAnalyzer.analyze(sold_listings)

if comparable.sample_count < 3:
    return None  # Too few comparables

fair_value = comparable.median_price
```

**What it calculates**:
- **Median price**: Middle sold price (ignores outliers)
- **Spread**: Range of prices (indicates market stability)
- **Sample count**: How many comps available
- **Outlier removal**: Uses IQR (interquartile range)

**Example - Mahomes Card**:

Recent eBay sold listings:
- $145 (1 week ago)
- $152 (5 days ago)
- $148 (3 days ago)
- $155 (2 days ago)
- $150 (yesterday)
- $158 (today)

**Analysis**:
```
Sample count: 6 ✅
Median: $151 (middle of $145, $152, $155)
Mean: $151.33
Std Dev: $5.13
Min: $145
Max: $158

Fair Value: $151 (median used for robustness)
```

**Why median, not mean?**
- One $500 outlier doesn't skew decision
- More stable when market has noise

---

### **Step 3: Economics Calculation**

**Purpose**: Calculate exact profit/loss including ALL costs

**Code** (lines 142-150):
```python
acq_cost = calculate_acquisition_cost(buy_market, purchase_price=buy_price)
sale_proceeds = calculate_sale_proceeds(sell_market, sale_price=sell_price_estimate)

economics = TradeEconomics(
    acquisition_cost=acq_cost,
    expected_sale_proceeds=sale_proceeds,
    expected_holding_days=self._estimate_holding_days(active_listings),
)
```

**AcquisitionCost Breakdown** (eBay):
```
Purchase price:          $95.50
eBay buyer fees:          $9.55  (10% standard fee)
Shipping to you:          $5.00  (estimate)
Insurance:                $2.00  (1% value)
Holding cost (14 days):   $1.50  (storage/insurance)
───────────────────────────────
Total all-in cost:      $113.55
```

**SaleProceeds Breakdown** (PWCC):
```
Sale price:             $162.29
PWCC seller fees:       $16.23  (10% standard fee)
Shipping from you:       $5.00  (estimate)
Insurance paid out:      $2.00  (1% value)
───────────────────────────────
Net proceeds:           $139.06
```

**Economics Summary**:
```
Gross profit: $162.29 - $95.50 = $66.79
Net profit: $139.06 - $113.55 = $25.51
ROIC: $25.51 / $113.55 = 22.5%
Holding days: 14 (estimated from PWCC liquidity)
```

**Why this matters**:
- $66 gross looks great, but $26 net after fees
- eBay fee of 10% + PWCC fee of 10% = 20% total friction
- Need 20%+ spread MINIMUM just to break even
- Need 30%+ spread to hit 5%+ ROIC threshold

---

### **Step 4: Liquidity Analysis**

**Purpose**: Assess how fast the card can be sold (impacts holding costs)

**Code** (lines 153, 190-202):
```python
liquidity = LiquidityAnalyzer.analyze(sold_listings, active_listings)

# In _estimate_holding_days:
listing_count = len(active_listings)

if listing_count >= 5:
    return 7  # High competition = fast sale
elif listing_count >= 3:
    return 14
elif listing_count >= 1:
    return 21
else:
    return 30  # Low supply = slow sale
```

**Example - Mahomes Card**:

Active PWCC listings for this card:
- Seller A: $162 (1000+ feedback)
- Seller B: $165 (500+ feedback)
- Seller C: $168 (200+ feedback)
- Seller D: $170 (50+ feedback)

```
Active listings: 4
Estimated sale: 14 days
Holding cost: ~$1.50
```

**Liquidity Profile**:
```
High supply: 4+ active listings
Expected days to sale: 14 days
Price elasticity: High (lots of competition)
```

**Why this matters**:
- More listings = faster sale = lower holding cost
- Tight spreads need fast liquidity or they turn negative
- Illiquid cards can take 60+ days to sell

---

### **Step 5: Guardrails Check (12 Gates)**

**Purpose**: Validate opportunity meets risk thresholds

**Code** (lines 155-162):
```python
guardrails_result = GuardrailsChecker.check(
    card=card,
    comparable_analysis=comparable,
    liquidity=liquidity,
    economics=economics,
    current_positions=current_positions,
    guardrails=self.guardrails,
)
```

**The 12 Guardrails** (from ExecutionGuardrails):

| Gate | Threshold | Mahomes | Status |
|------|-----------|---------|--------|
| 1. Min profit | $10 | $25.51 | ✅ Pass |
| 2. Min ROIC | 5% | 22.5% | ✅ Pass |
| 3. Min comps | 3 | 6 | ✅ Pass |
| 4. Min comp recency | 30 days | All recent | ✅ Pass |
| 5. Max position size | $200 | $113.55 | ✅ Pass |
| 6. Card confidence | >95% | 98.5% | ✅ Pass |
| 7. Fair value deviation | <20% | $6.71 (4.4%) | ✅ Pass |
| 8. Liquidity score | >0.6 | 0.85 | ✅ Pass |
| 9. Inventory limit | <5 open | 0 | ✅ Pass |
| 10. Market stability | Coefficient <0.15 | 0.034 | ✅ Pass |
| 11. Slippage buffer | 5% | $8.11 | ✅ Pass |
| 12. Sector concentration | <40% football | 20% | ✅ Pass |

**Example failure reasons** (the 28 close calls):
```
Card A: PASS - Profit $9.50 (below $10 minimum)
Card B: PASS - ROIC 4.2% (below 5% minimum)
Card C: PASS - Only 2 comps (below 3 minimum)
Card D: PASS - Position size $250 (above $200 limit)
```

**Why 12 gates, not just profit + ROIC?**
- Profit can be illusion (bad comps, illiquid)
- ROIC ignores leverage/capital efficiency
- Multiple gates catch different risk types
- Conservative approach: pass if ANY gate fails

---

### **Step 6: Recommendation Generation**

**Purpose**: Generate actionable BUY or PASS decision

**Code** (lines 164-172):
```python
if economics.expected_net_profit < self.guardrails.min_expected_profit:
    recommendation = "PASS"
elif economics.expected_roic < self.guardrails.min_expected_roic:
    recommendation = "PASS"
elif not guardrails_result.passed_all_checks:
    recommendation = "PASS"
else:
    recommendation = "BUY"
```

**Decision Logic**:
1. Check profit threshold → If fail → PASS
2. Check ROIC threshold → If fail → PASS
3. Check all 12 guardrails → If any fail → PASS
4. All checks pass → BUY

**For Mahomes Card**:
```
Profit check: $25.51 > $10 ✅
ROIC check: 22.5% > 5% ✅
Guardrails check: All 12 pass ✅

Decision: BUY ✅
```

---

### **Step 7: Ranking**

**Purpose**: Sort opportunities by attractiveness (highest ROIC first)

**Code** (lines 96-100):
```python
self.opportunities.sort(
    key=lambda o: o.rank_score,
    reverse=True,
)
```

**Why ROIC?**
- ROIC (Return On Invested Capital) = return per dollar deployed
- $100 investment × 20% ROIC = $20 profit
- $100 investment × 5% ROIC = $5 profit
- ROIC is capital-efficient metric
- Prefer high-return-per-dollar trades

**Example ranking** (from MVP test):
```
Rank 1: Mahomes 2020 Donruss #201
        ROIC: 22.5% | Profit: $25.51

Rank 2: Josh Allen 2018 Prizm #255
        ROIC: 18.3% | Profit: $19.20

Rank 3: Ja Morant 2019 Prizm #249
        ROIC: 14.7% | Profit: $15.80
```

---

## Complete Example: Patrick Mahomes 2020 Donruss #201

### **Market Data**
```
eBay ask prices:
  - $93.00 (seller A)
  - $95.50 (seller B) ← Use lowest
  - $97.00 (seller C)

PWCC ask prices:
  - $160.00 (seller D)
  - $162.29 (seller E) ← Research shows realistic
  - $165.00 (seller F)

Recent eBay sold comps:
  $145, $152, $148, $155, $150, $158
  → Fair value: $151 (median)
```

### **Step 1: Identity Validation**
```
✅ Mahomes 2020 Donruss #201 PSA 8
   Confidence: 98.5%
   Reason: All fields match (cert#, parallel, grade)
```

### **Step 2: Comparable Analysis**
```
✅ 6 comps available
   Median: $151
   Range: $145-$158
   Spread: 9% (tight, market stable)
```

### **Step 3: Economics**
```
Buy @ eBay:          $95.50
All-in cost:        $113.55
Sell @ PWCC:        $162.29
Net proceeds:       $139.06
───────────────────────────
NET PROFIT:          $25.51
ROIC:                22.5%
HOLDING:             14 days
```

### **Step 4: Liquidity**
```
✅ 4 active PWCC listings
   Fast sale expected
   Holding cost minimal
```

### **Step 5: Guardrails**
```
✅ All 12 gates pass
   Strongest areas:
   - High ROIC (22.5% >> 5% minimum)
   - Good profit ($25.51 >> $10 minimum)
   - High confidence (98.5% >> 95% minimum)
   - Strong liquidity (0.85 >> 0.6 minimum)
```

### **Step 6: Recommendation**
```
✅ BUY
   Execution: Buy $95.50 on eBay today
   Timeline: Hold 14 days
   Target: Sell $162+ on PWCC
   Expected: $25.51 profit, 22.5% ROIC
```

---

## Key Insights

### **Why This Strategy Works**
1. **No prediction needed** - prices are current, not forecasted
2. **No grading risk** - buying/selling already graded
3. **Fast feedback** - 14 days to profit, not 6 months
4. **Mechanical** - rules-based, no emotion
5. **Testable** - can validate against historical spreads

### **Why Most Don't Pass**
1. **High fees** - 20% total friction kills thin spreads
2. **Market efficiency** - most opportunities already arbed
3. **Liquidity gaps** - holding costs eat into margin
4. **Identity risk** - card mismatch = catastrophic loss
5. **Data gaps** - missing comps or current prices

### **Why Mahomes Passed**
1. **Big spread** - 70% (eBay $95 vs PWCC $162) before fees
2. **Real comps** - 6 sales in last month at $145-158
3. **Strong liquidity** - multiple sellers at target price
4. **High certainty** - 98.5% identity confidence
5. **Room for error** - 22.5% ROIC >> 5% minimum

---

## What This Enables

Once you have real eBay prices + real PWCC comps:

**Daily execution**:
1. Fetch eBay active listings (500 cards)
2. Fetch eBay sold comps (500 cards)
3. Run strategy (15 seconds)
4. Get 0-5 BUY recommendations
5. Execute buys

**Scale**:
- Start: $5K capital, ~4 positions
- After 30 days: $7-8K (profit cycles)
- After 90 days: $15-20K (scale to 8-12 positions)
- After 1 year: $50-100K+ (if 20% ROIC holds)

**Validation metrics**:
- Predicted vs actual ROIC
- Predicted vs actual holding days
- Win rate (% profitable vs predicted)
- Slippage (actual vs predicted prices)
