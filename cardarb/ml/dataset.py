"""Builds a synthetic labeled training set for the price-rise classifier.

There's no real trade history yet, so training data comes from re-running the
same mock generators used at inference time across many (card, snapshot_date)
pairs, with the label derived by comparing the underlying simulated price at
the snapshot date vs. 30 days later. Because `generators.price_at()` is keyed
off a fixed absolute origin (see generators.py), the label is consistent with
whatever features would actually be computed live for that snapshot date.

Deliberately not a clean 100%-separable signal: sold-price noise, and profiles
overlapping in feature space, keep this an honest ~60-65% baseline demo,
matching the target in the user's Phase 1 spec.
"""
from __future__ import annotations

import random
import statistics
from datetime import date, timedelta

import pandas as pd

from cardarb.db.models import Card
from cardarb.sources.mock_data import generators
from cardarb.sources.mock_data.card_catalog import get_cards

FEATURE_COLUMNS = [
    "avg_sold_price_7d",
    "avg_sold_price_30d",
    "price_change_pct_7d",
    "price_change_pct_30d",
    "sales_velocity_7d",
    "listing_count_active",
    "listing_count_trend_pct",
    "price_volatility_30d",
    "social_mention_count_7d",
    "social_sentiment_avg_7d",
    "psa_pop_growth_30d_pct",
    "news_sentiment_avg_7d",
]

LABEL_COLUMN = "price_rose_30d"

MIN_DAY_OFFSET = 35  # needs 30d lookback + a few days buffer
LABEL_HORIZON_DAYS = 30


def _snapshot_features(card: Card, as_of_date: date) -> dict | None:
    listings = generators.generate_listings(card, as_of_date, lookback_days=30)
    sold = [l for l in listings if l.listing_type == "sold"]
    active = [l for l in listings if l.listing_type == "active"]

    if not sold:
        return None

    def window_avg(days: int) -> float | None:
        cutoff = as_of_date - timedelta(days=days)
        prices = [l.price for l in sold if l.sold_at.date() >= cutoff]
        return statistics.mean(prices) if prices else None

    avg_7d = window_avg(7)
    avg_30d = window_avg(30)
    if avg_7d is None or not avg_30d:
        return None

    price_change_pct_7d = round((avg_7d / avg_30d - 1) * 100, 3)

    sold_sorted = sorted(sold, key=lambda l: l.sold_at)
    first_price, last_price = sold_sorted[0].price, sold_sorted[-1].price
    price_change_pct_30d = round((last_price / first_price - 1) * 100, 3) if first_price else None

    recent_cutoff = as_of_date - timedelta(days=7)
    prior_cutoff = as_of_date - timedelta(days=14)
    recent_count = sum(1 for l in sold if l.sold_at.date() >= recent_cutoff)
    prior_count = sum(1 for l in sold if prior_cutoff <= l.sold_at.date() < recent_cutoff)
    listing_count_trend_pct = round((recent_count - prior_count) / max(1, prior_count) * 100, 3)

    prices = [l.price for l in sold]
    price_volatility_30d = None
    if len(prices) > 1:
        mean_p = statistics.mean(prices)
        if mean_p:
            price_volatility_30d = round(statistics.pstdev(prices) / mean_p * 100, 3)

    socials = generators.generate_social_mentions(card, as_of_date, lookback_days=7)
    total_mentions = sum(s.mention_count for s in socials)
    if total_mentions:
        sentiment_avg = sum(s.sentiment_score * s.mention_count for s in socials) / total_mentions
    else:
        sentiment_avg = statistics.mean(s.sentiment_score for s in socials) if socials else 0.0

    psa = generators.generate_psa_pop(card, as_of_date)
    prior_pop = psa.population - psa.population_change_30d
    psa_growth = round(psa.population_change_30d / prior_pop * 100, 3) if prior_pop > 0 else 0.0

    news = generators.generate_news(card, as_of_date, lookback_days=7)
    news_sentiment = round(statistics.mean(n.sentiment_score for n in news), 4) if news else 0.0

    return {
        "avg_sold_price_7d": round(avg_7d, 2),
        "avg_sold_price_30d": round(avg_30d, 2),
        "price_change_pct_7d": price_change_pct_7d,
        "price_change_pct_30d": price_change_pct_30d,
        "sales_velocity_7d": recent_count,
        "listing_count_active": len(active),
        "listing_count_trend_pct": listing_count_trend_pct,
        "price_volatility_30d": price_volatility_30d,
        "social_mention_count_7d": total_mentions,
        "social_sentiment_avg_7d": round(sentiment_avg, 4),
        "psa_pop_growth_30d_pct": psa_growth,
        "news_sentiment_avg_7d": news_sentiment,
    }


def build_training_dataset(snapshots_per_card: int = 150, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    max_offset = generators.HORIZON_DAYS - LABEL_HORIZON_DAYS - 5

    rows = []
    for card in get_cards():
        offsets = rng.sample(
            range(MIN_DAY_OFFSET, max_offset), min(snapshots_per_card, max_offset - MIN_DAY_OFFSET)
        )
        for offset in offsets:
            snapshot_date = generators.EPOCH + timedelta(days=offset)
            features = _snapshot_features(card, snapshot_date)
            if features is None or any(v is None for v in features.values()):
                continue

            price_now = generators.price_at(card, snapshot_date)
            price_future = generators.price_at(card, snapshot_date + timedelta(days=LABEL_HORIZON_DAYS))

            row = dict(features)
            row["card_id"] = card.card_id
            row["as_of_date"] = snapshot_date.isoformat()
            row[LABEL_COLUMN] = int(price_future > price_now)
            rows.append(row)

    return pd.DataFrame(rows)
