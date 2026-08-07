"""Deterministic, seeded mock market data generators.

Every function here is a pure function of (card_id, ...) — same inputs always
produce the same outputs, so re-running the pipeline on the same as_of_date
is reproducible, and the ML training set (built by simulating a longer
synthetic window) uses the exact same generators as live "ingest".

Each card is deterministically assigned a market "profile" that drives its
simulated price path, so the bubble index and ML model have real signal to
find (some cards trend up, some spike-and-fade like a bubble, some are flat,
some decline) rather than pure noise.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from functools import lru_cache

from cardarb.db.models import Card, ListingRecord, NewsRecord, PSAPopRecord, SocialMentionRecord

EPOCH = date(2023, 1, 1)
# Simulated from a fixed origin far enough out to cover both live "as_of today"
# calls and ML training snapshots. Must stay ahead of real usage dates.
HORIZON_DAYS = 2200

PROFILES = ["flat", "trending_up", "bubble_spike", "declining"]
PROFILE_WEIGHTS = [0.40, 0.25, 0.20, 0.15]

_GRADE_MULTIPLIER = {
    "PSA 10": 3.0,
    "PSA 9": 1.6,
    "PSA 8": 1.0,
    "PSA 7": 0.7,
}

_HEADLINE_TEMPLATES = [
    "{player} named to all-star roster, card values reacting",
    "{player} injury update sends shockwaves through the hobby",
    "Grading backlog easing for {player} submissions",
    "{player} rookie card breaks auction record",
    "Hobby analysts split on {player} card longevity",
]


def _rng(card_id: int, salt: str) -> random.Random:
    return random.Random(f"card-{card_id}-{salt}")


def card_profile(card_id: int) -> str:
    return _rng(card_id, "profile").choices(PROFILES, weights=PROFILE_WEIGHTS, k=1)[0]


def base_price(card: Card) -> float:
    r = _rng(card.card_id, "base_price")
    era_factor = 1.0 if card.year >= 2018 else max(0.6, 1.0 - (2018 - card.year) * 0.02)
    grade_factor = _GRADE_MULTIPLIER.get(card.grade, 1.0)
    return round(r.uniform(20, 300) * era_factor * grade_factor, 2)


@lru_cache(maxsize=None)
def _full_price_series(card: Card) -> dict[date, float]:
    """Daily closing price for the entire simulated horizon (EPOCH..EPOCH+HORIZON_DAYS).

    Cached per card and always walked from day_offset=0 at EPOCH, so the price
    resolved for any given calendar date is stable no matter what window
    (as_of_date, num_days) it's later sliced through — required so that
    training labels (price at snapshot vs. snapshot+30) are self-consistent.
    """
    profile = card_profile(card.card_id)
    r = _rng(card.card_id, "price_walk")
    price = base_price(card)

    spike_day = r.randint(int(HORIZON_DAYS * 0.3), int(HORIZON_DAYS * 0.7))

    series: dict[date, float] = {}
    for day_offset in range(HORIZON_DAYS + 1):
        current_date = EPOCH + timedelta(days=day_offset)

        if profile == "flat":
            drift = 0.0002
            volatility = 0.01
        elif profile == "trending_up":
            drift = 0.0025
            volatility = 0.015
        elif profile == "declining":
            drift = -0.0018
            volatility = 0.015
        else:  # bubble_spike
            if day_offset < spike_day:
                drift = 0.001
                volatility = 0.012
            elif day_offset < spike_day + 20:
                drift = 0.02  # sharp run-up
                volatility = 0.03
            else:
                drift = -0.012  # fade after the spike
                volatility = 0.035

        shock = r.gauss(drift, volatility)
        price = max(2.0, price * (1 + shock))
        series[current_date] = round(price, 2)

    return series


def price_at(card: Card, on_date: date) -> float:
    series = _full_price_series(card)
    clamped = min(max(on_date, EPOCH), EPOCH + timedelta(days=HORIZON_DAYS))
    return series[clamped]


def simulate_price_series(card: Card, as_of_date: date, num_days: int = 400) -> list[tuple[date, float]]:
    """Daily closing price from (as_of_date - num_days) through as_of_date."""
    series = _full_price_series(card)
    start_date = as_of_date - timedelta(days=num_days)
    return [(d, p) for d, p in series.items() if start_date <= d <= as_of_date]


def generate_listings(card: Card, as_of_date: date, lookback_days: int = 30) -> list[ListingRecord]:
    series = dict(simulate_price_series(card, as_of_date, num_days=lookback_days + 5))
    r = _rng(card.card_id, f"listings-{as_of_date.isoformat()}")
    profile = card_profile(card.card_id)
    base_sales_per_day = {"flat": 0.6, "trending_up": 1.1, "bubble_spike": 1.4, "declining": 0.4}[profile]

    listings: list[ListingRecord] = []
    for day_offset in range(lookback_days):
        day = as_of_date - timedelta(days=lookback_days - day_offset)
        day_price = series.get(day, base_price(card))
        num_sales = _poisson(r, base_sales_per_day)
        for _ in range(num_sales):
            noise = r.uniform(-0.06, 0.06)
            listings.append(
                ListingRecord(
                    card_id=card.card_id,
                    source="ebay",
                    listing_type="sold",
                    price=round(day_price * (1 + noise), 2),
                    listed_at=datetime.combine(day, datetime.min.time()),
                    sold_at=datetime.combine(day, datetime.min.time()) + timedelta(hours=r.randint(1, 23)),
                )
            )

    num_active = max(1, int(r.uniform(2, 10)))
    current_price = series[as_of_date]
    for _ in range(num_active):
        markup = r.uniform(0.02, 0.20)
        listings.append(
            ListingRecord(
                card_id=card.card_id,
                source="ebay",
                listing_type="active",
                price=round(current_price * (1 + markup), 2),
                listed_at=datetime.combine(as_of_date - timedelta(days=r.randint(0, 5)), datetime.min.time()),
                sold_at=None,
            )
        )
    return listings


def _poisson(r: random.Random, lam: float) -> int:
    # stdlib random.Random has no poisson(); Knuth's algorithm.
    import math

    l = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= r.random()
        if p <= l:
            return k - 1


def generate_social_mentions(card: Card, as_of_date: date, lookback_days: int = 7) -> list[SocialMentionRecord]:
    profile = card_profile(card.card_id)
    r = _rng(card.card_id, f"social-{as_of_date.isoformat()}")

    base_mentions = {"flat": 15, "trending_up": 60, "bubble_spike": 150, "declining": 8}[profile]
    base_sentiment = {"flat": 0.05, "trending_up": 0.35, "bubble_spike": 0.55, "declining": -0.25}[profile]

    records = []
    for source in ("twitter", "reddit"):
        mentions = max(0, int(r.gauss(base_mentions, base_mentions * 0.3)))
        sentiment = max(-1.0, min(1.0, r.gauss(base_sentiment, 0.15)))
        records.append(
            SocialMentionRecord(
                card_id=card.card_id,
                source=source,
                mention_count=mentions,
                sentiment_score=round(sentiment, 3),
                window_start=as_of_date - timedelta(days=lookback_days),
                window_end=as_of_date,
            )
        )
    return records


def generate_psa_pop(card: Card, as_of_date: date) -> PSAPopRecord:
    profile = card_profile(card.card_id)
    r = _rng(card.card_id, "psa_pop")
    growth_pct = {"flat": 0.01, "trending_up": 0.03, "bubble_spike": 0.08, "declining": 0.005}[profile]

    days_since_epoch = (as_of_date - EPOCH).days
    base_pop = max(50, int(r.uniform(200, 5000)))
    population = int(base_pop * (1 + growth_pct) ** (days_since_epoch / 30))
    population_change_30d = int(population * growth_pct)

    return PSAPopRecord(
        card_id=card.card_id,
        grade=card.grade,
        population=population,
        population_change_30d=population_change_30d,
    )


def generate_news(card: Card, as_of_date: date, lookback_days: int = 7) -> list[NewsRecord]:
    profile = card_profile(card.card_id)
    r = _rng(card.card_id, f"news-{as_of_date.isoformat()}")
    base_sentiment = {"flat": 0.0, "trending_up": 0.3, "bubble_spike": 0.5, "declining": -0.3}[profile]

    num_headlines = r.randint(0, 3)
    news = []
    for _ in range(num_headlines):
        template = r.choice(_HEADLINE_TEMPLATES)
        sentiment = max(-1.0, min(1.0, r.gauss(base_sentiment, 0.2)))
        news.append(
            NewsRecord(
                card_id=card.card_id,
                headline=template.format(player=card.player_name),
                sentiment_score=round(sentiment, 3),
                published_at=datetime.combine(
                    as_of_date - timedelta(days=r.randint(0, lookback_days)), datetime.min.time()
                ),
            )
        )
    return news
