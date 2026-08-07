# Relative Value Strategy - Complete Logic Breakdown

## Overview

**RelativeValueStrategy** finds cards trading below fair value and buys them for passive price normalization.

**Key difference from CrossMarket**:
- CrossMarket: Buy cheap at Market A, sell at premium at Market B (multi-market arb)
- RelativeValue: Buy underpriced on same market, hold until price normalizes (value arb)

**Example**:
```
CrossMarket:        Buy eBay $95  → Sell PWCC $162  (market spread)
RelativeValue:      Buy eBay $80  → Sell eBay $95   (underpricing)
```

---

## 8-Step Analysis Pipeline

### **Step 1: Card Identity Validation**

**Code**:
```python
if not card.is_valid():
    return None
```

**Same as Strategy 1**: Card confidence must be >95%

**Example**:
```
Mahomes 2020 Donruss #201 PSA 8
Confidence: 98.5% ✅
```

---

### **Step 2: Fair Value Establishment (Comparables)**

**Code**:
```python
comparable = ComparableAnalyzer.analyze(sold_listings)
fair_value = comparable.median_price

if not sold_listings or len(sold_listings) < 3:
    return None  # Need minimum sample
```

**Same logic as Strategy 1**: Use sold comps to establish baseline.

**Example**:
```
Recent eBay sales:
  $90, $92, $95, $97, $100
  
Fair value: $95 (median)
```

---

### **Step 3: Detect Underpricing**

**Code**:
```python
discount_pct = (fair_value - current_ask_price) / fair_value
discount_amount = fair_value - current_ask_price

# Must be underpriced (not at or above fair value)
if current_ask_price <= 0 or current_ask_price >= fair_value:
    return None
```

**Key difference from Strategy 1**: 
- CrossMarket: Looks for price differences ACROSS markets
- RelativeValue: Looks for price differences WITHIN same market

**Example**:
```
Fair value: $95
Current ask: $80
Discount: ($95 - $80) / $95 = 15.8%
Status: UNDERPRICED ✅
```

---

### **Step 4: Filter for Meaningful Discounts**

**Code**:
```python
if discount_pct < 0.05:
    return None  # Need at least 5% discount
```

**Why 5% minimum?**
```
At 5% discount:
  Buy: $95 * 0.95 = $90.25
  Fees (10%): $9.03
  Total cost: $99.28
  
If sells at fair value $95:
  Proceeds: $95 - $9.50 = $85.50
  Loss: -$13.78

WAIT - This doesn't work! Need bigger discount to overcome fees.
```

**Actual math with fees**:
```
5% discount ($95 → $90):
  Cost: $90 + fees $9 = $99
  Proceeds: $95 - fees $9.50 = $85.50
  Loss: -$13.50 ❌ NEGATIVE

15% discount ($95 → $81):
  Cost: $81 + fees $8.10 = $89.10
  Proceeds: $95 - fees $9.50 = $85.50
  Loss: -$3.60 ❌ Still negative
  
30% discount ($95 → $67):
  Cost: $67 + fees $6.70 = $73.70
  Proceeds: $95 - fees $9.50 = $85.50
  Profit: $11.80 ✅ POSITIVE
```

**Reality check**: 5% discount is too small. Strategy will filter out in Steps 5-7 if profit/ROIC don't meet thresholds.

---

### **Step 5: Calculate Economics**

**Code**:
```python
acq_cost = calculate_acquisition_cost("ebay", purchase_price=current_ask_price)
sale_proceeds = calculate_sale_proceeds("ebay", sale_price=fair_value)

economics = TradeEconomics(
    acquisition_cost=acq_cost,
    expected_sale_proceeds=sale_proceeds,
    expected_holding_days=self._estimate_holding_days(active_listings, discount_pct),
)
```

**Key difference**: Both buy AND sell on eBay (same market)

