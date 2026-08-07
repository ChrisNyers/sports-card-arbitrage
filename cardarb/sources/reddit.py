from __future__ import annotations

from datetime import date

from cardarb.db.models import SocialMentionRecord
from cardarb.sources.base import SocialSource
from cardarb.sources.mock_data import generators
from cardarb.sources.mock_data.card_catalog import get_cards


class MockRedditAdapter(SocialSource):
    def __init__(self) -> None:
        self._cards_by_id = {c.card_id: c for c in get_cards()}

    def fetch_mentions(
        self, card_ids: list[int], as_of_date: date, lookback_days: int = 7
    ) -> list[SocialMentionRecord]:
        records: list[SocialMentionRecord] = []
        for card_id in card_ids:
            card = self._cards_by_id[card_id]
            all_records = generators.generate_social_mentions(card, as_of_date, lookback_days)
            records.extend(r for r in all_records if r.source == "reddit")
        return records


class RedditAdapter(SocialSource):
    """Real Reddit API adapter. Requires REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET.

    Not implemented yet. When real API access is available, implement
    fetch_mentions() using PRAW against r/sportscards, r/baseballcards, etc.,
    aggregating mention_count and sentiment per window.
    """

    def fetch_mentions(
        self, card_ids: list[int], as_of_date: date, lookback_days: int = 7
    ) -> list[SocialMentionRecord]:
        raise NotImplementedError(
            "Real Reddit API integration is not implemented yet. "
            "Set REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET only once fetch_mentions() is implemented."
        )
