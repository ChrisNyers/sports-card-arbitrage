from cardarb.positions.pnl import position_pnl


def _base_position(**overrides):
    position = {
        "buy_price": 100.0,
        "buy_fees": 0.0,
        "quantity": 1,
        "status": "open",
        "sell_price": None,
        "sell_fees": 0.0,
        "current_market_price": None,
    }
    position.update(overrides)
    return position


def test_open_position_with_no_current_price_is_zero():
    result = position_pnl(_base_position())
    assert result == {"realized": 0.0, "unrealized": 0.0, "roic_pct": 0.0}


def test_open_position_unrealized_gain():
    result = position_pnl(_base_position(current_market_price=150.0))
    assert result["unrealized"] > 0
    assert result["realized"] == 0.0
    assert result["roic_pct"] > 0


def test_closed_position_realized_gain():
    result = position_pnl(_base_position(status="closed", sell_price=150.0))
    assert result["realized"] > 0
    assert result["unrealized"] == 0.0


def test_closed_position_realized_loss():
    result = position_pnl(_base_position(status="closed", sell_price=80.0))
    assert result["realized"] < 0
    assert result["roic_pct"] < 0
