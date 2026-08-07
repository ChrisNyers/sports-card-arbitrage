#!/usr/bin/env python3
"""Integration Test: eBay API + Cross-Market Strategy

Tests the complete workflow:
1. Fetch active eBay listings for known cards
2. Use synthetic sold comparables (from Card Hedge/Ladder)
3. Run cross-market strategy to find opportunities
4. Display recommendations
"""

from datetime import date, datetime, timedelta
import random

from cardarb.sources.ebay import EbayAdapter, MockEbayAdapter
from cardarb.sources.mock_data.card_catalog import get_cards
from cardarb.models import CardIdentity, SoldListing
from cardarb.strategies import CrossMarketStrategy


def catalog_card_to_identity(card) -> CardIdentity:
    """Convert a catalog Card object to CardIdentity."""
    # Parse grade string like "PSA 9" to extract grading company and numeric grade
    grade_parts = card.grade.split()
    grading_company = grade_parts[0] if grade_parts else None
    try:
        grade_numeric = float(grade_parts[1]) if len(grade_parts) > 1 else None
    except ValueError:
        grade_numeric = None

    return CardIdentity(
        sport=card.sport,
        player_name=card.player_name,
        player_position=None,  # Not available in catalog
        year=card.year,
        manufacturer="Panini" if "Panini" in card.set_name else "Topps" if "Topps" in card.set_name else "Upper Deck",
        product=card.set_name.split()[1] if len(card.set_name.split()) > 1 else card.set_name,
        card_number=card.card_number or "",
        set_name=card.set_name,
        parallel=card.variant if card.variant and card.variant != "Base" else None,
        grading_company=grading_company,
        grade=grade_numeric,
        is_graded=grading_company is not None,
        identity_confidence=random.uniform(0.92, 0.99),
        confidence_notes="Converted from mock catalog",
    )


def build_synthetic_sold_listings(card: CardIdentity, ebay_price: float) -> list[SoldListing]:
    """Build synthetic sold comps centered around a fair value.

    In production, these would come from Card Hedge/Card Ladder.
    For MVP testing, we generate realistic comps around the eBay ask price.
    """
    # Assume fair value is 10-15% higher than eBay ask (typical spread)
    fair_value = ebay_price * random.uniform(1.10, 1.15)

    sold_listings = []
    for _ in range(random.randint(5, 10)):
        comp_price = fair_value * random.uniform(0.95, 1.05)
        sold_listings.append(
            SoldListing(
                price=comp_price,
                sold_date=datetime.now() - timedelta(days=random.randint(1, 60)),
                sale_type=random.choice(["auction", "fixed-price"]),
                transaction_id=f"comp-{card.player_name}-{len(sold_listings)}",
                seller_rating=random.uniform(4.5, 5.0),
                source=random.choice(["eBay", "PWCC"]),
            )
        )

    return sold_listings


