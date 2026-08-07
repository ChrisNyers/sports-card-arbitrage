#!/usr/bin/env bash
# Thin wrapper for cron/launchd. Example crontab entry (runs at 8am daily):
#   0 8 * * * /path/to/sports-card-arbitrage/scripts/daily_run.sh >> /path/to/sports-card-arbitrage/var/daily_run.log 2>&1
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

source .venv/bin/activate
cardarb daily-run
