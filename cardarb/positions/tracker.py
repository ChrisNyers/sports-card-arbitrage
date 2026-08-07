"""Position lifecycle. Every function here is pure record-keeping — logging a
decision the user already made and executed manually on eBay/COMC themselves.
Nothing here places an order, lists an item, or moves money.
"""
from __future__ import annotations

from datetime import date, datetime

from cardarb.db.database import connection


def approve_opportunity(opportunity_id: int, actual_buy_price: float | None = None, notes: str = "") -> int:
    """Logs the user's manual approval/purchase and opens a tracked position."""
    with connection() as conn:
        opp = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
        if opp is None:
            raise ValueError(f"No opportunity with id {opportunity_id}")

        buy_price = actual_buy_price if actual_buy_price is not None else opp["current_price"]
        now = datetime.utcnow().isoformat()
        today = date.today().isoformat()

        conn.execute(
            """
            INSERT INTO approval_decisions (opportunity_id, decision, decided_at, notes, actual_buy_price)
            VALUES (?, 'approved', ?, ?, ?)
            """,
            (opportunity_id, now, notes, buy_price),
        )
        conn.execute("UPDATE opportunities SET status = 'approved' WHERE id = ?", (opportunity_id,))

        cursor = conn.execute(
            """
            INSERT INTO positions (card_id, opportunity_id, buy_price, buy_date, status, notes, created_at)
            VALUES (?, ?, ?, ?, 'open', ?, ?)
            """,
            (opp["card_id"], opportunity_id, buy_price, today, notes, now),
        )
        return cursor.lastrowid


def refresh_current_prices() -> int:
    """Updates open positions' current_market_price from the latest features row."""
    now = datetime.utcnow().isoformat()
    updated = 0
    with connection() as conn:
        open_positions = conn.execute("SELECT id, card_id FROM positions WHERE status = 'open'").fetchall()
        for pos in open_positions:
            latest = conn.execute(
                """
                SELECT avg_sold_price_7d, avg_sold_price_30d FROM features
                WHERE card_id = ? ORDER BY as_of_date DESC LIMIT 1
                """,
                (pos["card_id"],),
            ).fetchone()
            if latest is None:
                continue
            price = (
                latest["avg_sold_price_7d"] if latest["avg_sold_price_7d"] is not None else latest["avg_sold_price_30d"]
            )
            if price is None:
                continue
            conn.execute(
                "UPDATE positions SET current_market_price = ?, current_price_updated_at = ? WHERE id = ?",
                (price, now, pos["id"]),
            )
            updated += 1
    return updated


def close_position(position_id: int, sell_price: float, sell_date: date, sell_fees: float = 0.0) -> None:
    """Logs the user's manual sale of an already-open position."""
    with connection() as conn:
        row = conn.execute("SELECT id FROM positions WHERE id = ?", (position_id,)).fetchone()
        if row is None:
            raise ValueError(f"No position with id {position_id}")
        conn.execute(
            """
            UPDATE positions
            SET sell_price = ?, sell_date = ?, sell_fees = ?, status = 'closed'
            WHERE id = ?
            """,
            (sell_price, sell_date.isoformat(), sell_fees, position_id),
        )
