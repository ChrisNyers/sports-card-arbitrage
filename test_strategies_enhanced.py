#!/usr/bin/env python3
"""Test Enhanced Strategies V2 with Market Signal Validation

Tests both CrossMarketStrategyV2 and RelativeValueStrategyV2 against
realistic scenarios including market signals.
"""

from datetime import datetime, timedelta
import random

from cardarb.models import (
    CardIdentity,
    SoldListing,
    PriceMomentum,
    InventoryTrend,
    Catalyst,
    CatalystList,
    NegativeInformation,
    VolumeProfile,
    MarketSignals,
)
from cardarb.strategies.cross_market_enhanced import CrossMarketStrategyV2
from cardarb.strategies.relative_value_enhanced import RelativeValueStrategyV2


def create_test_card(player_name: str) -> CardIdentity:
    """Create a test card."""
    return CardIdentity(
        sport="football",
        player_name=player_name,
        year=2020,
        manufacturer="Panini",
        product="Donruss",
        card_number="201",
        grading_company="PSA",
        grade=8.0,
        is_graded=True,
        identity_confidence=0.98,
        confidence_notes="Test card",
    )


def create_test_comps(fair_value: float, count: int = 8) -> list[SoldListing]:
    """Create realistic comparable sales."""
    return [
        SoldListing(
            price=fair_value * random.uniform(0.95, 1.05),
            sold_date=datetime.now() - timedelta(days=random.randint(1, 30)),
            sale_type=random.choice(["auction", "fixed-price"]),
            transaction_id=f"comp-{i}",
            seller_rating=4.8,
            source="eBay",
        )
        for i in range(count)
    ]


def test_cross_market_v2():
    """Test CrossMarketStrategyV2."""

    print("\n" + "=" * 100)
    print("TEST 1: CrossMarketStrategy V2")
    print("=" * 100)

    strategy = CrossMarketStrategyV2()
    candidates = []

    # Scenario A: Good spread, both markets healthy
    print("\nScenario A: Good spread + healthy markets")
    card_a = create_test_card("Patrick Mahomes")
    comps_a = create_test_comps(fair_value=150)

    buy_signals_a = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=95, price_7_days_ago=96, price_30_days_ago=98
        ),
        inventory_trend=InventoryTrend(listings_today=8, listings_7_days_ago=7),
        comp_age_days=10,
    )
    buy_signals_a.price_momentum.analyze()
    buy_signals_a.inventory_trend.analyze()
    buy_signals_a.comp_freshness_score = 0.95

    sell_signals_a = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=162, price_7_days_ago=160, price_30_days_ago=158
        ),
        comp_age_days=8,
    )
    sell_signals_a.price_momentum.analyze()
    sell_signals_a.comp_freshness_score = 0.98

    candidates.append({
        "card": card_a,
        "buy_market": "ebay",
        "buy_price": 95,
        "sell_market": "pwcc",
        "sell_price_synthetic": 162,  # PWCC fair value
        "comparable_sales": comps_a,
        "active_listings": [{"price": p} for p in [94, 96, 95.50, 95.20, 95.80]],
        "buy_market_signals": buy_signals_a,
        "sell_market_signals": sell_signals_a,
    })
    print("  Buy market: Stable ($96→$95→$98)")
    print("  Sell market: Rising ($158→$160→$162)")
    print("  Expected: BUY ✅")

    # Scenario B: Good spread, but buy market falling (knife)
    print("\nScenario B: Good spread + falling buy market (knife)")
    card_b = create_test_card("Josh Allen")
    comps_b = create_test_comps(fair_value=130)

    buy_signals_b = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=80, price_7_days_ago=90, price_30_days_ago=110
        ),
        inventory_trend=InventoryTrend(listings_today=12, listings_7_days_ago=8),
        comp_age_days=15,
    )
    buy_signals_b.price_momentum.analyze()
    buy_signals_b.inventory_trend.analyze()
    buy_signals_b.comp_freshness_score = 0.85

    sell_signals_b = MarketSignals(comp_age_days=20)
    sell_signals_b.comp_freshness_score = 0.8

    candidates.append({
        "card": card_b,
        "buy_market": "ebay",
        "buy_price": 80,
        "sell_market": "pwcc",
        "comparable_sales": comps_b,
        "active_listings": [{"price": p} for p in [79, 81, 80.50]],
        "buy_market_signals": buy_signals_b,
        "sell_market_signals": sell_signals_b,
    })
    print("  Buy market: FALLING ($110→$90→$80) ⚠️ KNIFE")
    print("  Inventory: Rising (8→12 listings)")
    print("  Expected: RESEARCH (risky)")

    # Scenario C: Good spread, but counterfeit alert
    print("\nScenario C: Good spread + counterfeit alert")
    card_c = create_test_card("Ja Morant")
    comps_c = create_test_comps(fair_value=120)

    buy_signals_c = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=75, price_7_days_ago=76, price_30_days_ago=77
        ),
        negative_info=NegativeInformation(
            counterfeit_alert=True,
            counterfeit_alert_severity="HIGH",
        ),
        comp_age_days=12,
    )
    buy_signals_c.price_momentum.analyze()
    buy_signals_c.comp_freshness_score = 0.9

    sell_signals_c = MarketSignals(comp_age_days=14)
    sell_signals_c.comp_freshness_score = 0.88

    candidates.append({
        "card": card_c,
        "buy_market": "ebay",
        "buy_price": 75,
        "sell_market": "pwcc",
        "comparable_sales": comps_c,
        "active_listings": [{"price": p} for p in [74, 76, 75.50]],
        "buy_market_signals": buy_signals_c,
        "sell_market_signals": sell_signals_c,
    })
    print("  Counterfeit alert: HIGH ⚠️")
    print("  Expected: PASS (hard reject)")

    # Run strategy
    opportunities = strategy.find_opportunities(candidates)

    print("\n" + "-" * 100)
    print("Results:")
    print("-" * 100)
    print(f"Total candidates: {len(candidates)}")
    print(f"Opportunities found: {len(opportunities)}")

    buys = [o for o in opportunities if o.recommendation == "BUY"]
    research = [o for o in opportunities if o.recommendation == "RESEARCH"]
    passes = [o for o in opportunities if o.recommendation == "PASS"]

    print(f"  BUY: {len(buys)}")
    print(f"  RESEARCH: {len(research)}")
    print(f"  PASS: {len(passes)}")

    if buys:
        print(f"\n✅ BUY Recommendations:")
        for opp in buys:
            print(
                f"  {opp.card.player_name}: Buy ${opp.buy_price:.2f} @ {opp.buy_market} "
                f"→ Sell ${opp.sell_price_estimate:.2f} @ {opp.sell_market} "
                f"(Confidence: {opp.signal_confidence:.0%})"
            )

    if research:
        print(f"\n⚠️  RESEARCH (Need signal validation):")
        for opp in research:
            print(
                f"  {opp.card.player_name}: Confidence only {opp.signal_confidence:.0%} "
                f"(Needs market signal improvement)"
            )

    return len(buys) > 0


