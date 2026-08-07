from cardarb.scanner.ranker import (
    estimate_cost_basis,
    estimate_roic,
    estimate_target_sell_price,
    opportunity_score,
)


def test_estimate_cost_basis_includes_fees_and_shipping():
    cost = estimate_cost_basis(100.0, fee_pct=0.129, shipping=5.0, grading_cost=0.0)
    assert cost == round(100 * 1.129 + 5.0, 2)


def test_estimate_target_sell_price_clips_momentum():
    target_up = estimate_target_sell_price(100.0, momentum_pct=200.0)
    assert target_up == round(100.0 * 1.50, 2)

    target_down = estimate_target_sell_price(100.0, momentum_pct=-200.0)
    assert target_down == round(100.0 * 0.70, 2)


def test_estimate_roic_positive_when_sell_exceeds_cost_basis():
    assert estimate_roic(buy_price=100.0, target_sell_price=150.0) > 0


def test_estimate_roic_negative_when_sell_below_cost_basis():
    assert estimate_roic(buy_price=100.0, target_sell_price=90.0) < 0


def test_opportunity_score_penalizes_high_bubble_risk():
    low_bubble = opportunity_score(roic_pct=20.0, ml_prob_rise=0.8, bubble_score=10.0)
    high_bubble = opportunity_score(roic_pct=20.0, ml_prob_rise=0.8, bubble_score=100.0)
    assert low_bubble > high_bubble
