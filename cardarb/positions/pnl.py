"""P&L is always computed live from `positions` — there is deliberately no
separate pnl table, so there's a single source of truth and no risk of stored
and derived numbers drifting apart.
"""
from __future__ import annotations

from cardarb.config import MARKETPLACE_FEE_PCT
from cardarb.db.database import connection


def position_pnl(position: dict) -> dict:
    buy_price = position["buy_price"]
    buy_fees = position["buy_fees"] or 0.0
    quantity = position["quantity"] or 1
    cost_basis = (buy_price + buy_fees) * quantity

    if position["status"] == "closed" and position["sell_price"] is not None:
        sell_fees = position["sell_fees"] or 0.0
        proceeds = (position["sell_price"] - sell_fees) * quantity
        realized = round(proceeds - cost_basis, 2)
        return {
            "realized": realized,
            "unrealized": 0.0,
            "roic_pct": round(realized / cost_basis * 100, 3) if cost_basis else 0.0,
        }

    current_price = position["current_market_price"]
    if current_price is None:
        return {"realized": 0.0, "unrealized": 0.0, "roic_pct": 0.0}

    estimated_sell_fees = current_price * MARKETPLACE_FEE_PCT
    unrealized_proceeds = (current_price - estimated_sell_fees) * quantity
    unrealized = round(unrealized_proceeds - cost_basis, 2)
    return {
        "realized": 0.0,
        "unrealized": unrealized,
        "roic_pct": round(unrealized / cost_basis * 100, 3) if cost_basis else 0.0,
    }


def portfolio_summary() -> dict:
    with connection() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM positions").fetchall()]

    open_positions = [r for r in rows if r["status"] == "open"]
    closed_positions = [r for r in rows if r["status"] == "closed"]

    closed_pnls = [position_pnl(r) for r in closed_positions]
    open_pnls = [position_pnl(r) for r in open_positions]

    total_realized = round(sum(p["realized"] for p in closed_pnls), 2)
    total_unrealized = round(sum(p["unrealized"] for p in open_pnls), 2)

    winning_closed = sum(1 for p in closed_pnls if p["realized"] > 0)
    win_rate_pct = round(winning_closed / len(closed_positions) * 100, 2) if closed_positions else None

    closed_roics = [p["roic_pct"] for p in closed_pnls]
    avg_roic_pct_closed = round(sum(closed_roics) / len(closed_roics), 3) if closed_roics else None

    total_capital_deployed = round(
        sum((r["buy_price"] + (r["buy_fees"] or 0)) * (r["quantity"] or 1) for r in rows), 2
    )

    return {
        "open_count": len(open_positions),
        "closed_count": len(closed_positions),
        "win_rate_pct": win_rate_pct,
        "total_realized_pnl": total_realized,
        "total_unrealized_pnl": total_unrealized,
        "avg_roic_pct_closed": avg_roic_pct_closed,
        "total_capital_deployed": total_capital_deployed,
    }
