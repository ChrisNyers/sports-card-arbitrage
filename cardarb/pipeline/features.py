"""Turns raw_* ingested rows into the engineered `features` row per card/day.

Note on windows: each ingest call only pulls a `lookback_days` (default 30)
window of listings relative to its own as_of_date, so there isn't a full
60-day history available to compute a true month-over-month delta. Momentum
signals here are deliberately defined within that 30-day budget (e.g.
comparing the most recent 7 days against the trailing 30-day baseline)
rather than requesting data we don't have.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from cardarb.db.database import connection


def _sold_listings_df(conn, card_id: int, as_of_date: date) -> pd.DataFrame:
    query = """
        SELECT price, sold_at FROM raw_listings
        WHERE card_id = ? AND listing_type = 'sold'
          AND ingested_at = (SELECT MAX(ingested_at) FROM raw_listings WHERE card_id = ?)
    """
    df = pd.read_sql_query(query, conn, params=(card_id, card_id))
    if df.empty:
        return df
    df["sold_at"] = pd.to_datetime(df["sold_at"]).dt.date
    return df


def _active_listings_count(conn, card_id: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) as cnt FROM raw_listings
        WHERE card_id = ? AND listing_type = 'active'
          AND ingested_at = (SELECT MAX(ingested_at) FROM raw_listings WHERE card_id = ?)
        """,
        (card_id, card_id),
    ).fetchone()
    return row["cnt"] if row else 0


def _social_features(conn, card_id: int) -> tuple[int, float]:
    df = pd.read_sql_query(
        """
        SELECT mention_count, sentiment_score FROM raw_social_mentions
        WHERE card_id = ?
          AND ingested_at = (SELECT MAX(ingested_at) FROM raw_social_mentions WHERE card_id = ?)
        """,
        conn,
        params=(card_id, card_id),
    )
    if df.empty:
        return 0, 0.0
    total_mentions = int(df["mention_count"].sum())
    if total_mentions > 0:
        weighted_sentiment = (df["sentiment_score"] * df["mention_count"]).sum() / total_mentions
    else:
        weighted_sentiment = float(df["sentiment_score"].mean())
    return total_mentions, round(float(weighted_sentiment), 4)


def _psa_growth_pct(conn, card_id: int) -> float:
    row = conn.execute(
        """
        SELECT population, population_change_30d FROM raw_psa_pop
        WHERE card_id = ?
          AND ingested_at = (SELECT MAX(ingested_at) FROM raw_psa_pop WHERE card_id = ?)
        """,
        (card_id, card_id),
    ).fetchone()
    if not row:
        return 0.0
    prior_pop = row["population"] - row["population_change_30d"]
    if prior_pop <= 0:
        return 0.0
    return round(row["population_change_30d"] / prior_pop * 100, 3)


def _news_sentiment(conn, card_id: int) -> float:
    df = pd.read_sql_query(
        """
        SELECT sentiment_score FROM raw_news
        WHERE card_id = ?
          AND ingested_at = (SELECT MAX(ingested_at) FROM raw_news WHERE card_id = ?)
        """,
        conn,
        params=(card_id, card_id),
    )
    if df.empty:
        return 0.0
    return round(float(df["sentiment_score"].mean()), 4)


