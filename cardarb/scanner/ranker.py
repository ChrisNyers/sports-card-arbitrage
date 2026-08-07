from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from cardarb.config import DEFAULT_GRADING_COST, DEFAULT_SHIPPING_COST, MARKETPLACE_FEE_PCT
from cardarb.db.database import connection

BUBBLE_PENALTY_WEIGHT = 0.3
# Recent 7d momentum is used as the target-sell projection; clipped so one
# noisy week of mock sales doesn't imply an absurd target price.
MOMENTUM_CLIP = (-0.30, 0.50)


def estimate_cost_basis(
    buy_price: float,
    fee_pct: float = MARKETPLACE_FEE_PCT,
    shipping: float = DEFAULT_SHIPPING_COST,
    grading_cost: float = DEFAULT_GRADING_COST,
) -> float:
    return round(buy_price * (1 + fee_pct) + shipping + grading_cost, 2)


def estimate_target_sell_price(current_price: float, momentum_pct: float) -> float:
    clipped = max(MOMENTUM_CLIP[0], min(MOMENTUM_CLIP[1], momentum_pct / 100))
    return round(current_price * (1 + clipped), 2)


def estimate_roic(
    buy_price: float,
    target_sell_price: float,
    sell_fee_pct: float = MARKETPLACE_FEE_PCT,
    **cost_kwargs,
) -> float:
    cost_basis = estimate_cost_basis(buy_price, **cost_kwargs)
    if cost_basis <= 0:
        return 0.0
    net_sell_proceeds = target_sell_price * (1 - sell_fee_pct)
    return round((net_sell_proceeds - cost_basis) / cost_basis * 100, 3)


def opportunity_score(
    roic_pct: float,
    ml_prob_rise: float,
    bubble_score: float,
    bubble_penalty_weight: float = BUBBLE_PENALTY_WEIGHT,
) -> float:
    bubble_penalty = (bubble_score / 100) * bubble_penalty_weight
    return round(roic_pct * ml_prob_rise * (1 - bubble_penalty), 4)


def rank_opportunities(
    features_df: pd.DataFrame, predictions_df: pd.DataFrame, bubble_df: pd.DataFrame
) -> pd.DataFrame:
    merged = features_df.merge(
        predictions_df[["card_id", "prob_price_rise"]], on="card_id", how="inner"
    ).merge(bubble_df[["card_id", "composite_score"]], on="card_id", how="inner")

    merged["current_price"] = merged["avg_sold_price_7d"].fillna(merged["avg_sold_price_30d"])
    merged = merged.dropna(subset=["current_price"]).copy()
    merged["momentum_pct"] = merged["price_change_pct_7d"].fillna(0.0)

    merged["target_sell_price"] = merged.apply(
        lambda r: estimate_target_sell_price(r["current_price"], r["momentum_pct"]), axis=1
    )
    merged["estimated_cost_basis"] = merged["current_price"].apply(estimate_cost_basis)
    merged["estimated_roic_pct"] = merged.apply(
        lambda r: estimate_roic(r["current_price"], r["target_sell_price"]), axis=1
    )
    merged["opportunity_score"] = merged.apply(
        lambda r: opportunity_score(r["estimated_roic_pct"], r["prob_price_rise"], r["composite_score"]), axis=1
    )

    merged = merged.sort_values("opportunity_score", ascending=False).reset_index(drop=True)
    merged["rank"] = merged.index + 1

    merged = merged.rename(
        columns={"prob_price_rise": "ml_prob_price_rise", "composite_score": "bubble_composite_score"}
    )
    return merged[
        [
            "card_id",
            "as_of_date",
            "current_price",
            "target_sell_price",
            "estimated_cost_basis",
            "estimated_roic_pct",
            "ml_prob_price_rise",
            "bubble_composite_score",
            "opportunity_score",
            "rank",
        ]
    ]


def run_scan(as_of_date: date) -> pd.DataFrame:
    with connection() as conn:
        as_of_str = as_of_date.isoformat()
        features_df = pd.read_sql_query("SELECT * FROM features WHERE as_of_date = ?", conn, params=(as_of_str,))
        predictions_df = pd.read_sql_query(
            "SELECT * FROM ml_predictions WHERE as_of_date = ?", conn, params=(as_of_str,)
        )
        bubble_df = pd.read_sql_query("SELECT * FROM bubble_scores WHERE as_of_date = ?", conn, params=(as_of_str,))

        if features_df.empty or predictions_df.empty or bubble_df.empty:
            return pd.DataFrame()

        ranked = rank_opportunities(features_df, predictions_df, bubble_df)

        # Only unreviewed opportunities from a prior run of the same day are
        # replaced, so re-running daily-run twice on one day never orphans an
        # already-approved opportunity's linked position.
        conn.execute("DELETE FROM opportunities WHERE as_of_date = ? AND status = 'new'", (as_of_str,))

        created_at = datetime.utcnow().isoformat()
        for _, row in ranked.iterrows():
            conn.execute(
                """
                INSERT INTO opportunities (
                    card_id, as_of_date, current_price, target_sell_price, estimated_cost_basis,
                    estimated_roic_pct, ml_prob_price_rise, bubble_composite_score, opportunity_score,
                    rank, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
                """,
                (
                    int(row["card_id"]),
                    row["as_of_date"],
                    float(row["current_price"]),
                    float(row["target_sell_price"]),
                    float(row["estimated_cost_basis"]),
                    float(row["estimated_roic_pct"]),
                    float(row["ml_prob_price_rise"]),
                    float(row["bubble_composite_score"]),
                    float(row["opportunity_score"]),
                    int(row["rank"]),
                    created_at,
                ),
            )

    return ranked