**Example** (30% underpriced card):
```
Purchase price: $67 (30% below $95 fair value)
Sales tax (8%): $5.36
Shipping in: $5.00
Insurance in: $0.67
─────────────────
ALL-IN COST: $78.03

Sale price: $95 (fair value)
eBay fee (10%): $9.50
Shipping out: $5.00
Insurance out: $0.95
Reserve (2%): $1.90
─────────────────
NET PROCEEDS: $77.65

Net profit: $77.65 - $78.03 = -$0.38 ❌ STILL NEGATIVE
```

**Insight**: Even 30% discount barely breaks even due to double fee hit (buy + sell).

**Need even bigger discount**:
```
50% discount ($95 → $47.50):
  Cost: $47.50 + $5.95 in fees = $53.45
  Proceeds: $95 - $17.45 in fees = $77.55
  Profit: $24.10 ✅
  ROIC: 45%
```

---

### **Step 6: Estimate Holding Days (KEY DIFFERENCE)**

**Code**:
```python
def _estimate_holding_days(self, active_listings, discount_pct):
    # Bigger discount = longer hold
    if discount_pct > 0.20:
        base_days = 45
    elif discount_pct > 0.10:
        base_days = 30
    else:
        base_days = 15
    
    # More listings = faster normalization
    if listing_count >= 10:
        return base_days // 2
    elif listing_count >= 5:
        return base_days
    elif listing_count >= 2:
        return base_days + 15
    else:
        return base_days + 30
```

**Why this matters**:
- **Bigger discounts take longer to normalize**. Market needs time to recognize the value.
- **More active listings = faster normalization**. Competitive pressure forces price up.

**Example**:
```
30% discount, 4 active listings:
  Base: 30 days (for 10-20% discount range)
  But discount is 30% (>20%), so: 45 days base
  With 4 listings (>2, <5): +15 days
  Total: 45 + 15 = 60 days

60% discount, 10 active listings:
  Base: 45 days (for 20%+ discount)
  With 10+ listings: 45 / 2 = 22.5 → 23 days
  Total: 23 days
```

---

### **Step 7: Check Guardrails**

**Code**:
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

**Same 12 gates as Strategy 1**:
1. Identity Confidence >95%
2. Comparable Count ≥3
3. Fair Value Confidence ≥70%
4. Liquidity Score ≥40
5. 30-Day Sales Volume ≥2
6. Holding Period ≤90 days
7. Expected ROIC ≥5%
8. Expected Profit ≥$10
9. Position Size ≤$200
10. Player Exposure ≤$1K
11. Sport Exposure ≤$5K
12. Set Exposure ≤$2K

**Different risk profile**:
- Strategy 1 (CrossMarket) has multi-market friction, faster feedback
- Strategy 2 (RelativeValue) depends on price normalization timing, longer holding

---

### **Step 8: Recommendation**

**Code**:
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

**Same logic as Strategy 1**: All gates must pass.

---

## Ranking: Discount % vs ROIC

**Strategy 1** ranks by: **ROIC** (capital efficiency)

**Strategy 2** ranks by: **Discount %** (upside potential)

**Why the difference?**

Strategy 1:
```
Mahomes: $95 → $162 = $66 gross, 22.5% ROIC
Josh Allen: $60 → $110 = $50 gross, 18.3% ROIC

ROIC matters because capital is deployed identically (buy/sell).
Higher ROIC = better use of capital.
```

Strategy 2:
```
Card A: 50% discount, 60-day hold, 35% ROIC
Card B: 60% discount, 90-day hold, 32% ROIC

Discount % matters because bigger discount = more margin of safety.
If normalization is wrong, bigger discount provides cushion.
```

---

## Example Trade: 60% Underpriced Card

### Market Data
```
Fair value (comps): $100
Current ask: $40 (60% underpriced!)
Active listings: 8
Recent sales: 12 in 30 days (active market)
```

### Step-by-Step Analysis

**Step 1: Identity**
```
✅ 98% confidence
```

**Step 2: Fair Value**
```
✅ 8 comps, median $100
```