def run_integration_test():
    """Run the full integration test."""

    print("=" * 100)
    print("eBay API + Cross-Market Strategy Integration Test")
    print("=" * 100)

    # Step 1: Try real eBay adapter; fall back to mock if credentials not set
    print("\nStep 1: Initialize eBay adapter...")
    try:
        adapter = EbayAdapter()
        print("✓ eBay adapter initialized (REAL)")
        use_real = True
    except ValueError:
        print("⚠ eBay credentials not found, using MockEbayAdapter")
        adapter = MockEbayAdapter()
        use_real = False

    # Step 2: Get a subset of cards to test
    print("\nStep 2: Get test cards...")
    all_cards = get_cards()
    test_cards = all_cards[:5]  # Test with first 5 cards
    test_card_ids = [c.card_id for c in test_cards]
    print(f"✓ Selected {len(test_cards)} cards for testing")

    # Step 3: Fetch eBay listings
    print("\nStep 3: Fetch eBay listings...")
    today = date.today()
    ebay_listings = adapter.fetch_listings(test_card_ids, today)
    print(f"✓ Retrieved {len(ebay_listings)} listings from eBay")

    # Step 4: Group listings by card
    listings_by_card = {}
    for listing in ebay_listings:
        if listing.card_id not in listings_by_card:
            listings_by_card[listing.card_id] = []
        listings_by_card[listing.card_id].append(listing)

    print(f"  Cards with listings: {len(listings_by_card)}")
    for card_id, listings in listings_by_card.items():
        card = next(c for c in test_cards if c.card_id == card_id)
        prices = [l.price for l in listings]
        print(f"    {card.player_name}: {len(listings)} listings, avg price ${sum(prices)/len(prices):.2f}")

    # Step 5: Build candidates for strategy
    print("\nStep 4: Build strategy candidates...")
    candidates = []

    for card_id in test_card_ids:
        catalog_card = next(c for c in test_cards if c.card_id == card_id)
        card_listings = listings_by_card.get(card_id, [])

        if not card_listings:
            print(f"  ⚠ {catalog_card.player_name}: No eBay listings found, skipping")
            continue

        # Convert catalog card to CardIdentity
        card_identity = catalog_card_to_identity(catalog_card)

        # Use the average eBay ask price as the buy price
        avg_ebay_price = sum(l.price for l in card_listings) / len(card_listings)

        # Simulate that we can sell at PWCC at a premium
        # In real system, this comes from Card Hedge/Ladder sold data
        pwcc_fair_value = avg_ebay_price * random.uniform(1.10, 1.25)

        # Generate synthetic sold comps
        sold_listings = build_synthetic_sold_listings(card_identity, avg_ebay_price)

        # Create candidate
        candidate = {
            "card": card_identity,
            "buy_market": "ebay",
            "buy_price": avg_ebay_price,
            "sell_market": "pwcc",
            "sell_price_synthetic": pwcc_fair_value,
            "comparable_sales": sold_listings,
            "active_listings": [{"price": listing.price, "seller_id": f"seller-{i}"} for i, listing in enumerate(card_listings[:5])],
        }
        candidates.append(candidate)

    print(f"✓ Built {len(candidates)} candidates from eBay listings")

    # Step 6: Run strategy
    print("\nStep 5: Run Cross-Market Strategy...")
    strategy = CrossMarketStrategy()
    opportunities = strategy.find_opportunities(candidates)
    print(f"✓ Found {len(opportunities)} opportunities")

    # Step 7: Display results
    print("\n" + "=" * 100)
    print("Results:")
    print("=" * 100)

    buys = [o for o in opportunities if o.recommendation == "BUY"]
    passes = [o for o in opportunities if o.recommendation == "PASS"]

    print(f"BUY recommendations: {len(buys)}")
    print(f"PASS recommendations: {len(passes)}")

    if buys:
        print(f"\nTop BUY Opportunities:")
        print("-" * 100)
        for i, opp in enumerate(buys[:5], 1):
            print(f"\n{i}. {opp.card.player_name} - {opp.card.year} {opp.card.set_name}")
            print(f"   Buy:  ${opp.buy_price:7.2f} @ eBay")
            print(f"   Sell: ${opp.sell_price_estimate:7.2f} @ PWCC")
            print(f"   ───────────────────────────────────")
            print(f"   All-in cost:      ${opp.economics.acquisition_cost.total_cost:7.2f}")
            print(f"   Net proceeds:     ${opp.economics.expected_sale_proceeds.net_proceeds:7.2f}")
            print(f"   Expected profit:  ${opp.economics.expected_net_profit:7.2f}")
            print(f"   Expected ROIC:    {opp.economics.expected_roic:7.1%}")
            print(f"   Holding period:   {opp.economics.expected_holding_days} days")
    else:
        print(f"\n⚠ No BUY opportunities found.")
        print(f"Typical spread needed: 30%+")
        print(f"Reason: High transaction fees (~14% total) eat into profits")

    # Step 8: Summary
    print(f"\n" + "=" * 100)
    print("Integration Test Summary:")
    print("=" * 100)

    if use_real:
        print("✅ Real eBay API credentials working")
    else:
        print("ℹ Using mock data (credentials not configured)")

    print(f"✅ Fetch {len(ebay_listings)} listings from eBay")
    print(f"✅ Process listings into strategy candidates")
    print(f"✅ Run cross-market strategy")
    print(f"✅ Generate {len(buys)} actionable recommendations")
    print(f"")
    print(f"Next steps:")
    print(f"  1. Get real sold comps from Card Hedge/Card Ladder API")
    print(f"  2. Add PWCC active listings (for sell-side market depth)")
    print(f"  3. Run strategy daily in shadow mode")
    print(f"  4. Validate recommendations against real market moves")


if __name__ == "__main__":
    run_integration_test()
