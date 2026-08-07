"""Environment loading and adapter factories.

Each `get_*_source()` factory picks the Mock adapter unless the relevant
credential env var is set, in which case it picks the Real adapter. Call
sites (the pipeline) never need to change when real credentials arrive.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "var" / "arbitrage.db"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Marketplace fee assumptions used by the scanner's cost-basis/ROIC math.
MARKETPLACE_FEE_PCT = 0.129
DEFAULT_SHIPPING_COST = 5.0
DEFAULT_GRADING_COST = 0.0

DAILY_REPORT_TOP_N = 20


def get_listings_source():
    from cardarb.sources.ebay import EbayAdapter, MockEbayAdapter

    return EbayAdapter() if os.getenv("EBAY_APP_ID") else MockEbayAdapter()


def get_social_sources():
    from cardarb.sources.reddit import MockRedditAdapter, RedditAdapter
    from cardarb.sources.twitter import MockTwitterAdapter, TwitterAdapter

    sources = []
    sources.append(TwitterAdapter() if os.getenv("TWITTER_BEARER_TOKEN") else MockTwitterAdapter())
    sources.append(
        RedditAdapter() if os.getenv("REDDIT_CLIENT_ID") else MockRedditAdapter()
    )
    return sources


def get_population_source():
    from cardarb.sources.psa import MockPsaAdapter, PsaAdapter

    return PsaAdapter() if os.getenv("PSA_API_KEY") else MockPsaAdapter()


def get_news_source():
    from cardarb.sources.news import MockNewsAdapter, NewsAdapter

    return NewsAdapter() if os.getenv("NEWS_API_KEY") else MockNewsAdapter()


def smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("ALERT_EMAIL_TO"))