def compute_card_features(conn, card_id: int, as_of_date: date) -> dict:
    sold = _sold_listings_df(conn, card_id, as_of_date)

    def window_avg(days: int) -> float | None:
        if sold.empty:
            return None
        cutoff = as_of_date - timedelta(days=days)
        subset = sold[sold["sold_at"] >= cutoff]
        return round(float(subset["price"].mean()), 2) if not subset.empty else None

    avg_7d = window_avg(7)
    avg_30d = window_avg(30)

    price_change_pct_7d = None
    if avg_7d is not None and avg_30d:
        price_change_pct_7d = round((avg_7d / avg_30d - 1) * 100, 3)

    price_change_pct_30d = None
    if not sold.empty:
        ordered = sold.sort_values("sold_at")
        first_price = ordered.iloc[0]["price"]
        last_price = ordered.iloc[-1]["price"]
        if first_price:
            price_change_pct_30d = round((last_price / first_price - 1) * 100, 3)

    sales_velocity_7d = 0
    listing_count_trend_pct = None
    if not sold.empty:
        recent_cutoff = as_of_date - timedelta(days=7)
        prior_cutoff = as_of_date - timedelta(days=14)
        recent_count = int((sold["sold_at"] >= recent_cutoff).sum())
        prior_count = int(((sold["sold_at"] >= prior_cutoff) & (sold["sold_at"] < recent_cutoff)).sum())
        sales_velocity_7d = recent_count
        listing_count_trend_pct = round((recent_count - prior_count) / max(1, prior_count) * 100, 3)

    price_volatility_30d = None
    if len(sold) > 1:
        mean_price = sold["price"].mean()
        if mean_price:
            price_volatility_30d = round(float(sold["price"].std() / mean_price * 100), 3)

    listing_count_active = _active_listings_count(conn, card_id)
    mention_count, sentiment_avg = _social_features(conn, card_id)
    psa_growth = _psa_growth_pct(conn, card_id)
    news_sentiment = _news_sentiment(conn, card_id)

    return {
        "card_id": card_id,
        "as_of_date": as_of_date.isoformat(),
        "avg_sold_price_7d": avg_7d,
        "avg_sold_price_30d": avg_30d,
        "price_change_pct_7d": price_change_pct_7d,
        "price_change_pct_30d": price_change_pct_30d,
        "sales_velocity_7d": sales_velocity_7d,
        "listing_count_active": listing_count_active,
        "listing_count_trend_pct": listing_count_trend_pct,
        "price_volatility_30d": price_volatility_30d,
        "social_mention_count_7d": mention_count,
        "social_sentiment_avg_7d": sentiment_avg,
        "psa_pop_growth_30d_pct": psa_growth,
        "news_sentiment_avg_7d": news_sentiment,
    }


def build_features(as_of_date: date) -> pd.DataFrame:
    with connection() as conn:
        card_ids = [row["card_id"] for row in conn.execute("SELECT card_id FROM cards").fetchall()]
        rows = [compute_card_features(conn, cid, as_of_date) for cid in card_ids]

        for row in rows:
            conn.execute(
                """
                INSERT INTO features (
                    card_id, as_of_date, avg_sold_price_7d, avg_sold_price_30d,
                    price_change_pct_7d, price_change_pct_30d, sales_velocity_7d,
                    listing_count_active, listing_count_trend_pct, price_volatility_30d,
                    social_mention_count_7d, social_sentiment_avg_7d, psa_pop_growth_30d_pct,
                    news_sentiment_avg_7d
                ) VALUES (
                    :card_id, :as_of_date, :avg_sold_price_7d, :avg_sold_price_30d,
                    :price_change_pct_7d, :price_change_pct_30d, :sales_velocity_7d,
                    :listing_count_active, :listing_count_trend_pct, :price_volatility_30d,
                    :social_mention_count_7d, :social_sentiment_avg_7d, :psa_pop_growth_30d_pct,
                    :news_sentiment_avg_7d
                )
                ON CONFLICT(card_id, as_of_date) DO UPDATE SET
                    avg_sold_price_7d=excluded.avg_sold_price_7d,
                    avg_sold_price_30d=excluded.avg_sold_price_30d,
                    price_change_pct_7d=excluded.price_change_pct_7d,
                    price_change_pct_30d=excluded.price_change_pct_30d,
                    sales_velocity_7d=excluded.sales_velocity_7d,
                    listing_count_active=excluded.listing_count_active,
                    listing_count_trend_pct=excluded.listing_count_trend_pct,
                    price_volatility_30d=excluded.price_volatility_30d,
                    social_mention_count_7d=excluded.social_mention_count_7d,
                    social_sentiment_avg_7d=excluded.social_sentiment_avg_7d,
                    psa_pop_growth_30d_pct=excluded.psa_pop_growth_30d_pct,
                    news_sentiment_avg_7d=excluded.news_sentiment_avg_7d
                """,
                row,
            )

    return pd.DataFrame(rows)
