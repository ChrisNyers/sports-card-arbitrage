"""Turns raw engineered features into 0-100 sub-scores, normalized by
percentile rank across the current card universe. Percentile ranking (rather
than a fixed absolute scale) means the index is useful from day one without
needing a long historical baseline to calibrate against.

For each signal, higher = more bubble-risk-like (hot, crowded, possibly
overextended), not necessarily "bad" on its own.
"""
from __future__ import annotations

import pandas as pd


def _percentile_rank(series: pd.Series) -> pd.Series:
    filled = series.fillna(series.median())
    if filled.nunique() <= 1:
        return pd.Series(50.0, index=series.index)
    return filled.rank(pct=True) * 100


def velocity_signal(features_df: pd.DataFrame) -> pd.Series:
    return _percentile_rank(features_df["sales_velocity_7d"])


def volatility_signal(features_df: pd.DataFrame) -> pd.Series:
    return _percentile_rank(features_df["price_volatility_30d"])


def sentiment_signal(features_df: pd.DataFrame) -> pd.Series:
    combined = (
        features_df["social_sentiment_avg_7d"].fillna(0) + features_df["news_sentiment_avg_7d"].fillna(0)
    ) / 2
    return _percentile_rank(combined)


def listing_trend_signal(features_df: pd.DataFrame) -> pd.Series:
    return _percentile_rank(features_df["listing_count_trend_pct"])


def psa_pop_signal(features_df: pd.DataFrame) -> pd.Series:
    return _percentile_rank(features_df["psa_pop_growth_30d_pct"])


def compute_sub_scores(features_df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "card_id": features_df["card_id"],
            "velocity_signal": velocity_signal(features_df),
            "volatility_signal": volatility_signal(features_df),
            "sentiment_signal": sentiment_signal(features_df),
            "listing_trend_signal": listing_trend_signal(features_df),
            "psa_pop_signal": psa_pop_signal(features_df),
        }
    )
