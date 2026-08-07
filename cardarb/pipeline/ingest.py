from __future__ import annotations

from datetime import date, datetime

from cardarb import config
from cardarb.db.database import connection
from cardarb.sources.mock_data.card_catalog import get_cards


def ensure_cards_loaded() -> list[int]:
    """Idempotently upsert the card catalog into the cards table. Returns all card_ids."""
    cards = get_cards()
    now = datetime.utcnow().isoformat()
    with connection() as conn:
        for card in cards:
            conn.execute(
                """
                INSERT INTO cards (card_id, player_name, year, set_name, card_number, variant, sport, grade, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(card_id) DO NOTHING
                """,
                (
                    card.card_id,
                    card.player_name,
                    card.year,
                    card.set_name,
                    card.card_number,
                    card.variant,
                    card.sport,
                    card.grade,
                    now,
                ),
            )
    return [c.card_id for c in cards]


def run_ingest(as_of_date: date) -> None:
    """Pull from all configured sources (mock or real) and persist raw_* rows for as_of_date."""
    card_ids = ensure_cards_loaded()
    now = datetime.utcnow().isoformat()

    listings_source = config.get_listings_source()
    social_sources = config.get_social_sources()
    population_source = config.get_population_source()
    news_source = config.get_news_source()

    listings = listings_source.fetch_listings(card_ids, as_of_date)
    mentions = [m for source in social_sources for m in source.fetch_mentions(card_ids, as_of_date)]
    pops = population_source.fetch_population(card_ids, as_of_date)
    news = news_source.fetch_news(card_ids, as_of_date)

    with connection() as conn:
        conn.executemany(
            """
            INSERT INTO raw_listings (card_id, source, listing_type, price, listed_at, sold_at, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    l.card_id,
                    l.source,
                    l.listing_type,
                    l.price,
                    l.listed_at.isoformat(),
                    l.sold_at.isoformat() if l.sold_at else None,
                    now,
                )
                for l in listings
            ],
        )
        conn.executemany(
            """
            INSERT INTO raw_social_mentions
                (card_id, source, mention_count, sentiment_score, window_start, window_end, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    m.card_id,
                    m.source,
                    m.mention_count,
                    m.sentiment_score,
                    m.window_start.isoformat(),
                    m.window_end.isoformat(),
                    now,
                )
                for m in mentions
            ],
        )
        conn.executemany(
            """
            INSERT INTO raw_psa_pop (card_id, grade, population, population_change_30d, ingested_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(p.card_id, p.grade, p.population, p.population_change_30d, now) for p in pops],
        )
        conn.executemany(
            """
            INSERT INTO raw_news (card_id, headline, sentiment_score, published_at, ingested_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(n.card_id, n.headline, n.sentiment_score, n.published_at.isoformat(), now) for n in news],
        )