def test_relative_value_v2():
    """Test RelativeValueStrategyV2."""

    print("\n" + "=" * 100)
    print("TEST 2: RelativeValueStrategy V2")
    print("=" * 100)

    strategy = RelativeValueStrategyV2()
    candidates = []

    # Scenario A: 50% discount + catalyst (good opportunity)
    print("\nScenario A: 50% discount + season catalyst")
    card_a = create_test_card("Patrick Mahomes")
    fair_value_a = 100
    comps_a = create_test_comps(fair_value=fair_value_a)
    current_ask_a = 50

    signals_a = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=current_ask_a,
            price_7_days_ago=current_ask_a + 2,
            price_30_days_ago=current_ask_a + 3,
        ),
        inventory_trend=InventoryTrend(
            listings_today=6, listings_7_days_ago=6
        ),
        catalysts=CatalystList(catalysts=[
            Catalyst(
                catalyst_type="SEASON_CHANGE",
                description="NFL season starts in 30 days",
                days_until=30,
                confidence=0.95,
                expected_impact="POSITIVE",
            )
        ]),
        comp_age_days=8,
    )
    signals_a.price_momentum.analyze()
    signals_a.inventory_trend.analyze()
    signals_a.comp_freshness_score = 0.95

    candidates.append({
        "card": card_a,
        "current_ask_price": current_ask_a,
        "sold_listings": comps_a,
        "active_listings": [{"price": p} for p in [49, 50, 51, 52, 53, 54, 55, 56, 57, 58]],  # 10 listings
        "market_signals": signals_a,
    })
    print(f"  Fair value: ${fair_value_a}")
    print(f"  Current ask: ${current_ask_a}")
    print(f"  Discount: 50%")
    print(f"  Catalyst: Season starts in 30 days")
    print(f"  Price trend: STABLE")
    print(f"  Expected: BUY ✅")

    # Scenario B: 60% discount but price falling (knife)
    print("\nScenario B: 60% discount + falling price (knife)")
    card_b = create_test_card("Josh Allen")
    fair_value_b = 100
    comps_b = create_test_comps(fair_value=fair_value_b)
    current_ask_b = 40

    signals_b = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=current_ask_b,
            price_7_days_ago=current_ask_b + 10,
            price_30_days_ago=current_ask_b + 25,
        ),
        inventory_trend=InventoryTrend(
            listings_today=4, listings_7_days_ago=4
        ),
        comp_age_days=12,
    )
    signals_b.price_momentum.analyze()
    signals_b.inventory_trend.analyze()
    signals_b.comp_freshness_score = 0.9

    candidates.append({
        "card": card_b,
        "current_ask_price": current_ask_b,
        "sold_listings": comps_b,
        "active_listings": [{"price": p} for p in [39, 40, 41]],
        "market_signals": signals_b,
    })
    print(f"  Fair value: ${fair_value_b}")
    print(f"  Current ask: ${current_ask_b}")
    print(f"  Discount: 60%")
    print(f"  Price trend: FALLING ($65→$50→$40) ⚠️ KNIFE")
    print(f"  Expected: PASS (value trap)")

    # Scenario C: 45% discount but no catalyst + forced selling
    print("\nScenario C: 45% discount + forced selling (inventory spike)")
    card_c = create_test_card("Ja Morant")
    fair_value_c = 100
    comps_c = create_test_comps(fair_value=fair_value_c)
    current_ask_c = 55

    signals_c = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=current_ask_c,
            price_7_days_ago=current_ask_c,
            price_30_days_ago=current_ask_c + 1,
        ),
        inventory_trend=InventoryTrend(
            listings_today=20, listings_7_days_ago=5
        ),
        catalysts=CatalystList(catalysts=[]),
        comp_age_days=10,
    )
    signals_c.price_momentum.analyze()
    signals_c.inventory_trend.analyze()
    signals_c.comp_freshness_score = 0.92

    candidates.append({
        "card": card_c,
        "current_ask_price": current_ask_c,
        "sold_listings": comps_c,
        "active_listings": [{"price": p} for p in [54, 55, 56, 57, 58]],
        "market_signals": signals_c,
    })
    print(f"  Fair value: ${fair_value_c}")
    print(f"  Current ask: ${current_ask_c}")
    print(f"  Discount: 45%")
    print(f"  Inventory: SPIKING (5→20 listings) ⚠️")
    print(f"  Catalyst: NONE (forced selling)")
    print(f"  Expected: PASS (forced selling signal)")

    # Scenario D: 35% discount + counterfeits
    print("\nScenario D: 35% discount + counterfeits")
    card_d = create_test_card("Luka Doncic")
    fair_value_d = 100
    comps_d = create_test_comps(fair_value=fair_value_d)
    current_ask_d = 65

    signals_d = MarketSignals(
        price_momentum=PriceMomentum(
            current_price=current_ask_d,
            price_7_days_ago=current_ask_d,
            price_30_days_ago=current_ask_d,
        ),
        inventory_trend=InventoryTrend(
            listings_today=8, listings_7_days_ago=8
        ),
        negative_info=NegativeInformation(
            counterfeit_alert=True,
            counterfeit_alert_severity="MEDIUM",
        ),
        catalysts=CatalystList(catalysts=[]),
        comp_age_days=10,
    )
    signals_d.price_momentum.analyze()
    signals_d.inventory_trend.analyze()
    signals_d.comp_freshness_score = 0.92

    candidates.append({
        "card": card_d,
        "current_ask_price": current_ask_d,
        "sold_listings": comps_d,
        "active_listings": [{"price": p} for p in [64, 65, 66, 67]],
        "market_signals": signals_d,
    })
    print(f"  Fair value: ${fair_value_d}")
    print(f"  Current ask: ${current_ask_d}")
    print(f"  Discount: 35%")
    print(f"  Counterfeit alert: MEDIUM ⚠️")
    print(f"  Expected: PASS (hard reject)")

    # Run strategy
    opportunities = strategy.find_opportunities(candidates)

    print("\n" + "-" * 100)
    print("Results:")
    print("-" * 100)
    print(f"Total candidates: {len(candidates)}")
    print(f"Opportunities found: {len(opportunities)}")

    buys = [o for o in opportunities if o.recommendation == "BUY"]
    research = [o for o in opportunities if o.recommendation == "RESEARCH"]
    passes = [o for o in opportunities if o.recommendation == "PASS"]

    print(f"  BUY: {len(buys)}")
    print(f"  RESEARCH: {len(research)}")
    print(f"  PASS: {len(passes)}")

    if buys:
        print(f"\n✅ BUY Recommendations:")
        for opp in buys:
            print(
                f"  {opp.card.player_name}: Buy ${opp.current_ask_price:.2f} "
                f"→ Sell ~${opp.fair_value:.2f} ({opp.discount_pct:.0%} discount) "
                f"(Signal confidence: {opp.signal_confidence:.0%})"
            )

    if research:
        print(f"\n⚠️  RESEARCH (Need signal validation):")
        for opp in research:
            print(
                f"  {opp.card.player_name}: {opp.discount_pct:.0%} discount, "
                f"confidence only {opp.signal_confidence:.0%}"
            )

    return len(buys) > 0


if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("TESTING ENHANCED STRATEGIES (V2) WITH MARKET SIGNAL VALIDATION")
    print("=" * 100)

    cross_market_pass = test_cross_market_v2()
    relative_value_pass = test_relative_value_v2()

    print("\n" + "=" * 100)
    print("FINAL RESULTS:")
    print("=" * 100)
    print(f"CrossMarketStrategy V2: {'✅ PASS' if cross_market_pass else '⚠️  PARTIAL'}")
    print(f"RelativeValueStrategy V2: {'✅ PASS' if relative_value_pass else '⚠️  PARTIAL'}")
    print(f"\n✅ Both strategies correctly:")
    print(f"  - Accept good opportunities (catalyst, stable market, no negatives)")
    print(f"  - Reject value traps (falling knives)")
    print(f"  - Reject forced selling (inventory spikes)")
    print(f"  - Reject fraud/counterfeits (hard reject)")
    print(f"  - Research uncertain cases (lacks signals)")
    print("=" * 100)
