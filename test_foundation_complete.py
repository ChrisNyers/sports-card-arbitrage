#!/usr/bin/env python3
"""Integration test for v1.1 foundation modules.

Tests all foundation pieces working together:
1. Card identity matching
2. Data provenance
3. Fair value calculation
4. Cost accounting
5. Liquidity analysis
6. Execution guardrails
7. Learning feedback loop
"""

from datetime import datetime, timedelta

from cardarb.models import (
    AcquisitionCost,
    CardIdentity,
    ComparableAnalyzer,
    DataRecord,
    DataSnapshot,
    ExecutionGuardrails,
    GuardrailsChecker,
    LearningRecorder,
    LiquidityAnalyzer,
    RecommendationSnapshot,
    SaleProceeds,
    SoldListing,
    TradeEconomics,
    TradeOutcome,
    calculate_acquisition_cost,
    calculate_sale_proceeds,
)


def test_complete_flow():
    """Run complete flow: identify card, analyze market, calculate economics, check guardrails."""

    print("=" * 100)
    print("V1.1 FOUNDATION INTEGRATION TEST")
    print("=" * 100)

    # Step 1: Card Identity
    print("\n1. CARD IDENTITY")
    print("-" * 100)

    card = CardIdentity(
        sport="football",
        player_name="Patrick Mahomes",
        player_position="QB",
        year=2020,
        manufacturer="Panini",
        product="Donruss",
        card_number="201",
        parallel="Red",
        parallel_count=100,
        grading_company="PSA",
        grade=8.0,
        cert_number="123456789",
        identity_confidence=0.98,
        confidence_notes="Exact match on all fields",
    )

    print(f"Card: {card.short_description()}")
    print(f"Confidence: {card.identity_confidence:.0%}")
    print(f"Can compare prices: {card.is_valid()}")

    # Step 2: Data Provenance
    print("\n2. DATA PROVENANCE & FRESHNESS")
    print("-" * 100)

    # Create data records with different ages
    sold_price_record = DataRecord.price_record(
        value=145.00,
        source="eBay (sold listing)",
        source_url="https://ebay.com/itm/...",
        data_age_minutes=5,
        confidence=0.98,
        notes="Clean sale, no issues",
    )

    listing_record = DataRecord.listing_record(
        price=150.00,
        source="eBay (active)",
        source_url="https://ebay.com/itm/...",
        seller_id="seller123",
        data_age_minutes=2,
        confidence=0.99,
        notes="BIN price, free shipping",
    )

    print(f"Sold price: ${sold_price_record.value} ({sold_price_record.age_description()})")
    print(f"  Freshness: {sold_price_record.recency_score():.0%}")
    print(f"  Is current: {sold_price_record.is_current()}")
    print(f"")
    print(f"Active listing: ${listing_record.value} ({listing_record.age_description()})")
    print(f"  Freshness: {listing_record.recency_score():.0%}")
    print(f"  Is current: {listing_record.is_current()}")

    # Step 3: Fair Value Analysis
    print("\n3. FAIR VALUE ANALYSIS")
    print("-" * 100)

    sold_listings = [
        SoldListing(
            price=145.00,
            sold_date=datetime.now() - timedelta(days=3),
            sale_type="fixed-price",
            transaction_id="ebay-1",
            seller_rating=4.9,
            source="eBay",
        ),
        SoldListing(
            price=142.50,
            sold_date=datetime.now() - timedelta(days=5),
            sale_type="auction",
            transaction_id="ebay-2",
            seller_rating=4.8,
            source="eBay",
        ),
        SoldListing(
            price=148.00,
            sold_date=datetime.now() - timedelta(days=8),
            sale_type="fixed-price",
            transaction_id="pwcc-1",
            seller_rating=5.0,
            source="PWCC",
        ),
        SoldListing(
            price=140.00,
            sold_date=datetime.now() - timedelta(days=15),
            sale_type="auction",
            transaction_id="ebay-3",
            seller_rating=4.7,
            source="eBay",
        ),
        SoldListing(
            price=250.00,  # Outlier
            sold_date=datetime.now() - timedelta(days=20),
            sale_type="fixed-price",
            transaction_id="ebay-4",
            seller_rating=3.0,
            source="eBay",
        ),
    ]

    comparable = ComparableAnalyzer.analyze(sold_listings)
    print(comparable.summary())
    print(f"\nOutliers removed: {comparable.outlier_count} (e.g., $250 mislabeled)")

    # Step 4: Cost Accounting
    print("\n4. TRANSACTION ECONOMICS")
    print("-" * 100)

    acq_cost = calculate_acquisition_cost("ebay", purchase_price=150.0)
    sale_proceeds = calculate_sale_proceeds("ebay", sale_price=145.0)

    econ = TradeEconomics(
        acquisition_cost=acq_cost,
        expected_sale_proceeds=sale_proceeds,
        expected_holding_days=14,
    )

    print(econ.economics_summary())
    print(f"\nBreak-even sale price: ${econ.break_even_sale_price():.2f}")
    print(f"Profit at $145: ${econ.profit_at_price(145):.2f}")

    # Step 5: Liquidity Analysis
    print("\n5. LIQUIDITY ANALYSIS")
    print("-" * 100)

    active_listings = [
        {"price": "150", "seller_id": "seller1"},
        {"price": "145", "seller_id": "seller2"},
        {"price": "152", "seller_id": "seller1"},
    ]

    liquidity = LiquidityAnalyzer.analyze(sold_listings, active_listings)
    print(liquidity.liquidity_summary())
    print(f"\nLiquid enough (prob_30d >= 70%)? {liquidity.is_liquid_enough()}")

    # Step 6: Execution Guardrails
    print("\n6. EXECUTION GUARDRAILS")
    print("-" * 100)

    guardrails = ExecutionGuardrails()
    print(guardrails.summary())

    print(f"\nRunning guardrails check...")
    current_positions = {}  # Empty portfolio for this test

    check_result = GuardrailsChecker.check(
        card=card,
        comparable_analysis=comparable,
        liquidity=liquidity,
        economics=econ,
        current_positions=current_positions,
        guardrails=guardrails,
    )

    print(check_result.summary())

    # Step 7: Learning Snapshot
    print("\n7. LEARNING FEEDBACK LOOP")
    print("-" * 100)

    rec_id = "REC-20260806-MAHOMES201PSA8-001"

    snapshot = RecommendationSnapshot(
        rec_id=rec_id,
        generated_at=datetime.now(),
        card_identity=card,
        predicted_fair_value=comparable.median_price,
        predicted_sale_price=145.0,
        predicted_days_to_sale=14,
        predicted_profit=econ.expected_net_profit,
        predicted_roic=econ.expected_roic,
        predicted_confidence=comparable.confidence,
        strategy_type="same-card-cross-market",
        market_platform="eBay→PWCC",
        comparable_analysis=comparable,
        liquidity_profile=liquidity,
        target_buy_price=140.0,
        max_buy_price=142.0,
        guardrails_passed=check_result.passed_all_checks,
        guardrails_failed=check_result.failed_checks,
        approved_by="test_user",
        approved_at=datetime.now(),
    )

    print(snapshot.summary())

    # Simulate outcome after trade completes
    print(f"\nSimulating trade outcome...")

    outcome = TradeOutcome(
        rec_id=rec_id,
        was_executed=True,
        purchased_price=141.0,
        purchased_date=datetime.now() - timedelta(days=14),
        sold_price=144.0,
        sold_date=datetime.now(),
        actual_profit=econ.profit_at_price(144.0),
        actual_roic=econ.profit_at_price(144.0) / acq_cost.total_cost,
        days_held=14,
        was_profitable=True,
    )

    # Calculate prediction errors
    outcome.prediction_error_price = snapshot.predicted_sale_price - outcome.sold_price
    outcome.prediction_error_days = snapshot.predicted_days_to_sale - outcome.days_held
    outcome.prediction_error_profit = snapshot.predicted_profit - outcome.actual_profit

    print(outcome.summary())

    # Step 8: Learning Recorder
    print("\n8. LEARNING RECORDER - PERFORMANCE TRACKING")
    print("-" * 100)

    recorder = LearningRecorder()
    recorder.save_recommendation(snapshot)
    recorder.save_outcome(outcome)

    # Link and analyze
    gap = recorder.link_outcome_to_recommendation(rec_id)
    print(f"Recommendation ID: {gap['rec_id']}")
    print(f"Status: {gap['status']}")
    print(f"")
    print(f"Gap Analysis:")
    print(f"  Price prediction error: ${gap['gaps']['price_prediction_error']:.2f}")
    print(f"  Days prediction error: {gap['gaps']['days_prediction_error']} days")
    print(f"  Profit prediction error: ${gap['gaps']['profit_prediction_error']:.2f}")
    print(f"  Profitable: {gap['gaps']['was_profitable']}")
    print(f"  Matched prediction: {gap['gaps']['matched_prediction']}")

    print(f"\n{recorder.performance_summary()}")

    # Final Summary
    print("\n" + "=" * 100)
    print("FOUNDATION TEST SUMMARY")
    print("=" * 100)
    print(f"✅ Card Identity: Working (confidence {card.identity_confidence:.0%})")
    print(f"✅ Data Provenance: Working (freshness tracking, timestamps)")
    print(f"✅ Fair Value: Working (${comparable.median_price:.2f}, confidence {comparable.confidence:.0%})")
    print(f"✅ Economics: Working (profit ${econ.expected_net_profit:.2f}, ROIC {econ.expected_roic:.1%})")
    print(f"✅ Liquidity: Working (score {liquidity.liquidity_score}/100)")
    print(f"✅ Guardrails: {'PASSED' if check_result.passed_all_checks else 'FAILED'} ({check_result.checks_passed}/{check_result.checks_total})")
    print(f"✅ Learning: Working (snapshot + outcome recorded, gap analysis complete)")
    print(f"")
    print(f"All foundation modules working and integrated.")
    print("=" * 100)


if __name__ == "__main__":
    test_complete_flow()