**Step 3: Underpricing**
```
Discount: ($100 - $40) / $100 = 60%
✅ Clearly underpriced
```

**Step 4: Meaningful?**
```
60% > 5% minimum
✅ Pass
```

**Step 5: Economics**
```
Buy: $40
Cost in: $40 + $3.20 fees + $5 shipping = $48.20
Sell: $100 (fair value)
Proceeds: $100 - $10 fees - $5 - $1 = $84
Profit: $84 - $48.20 = $35.80
ROIC: $35.80 / $48.20 = 74.3%
```

**Step 6: Holding Time**
```
Discount 60% (>20%): base 45 days
Active listings 8 (5-10 range): no adjustment
Estimate: 45 days
```

**Step 7: Guardrails**
```
1. Identity: 98% > 95% ✅
2. Comps: 8 > 3 ✅
3. Fair value confidence: 82% > 70% ✅
4. Liquidity: 75/100 > 40 ✅
5. 30-day sales: 12 > 2 ✅
6. Holding: 45 days < 90 ✅
7. ROIC: 74.3% > 5% ✅
8. Profit: $35.80 > $10 ✅
9. Position: $48.20 < $200 ✅
10. Player: $48.20 < $1K ✅
11. Sport: $48.20 < $5K ✅
12. Set: $48.20 < $2K ✅

All 12 pass ✅
```

**Step 8: Recommendation**
```
BUY ✅
```

### Trade Mechanics
```
Day 1: Buy at $40, cost $48.20
Day 45: Sell at ~$95-100 (normalized)
Proceeds: ~$84
Profit: ~$35.80

Annualized: 74.3% * (365/45) = 601% (if 1-year rolling)
```

---

## Strategy 2 vs Strategy 1: Key Differences

| Aspect | Strategy 1 (CrossMarket) | Strategy 2 (RelativeValue) |
|--------|--------------------------|---------------------------|
| **Opportunity** | Price gap across markets | Underpricing within market |
| **Buy** | Market A (e.g., eBay) | Same market (eBay) |
| **Sell** | Market B (e.g., PWCC) | Same market (eBay) |
| **Spread source** | Market inefficiency | Temporary mispricing |
| **Holding** | Short (7-30 days) | Medium (15-60 days) |
| **Ranking metric** | ROIC | Discount % |
| **Margin of safety** | Multi-market arb | Price normalization |
| **Feedback loop** | Quick (market prices tell truth) | Medium (comps must update) |
| **Risk** | Execution (can't sell at PWCC price) | Timing (normalization delayed) |
| **Data needed** | 2 market prices + comps | 1 market price + comps |

---

## When To Use Each Strategy

**Strategy 1 (CrossMarket)** when:
- Have real-time prices from 2+ markets
- Markets have different players/inefficiencies
- Want fast execution and clear signals

**Strategy 2 (RelativeValue)** when:
- Detecting temporary mispricings
- Playing mean-reversion/market noise
- Single market data is cleaner/fresher
- Willing to hold 30-60 days for normalization

**Run Both** when:
- Have data from multiple markets
- Want diversified opportunity sources
- Can manage both holding profiles

---

## Technical Implementation Notes

**Comps are critical**: Strategy 2's profit depends entirely on fair value being correct.
- Strategy 1: Can escape with PWCC comps being "close enough"
- Strategy 2: MUST have tight comps or wait forever for normalization

**Liquidity scoring matters more**: 
- Strategy 1: Buy and immediately trigger sale elsewhere
- Strategy 2: Must actually sell after buying; liquidity timing is critical

**Holding cost estimate is critical**:
- Strategy 1: 7-30 days (minimal holding costs)
- Strategy 2: 15-60 days (holding costs more significant)
- Bigger discounts take longer → higher cost burden

**Price normalization assumption**:
- Works IF: Market is efficient long-term
- Breaks IF: Card has permanent issue (faked, counterfeit, recalls)
- Mitigated BY: Guardrails, comps quality, card confidence
