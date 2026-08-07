from __future__ import annotations

from datetime import date

from cardarb.db.models import NewsRecord
from cardarb.sources.base import NewsSource
from cardarb.sources.mock_data import generators
from cardarb.sources.mock_data.card_catalog import get_cards


class MockNewsAdapter(NewsSource):
    def __init__(self) -> None:
        self._cards_by_id = {c.card_id: c for c in get_cards()}

    def fetch_news(self, card_ids: list[int], as_of_date: date, lookback_days: int = 7) -> list[NewsRecord]:
        news: list[NewsRecord] = []
        for card_id in card_ids:
            card = self._cards_by_id[card_id]
            news.extend(generators.generate_news(card, as_of_date, lookback_days))
        return news


class NewsAdapter(NewsSource):
    """Real news API adapter using NewsAPI.org. Requires NEWS_API_KEY.

    Fetches sports news and headlines related to specific players/cards,
    extracting sentiment from article descriptions.
    """

    def __init__(self) -> None:
        import os
        self._api_key = os.getenv("NEWS_API_KEY")
        self._cards_by_id = {c.card_id: c for c in get_cards()}
        if not self._api_key:
            raise ValueError("NEWS_API_KEY not set")

    def fetch_news(self, card_ids: list[int], as_of_date: date, lookback_days: int = 7) -> list[NewsRecord]:
        """Fetch news articles related to given cards.

        Uses file-based cache to minimize API calls:
        - Caches results per card for 24 hours
        - Only fetches from API if cache is missing or expired
        - Adds throttling (500ms) between API calls to spread requests
        """
        import requests
        import time
        from datetime import timedelta, datetime
        from cardarb.cache import NewsCache

        records: list[NewsRecord] = []
        start_date = as_of_date - timedelta(days=lookback_days)
        url = "https://newsapi.org/v2/everything"

        api_calls = 0  # Track actual API calls
        cache_hits = 0  # Track cache hits

        for card_id in card_ids:
            if card_id not in self._cards_by_id:
                continue
            card = self._cards_by_id[card_id]

            # Try cache first
            cached_articles = NewsCache.get(card_id)
            if cached_articles is not None:
                # Use cached results (no API call)
                cache_hits += 1
                articles = cached_articles
            else:
                # Cache miss - fetch from API
                query = f'"{card.player_name}" sports'

                try:
                    params = {
                        "q": query,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "apiKey": self._api_key,
                        "pageSize": 50,
                    }
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()

                    data = response.json()
                    articles = data.get("articles", [])

                    # Cache the results for next time
                    NewsCache.set(card_id, articles)
                    api_calls += 1

                    # Throttle: wait 500ms between API calls to spread requests
                    time.sleep(0.5)

                except requests.exceptions.RequestException as e:
                    print(f"News API error for card {card_id}: {e}")
                    continue

            # Process articles into records
            for article in articles:
                pub_date_str = article.get("publishedAt", "")
                if not pub_date_str:
                    continue

                try:
                    published_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue

                # Advanced sentiment scoring: severity-weighted, context-aware
                headline = article.get("title", "")
                description = article.get("description") or ""

                from cardarb.sentiment import SentimentEncoder
                sentiment_result = SentimentEncoder.score_text(headline, description)

                records.append(NewsRecord(
                    card_id=card_id,
                    headline=headline,
                    sentiment_score=sentiment_result.overall_score,
                    published_at=published_at,
                ))

        if cache_hits > 0 or api_calls > 0:
            print(f"[Cache] News API: {cache_hits} from cache, {api_calls} new API calls (out of {len(card_ids)} cards)")

        return records
