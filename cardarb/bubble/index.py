from __future__ import annotations

from datetime import date

import pandas as pd

from cardarb.bubble.signals import compute_sub_scores
from cardarb.db.database import connection

DEFAULT_WEIGHTS = {
    "velocity_signal": 0.25,
    "volatility_signal": 0.20,
    "sentiment_signal": 0.20,
    "listing_trend_signal": 0.15,
    "psa_pop_signal": 0.20,
}

RISK_THRESHOLDS = (40, 60, 80)  # low < 40 <= moderate < 60 <= elevated < 80 <= bubble_risk


def composite_bubble_score(sub_scores: dict, weights: dict = DEFAULT_WEIGHTS) -> float:
    return sum(sub_scores[key] * weight for key, weight in weights.items())


def classify_risk(score: float) -> str:
    low, moderate, elevated = RISK_THRESHOLDS
    if score < low:
        return "low"
    if score < moderate:
        return "moderate"
    if score < elevated:
        return "elevated"
    return "bubble_risk"


def compute_bubble_scores(features_df: pd.DataFrame, weights: dict = DEFAULT_WEIGHTS) -> pd.DataFrame:
    sub = compute_sub_scores(features_df)
    signal_cols = list(weights.keys())
    sub["composite_score"] = sub[signal_cols].mul(pd.Series(weights)).sum(axis=1)
    sub["risk_label"] = sub["composite_score"].apply(classify_risk)
    sub["as_of_date"] = features_df["as_of_date"].values
    return sub


def run_bubble_scoring(as_of_date: date) -> pd.DataFrame:
    with connection() as conn:
        features_df = pd.read_sql_query(
            "SELECT * FROM features WHERE as_of_date = ?", conn, params=(as_of_date.isoformat(),)
        )
        if features_df.empty:
            return features_df

        scores_df = compute_bubble_scores(features_df)

        for _, row in scores_df.iterrows():
            conn.execute(
                """
                INSERT INTO bubble_scores (
                    card_id, as_of_date, velocity_signal, volatility_signal, sentiment_signal,
                    listing_trend_signal, psa_pop_signal, composite_score, risk_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(card_id, as_of_date) DO UPDATE SET
                    velocity_signal=excluded.velocity_signal,
                    volatility_signal=excluded.volatility_signal,
                    sentiment_signal=excluded.sentiment_signal,
                    listing_trend_signal=excluded.listing_trend_signal,
                    psa_pop_signal=excluded.psa_pop_signal,
                    composite_score=excluded.composite_score,
                    risk_label=excluded.risk_label
                """,
                (
                    int(row["card_id"]),
                    row["as_of_date"],
                    float(row["velocity_signal"]),
                    float(row["volatility_signal"]),
                    float(row["sentiment_signal"]),
                    float(row["listing_trend_signal"]),
                    float(row["psa_pop_signal"]),
                    float(row["composite_score"]),
                    row["risk_label"],
                ),
            )

    return scores_df
