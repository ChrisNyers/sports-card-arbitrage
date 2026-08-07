# Sports Card Arbitrage — Phase 1 MVP

A local, single-user tool that scans sports card market data for arbitrage opportunities,
scores "bubble" risk, and tracks manually-executed trades and their P&L.

**This tool never executes trades or moves money.** It only surfaces ranked opportunities from
market data. You review the daily report, trade manually on eBay/COMC yourself, then log the
decision and outcome with the CLI so P&L and win rate are tracked accurately.

## Status: no live API credentials yet

All data sources (eBay, X/Twitter, Reddit, PSA, news) currently run against a deterministic
mock data generator (see `cardarb/sources/mock_data/`). This proves the pipeline works
end-to-end but the ML accuracy and bubble signals are **not** validated against real markets yet.
Add real credentials to `.env` (see `.env.example`) and implement the corresponding
`Real*Adapter` class in `cardarb/sources/` to switch a source from mock to live — no other
code changes needed.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

## Day-to-day usage

```bash
cardarb daily-run          # ingest -> features -> bubble -> predict -> scan -> report
cardarb report --top 20    # view the latest ranked opportunities
cardarb approve 12 --buy-price 45.00 --notes "PSA 10 rookie, good spread"
cardarb positions list
cardarb positions close 3 --sell-price 62.00 --sell-date 2026-08-01
cardarb pnl                # win rate, realized/unrealized P&L, avg ROIC
```

Schedule `daily-run` once a day via cron/launchd — see `scripts/daily_run.sh`.

## Tests

```bash
pytest
```
