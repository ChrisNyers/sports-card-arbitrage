import pandas as pd

from cardarb.bubble.index import classify_risk, composite_bubble_score, compute_bubble_scores


def test_composite_bubble_score_weighted_average():
    sub_scores = {
        "velocity_signal": 100,
        "volatility_signal": 0,
        "sentiment_signal": 50,
        "listing_trend_signal": 50,
        "psa_pop_signal": 50,
    }
    score = composite_bubble_score(sub_scores)
    expected = 100 * 0.25 + 0 * 0.20 + 50 * 0.20 + 50 * 0.15 + 50 * 0.20
    assert abs(score - expected) < 1e-6


def test_classify_risk_thresholds():
    assert classify_risk(10) == "low"
    assert classify_risk(45) == "moderate"
    assert classify_risk(65) == "elevated"
    assert classify_risk(90) == "bubble_risk"


def test_compute_bubble_scores_shape_and_ranking():
    features_df = pd.DataFrame(
        {
            "card_id": [1, 2, 3],
            "as_of_date": ["2026-06-01"] * 3,
            "sales_velocity_7d": [1, 5, 10],
            "price_volatility_30d": [2.0, 10.0, 30.0],
            "social_sentiment_avg_7d": [0.0, 0.2, 0.5],
            "news_sentiment_avg_7d": [0.0, 0.1, 0.4],
            "listing_count_trend_pct": [-10, 0, 20],
            "psa_pop_growth_30d_pct": [1.0, 3.0, 8.0],
        }
    )
    scores = compute_bubble_scores(features_df)

    assert set(scores["card_id"]) == {1, 2, 3}
    assert scores["composite_score"].between(0, 100).all()
    assert scores["risk_label"].isin(["low", "moderate", "elevated", "bubble_risk"]).all()

    top_card_id = scores.sort_values("composite_score", ascending=False).iloc[0]["card_id"]
    assert top_card_id == 3
