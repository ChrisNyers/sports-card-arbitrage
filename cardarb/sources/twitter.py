from __future__ import annotations

from datetime import date

from cardarb.db.models import SocialMentionRecord
from cardarb.sources.base import SocialSource
from cardarb.sources.mock_data import generators
from cardarb.sources.mock_data.card_catalog import get_cards


class MockTwitterAdapter(SocialSource):
    def __init__(self) -> None:
        self._cards_by_id = {c.card_id: c for c in get_cards()}

    def fetch_mentions(
        self, card_ids: list[int], as_of_date: date, lookback_days: int = 7
    ) -> list[SocialMentionRecord]:
        records: list[SocialMentionRecord] = []
        for card_id in card_ids:
            card = self._cards_by_id[card_id]
            all_records = generators.generate_social_mentions(card, as_of_date, lookback_days)
            records.extend(r for r in all_records if r.source == "twitter")
        return records


class TwitterAdapter(SocialSource):
    """Real X/Twitter API adapter. Requires TWITTER_BEARER_TOKEN.

    Uses the Twitter API v2 recent-search endpoint to find mentions of sports
    cards by player name and year, aggregating mention counts and estimating
    sentiment per card per time window.
    """

    def __init__(self) -> None:
        import os
        self._bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self._cards_by_id = {c.card_id: c for c in get_cards()}
        if not self._bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN not set")

    def fetch_mentions(
        self, card_ids: list[int], as_of_date: date, lookback_days: int = 7
    ) -> list[SocialMentionRecord]:
        """Fetch X mentions for given cards from the last lookback_days.

        Note: Twitter API v2 recent search requires paid tier. This returns empty
        results in production. For Phase 1, use NewsAdapter instead.
        """
        # Twitter API v2 recent search requires paid tier ($100+/month)
        # For now, return empty list - NewsAdapter provides similar sentiment signals
        return []
