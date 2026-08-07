"""Event detection for sports cards. Identifies key events affecting player value."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import re

from cardarb.db.models import EventRecord, NewsRecord
from cardarb.sources.mock_data.card_catalog import get_cards


class EventDetector:
    """Detect key events from news headlines and context."""

    # Event classification rules: (keyword_pattern, event_type, impact, severity)
    EVENT_RULES = [
        # Injuries (NEGATIVE)
        (r"\b(out|ruled out|injured|injury|shoulder|knee|hamstring|ligament|torn)\b", "injury", "NEGATIVE", "OUT"),
        (r"\bday-to-day\b", "injury", "NEGATIVE", "DAY_TO_DAY"),
        (r"\b(probable|questionable)\b", "injury", "NEGATIVE", "PROBABLE"),
        (r"\breturn|back\b", "injury", "POSITIVE", "RETURNING"),

        # Trades & Free Agency (MIXED)
        (r"\b(traded|trade|signs with|free agent|signs|joins)\b", "trade", "POSITIVE", None),
        (r"\bcontract (extension|renewal)\b", "contract", "POSITIVE", None),

        # Milestones & Records (POSITIVE)
        (r"\bmilestone|record|career-high|career high|100(th|st|nd|rd)\b", "milestone", "POSITIVE", None),
        (r"\b(\d{3,4})th (assist|rebound|point|hit|home run|strikeout)\b", "milestone", "POSITIVE", None),

        # Performance (POSITIVE/NEGATIVE)
        (r"\b(all-star|all star|mvp|award|champion)\b", "performance", "POSITIVE", None),
        (r"\b(benched|demoted|decline|decline|slump|struggles)\b", "performance", "NEGATIVE", None),

        # Season Events
        (r"\b(season ends|final game|playoff\b|playoff-bound|postseason)\b", "season", "POSITIVE", None),
        (r"\b(draft|draft (pick|selected))\b", "draft", "POSITIVE", None),
    ]

    @classmethod
    def detect_from_news(cls, news_records: list[NewsRecord], as_of_date: date) -> list[EventRecord]:
        """Extract events from news articles.

        Args:
            news_records: List of NewsRecords with headlines
            as_of_date: Date for context

        Returns:
            List of EventRecords with detected events
        """
        from cardarb.sentiment import SentimentEncoder

        events: list[EventRecord] = []

        for news in news_records:
            # Check headline against event rules
            headline_lower = news.headline.lower()

            for pattern, event_type, impact, severity in cls.EVENT_RULES:
                if re.search(pattern, headline_lower):
                    # Use advanced sentiment encoding for confidence
                    sentiment_result = SentimentEncoder.score_text(news.headline)
                    confidence = sentiment_result.confidence

                    event = EventRecord(
                        card_id=news.card_id,
                        event_type=event_type,
                        severity=severity,
                        detail=news.headline[:100],
                        impact=impact,
                        confidence=confidence,
                        event_date=news.published_at,
                        detected_at=datetime.now(),
                    )
                    events.append(event)
                    break  # Only one event per headline

        return events


class MockEventAdapter:
    """Mock event detector for testing."""

    def __init__(self) -> None:
        self._cards_by_id = {c.card_id: c for c in get_cards()}

    def fetch_events(self, card_ids: list[int], as_of_date: date, lookback_days: int = 7) -> list[EventRecord]:
        """Generate synthetic events for testing."""
        events: list[EventRecord] = []

        for card_id in card_ids[:5]:  # Generate events for first 5 cards only
            # Random event examples
            event_type = ["injury", "trade", "milestone", "performance"][card_id % 4]
            impact = ["POSITIVE", "NEGATIVE", "NEUTRAL"][card_id % 3]

            event = EventRecord(
                card_id=card_id,
                event_type=event_type,
                severity="OUT" if event_type == "injury" else None,
                detail=f"Mock {event_type} for card {card_id}",
                impact=impact,
                confidence=0.75,
                event_date=datetime.now(),
                detected_at=datetime.now(),
            )
            events.append(event)

        return events


class EventAdapter:
    """Real event detection adapter. Parses news for key events."""

    def __init__(self) -> None:
        self._detector = EventDetector()
        self._cards_by_id = {c.card_id: c for c in get_cards()}

    def fetch_events(self, news_records: list[NewsRecord], as_of_date: date) -> list[EventRecord]:
        """Fetch/detect events from news articles.

        Args:
            news_records: News articles to analyze
            as_of_date: Reference date

        Returns:
            List of detected events with impact scoring
        """
        events = self._detector.detect_from_news(news_records, as_of_date)

        if events:
            print(f"[Events] Detected {len(events)} events")

        return events
