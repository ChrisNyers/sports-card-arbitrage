# Cross-Market Strategy Logic (Compressed)

## The 6-Step Pipeline

| Step | What | Why | Example |
|------|------|-----|---------|
| 1. Identity | Confirm card match >95% confidence | Mismatch = catastrophic loss | Mahomes 2020 Donruss #201 PSA 8 |
| 2. Comps | Analyze 3+ sold listings for fair value | Establish baseline for validation | 6 comps: $145-158, median $151 |
| 3. Economics | Calculate all costs + profit/ROIC | Know exact margin after fees | Buy $95.50, sell $162 = $25.51 profit, 22.5% ROIC |
| 4. Liquidity | Estimate holding days from supply | Factor in holding costs | 4 active listings = 14 day hold |
| 5. Guardrails | Check 12 risk gates | Catch different risk types | All 12 pass: profit, ROIC, position size, confidence, etc |
| 6. Recommend | BUY if all pass, PASS if any fail | Binary decision | BUY ✅ |

## The Economics (Mahomes Example)

**Buy eBay**: $95.50  
**Fees/Shipping**: $18.05 (eBay 10% + shipping $5)  
**All-in cost**: $113.55  

**Sell PWCC**: $162.29  
**Fees/Shipping**: $16.23 (PWCC 10%)  
**Net proceeds**: $139.06  

**Profit**: $25.51 | **ROIC**: 22.5% | **Holding**: 14 days

## The 12 Guardrails

```
1. Min profit: $25.51 > $10 ✅
2. Min ROIC: 22.5% > 5% ✅
3. Min comps: 6 > 3 ✅
4. Comp recency: All <30 days ✅
5. Position size: $113.55 < $200 ✅
6. Card confidence: 98.5% > 95% ✅
7. Fair value deviation: 4.4% < 20% ✅
8. Liquidity score: 0.85 > 0.6 ✅
9. Inventory limit: 0 < 5 ✅
10. Market stability: 0.034 < 0.15 ✅
11. Slippage buffer: $8.11 available ✅
12. Sector concentration: 20% < 40% ✅

All pass → BUY
```

## Why 1 BUY, 28 PASS

- **28 close calls**: Each failed just one gate
- **Most common failure**: Profit < $10 or ROIC < 5%
- **Others**: Insufficient comps, illiquid, position size limit
- **Conservative approach**: One failure = reject

## Key Insight

**Need 30%+ spread to make 5%+ profit after 20% total fees**

eBay fee (10%) + PWCC fee (10%) = 20% friction  
Mahomes: 70% spread → 22.5% net ROIC ✅  
Most cards: 5-15% spread → Below 5% ROIC ✅ PASS
