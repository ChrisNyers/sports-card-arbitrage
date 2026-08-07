"""Data provenance wrapper for all market data.

Every price, population, listing, or market data point must include:
- The actual value
- Where it came from (source)
- When it was collected
- How fresh it is
- How reliable it is

This allows us to track data quality and make decisions based on freshness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class DataSource(str, Enum):
    """Enumeration of known data sources."""

    EBAY = "ebay"
    PWCC = "pwcc"
    PSA = "psa"
    BGS = "bgs"
    AUCTION = "auction"
    NEWS_API = "news_api"
    TWITTER = "twitter"
    REDDIT = "reddit"
    INTERNAL_CACHE = "internal_cache"
    MANUAL_INPUT = "manual_input"
    UNKNOWN = "unknown"


@dataclass
class DataRecord:
    """Wrapper around a market data point with provenance and freshness info."""

    value: Any  # The actual data (price, population count, etc.)
    source: str  # Where it came from
    data_type: str  # "price", "population", "listing", "news", etc.
    source_url: Optional[str] = None  # URL for verification (if applicable)

    # Timing information
    collection_timestamp: datetime = field(default_factory=datetime.now)
    data_age_minutes: int = 0  # How old is the underlying data?

    # Quality indicators
    confidence: float = 1.0  # 0.0-1.0, how reliable is this source?
    notes: Optional[str] = None  # Special context

    # Optional: related data
    context: dict = field(default_factory=dict)  # Additional context (fees, etc.)

    def recency_score(self) -> float:
        """Score from 0.0 to 1.0 representing how fresh this data is.

        1.0 = <1 hour old
        0.9 = 1-6 hours old
        0.7 = 6-24 hours old
        0.5 = 24-72 hours old
        0.2 = >72 hours old
        """
        if self.data_age_minutes < 60:
            return 1.0
        elif self.data_age_minutes < 360:  # 6 hours
            return 0.9
        elif self.data_age_minutes < 1440:  # 24 hours
            return 0.7
        elif self.data_age_minutes < 4320:  # 72 hours
            return 0.5
        else:
            return 0.2

    def age_description(self) -> str:
        """Human-readable age description."""
        minutes = self.data_age_minutes

        if minutes < 1:
            return "Just now"
        elif minutes < 60:
            return f"{minutes}m ago"
        elif minutes < 1440:
            hours = minutes // 60
            return f"{hours}h ago"
        elif minutes < 10080:  # 7 days
            days = minutes // 1440
            return f"{days}d ago"
        else:
            weeks = minutes // 10080
            return f"{weeks}w ago"

    def weighted_value(self) -> float:
        """Return the value, potentially adjusted by confidence and recency.

        Useful for averaging multiple data points from different sources.
        """
        if not isinstance(self.value, (int, float)):
            return 0.0

        return self.value * self.confidence * self.recency_score()

    def is_current(self, max_age_hours: int = 24) -> bool:
        """Check if this data is fresh enough to use.

        Args:
            max_age_hours: Maximum acceptable age in hours

        Returns:
            True if data is within acceptable age threshold
        """
        return self.data_age_minutes <= max_age_hours * 60

    def is_usable(self, max_age_hours: int = 24, min_confidence: float = 0.7) -> bool:
        """Determine if this data point is usable for decision-making.

        Args:
            max_age_hours: Maximum age for data to be considered current
            min_confidence: Minimum confidence level
        """
        if not self.is_current(max_age_hours):
            return False
        if self.confidence < min_confidence:
            return False
        return True

    def validation_summary(self) -> dict:
        """Return summary of data quality for logging."""
        return {
            "value": self.value,
            "source": self.source,
            "age": self.age_description(),
            "freshness_score": round(self.recency_score(), 2),
            "confidence": self.confidence,
            "is_usable": self.is_usable(),
        }

    @staticmethod
    def price_record(
        value: float,
        source: str,
        source_url: Optional[str] = None,
        sale_type: Optional[str] = None,
        seller_rating: Optional[float] = None,
        data_age_minutes: int = 0,
        confidence: float = 0.95,
        notes: Optional[str] = None,
    ) -> DataRecord:
        """Create a price data record."""
        return DataRecord(
            value=value,
            source=source,
            data_type="price",
            source_url=source_url,
            data_age_minutes=data_age_minutes,
            confidence=confidence,
            notes=notes,
            context={
                "sale_type": sale_type,  # "auction", "fixed-price", "buy-it-now"
                "seller_rating": seller_rating,  # 0-5 stars
            },
        )

    @staticmethod
    def listing_record(
        price: float,
        source: str,
        source_url: str,
        seller_id: str,
        quantity: int = 1,
        days_listed: int = 0,
        data_age_minutes: int = 0,
        confidence: float = 0.98,
        notes: Optional[str] = None,
    ) -> DataRecord:
        """Create an active listing data record."""
        return DataRecord(
            value=price,
            source=source,
            data_type="listing",
            source_url=source_url,
            data_age_minutes=data_age_minutes,
            confidence=confidence,
            notes=notes,
            context={
                "seller_id": seller_id,
                "quantity": quantity,
                "days_listed": days_listed,
            },
        )

    @staticmethod
    def population_record(
        population: int,
        source: str,
        grade_distribution: Optional[dict] = None,
        data_age_minutes: int = 0,
        confidence: float = 0.85,
        notes: Optional[str] = None,
    ) -> DataRecord:
        """Create a population/scarcity data record."""
        return DataRecord(
            value=population,
            source=source,
            data_type="population",
            data_age_minutes=data_age_minutes,
            confidence=confidence,
            notes=notes,
            context={
                "grade_distribution": grade_distribution or {},
            },
        )

    @staticmethod
    def news_record(
        sentiment_score: float,
        source: str,
        source_url: str,
        headline: str,
        event_type: str,
        data_age_minutes: int = 0,
        confidence: float = 0.80,
        notes: Optional[str] = None,
    ) -> DataRecord:
        """Create a news/sentiment data record."""
        return DataRecord(
            value=sentiment_score,
            source=source,
            data_type="news",
            source_url=source_url,
            data_age_minutes=data_age_minutes,
            confidence=confidence,
            notes=notes,
            context={
                "headline": headline,
                "event_type": event_type,
            },
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "value": self.value,
            "source": self.source,
            "data_type": self.data_type,
            "source_url": self.source_url,
            "collection_timestamp": self.collection_timestamp.isoformat(),
            "data_age_minutes": self.data_age_minutes,
            "confidence": self.confidence,
            "is_current": self.is_current,
            "notes": self.notes,
            "context": self.context,
        }

    @staticmethod
    def from_dict(data: dict) -> DataRecord:
        """Create DataRecord from dictionary."""
        if isinstance(data.get("collection_timestamp"), str):
            data["collection_timestamp"] = datetime.fromisoformat(data["collection_timestamp"])
        return DataRecord(**data)


@dataclass
class DataSnapshot:
    """Immutable snapshot of all data for a recommendation at a point in time."""

    card_id: str
    snapshot_timestamp: datetime = field(default_factory=datetime.now)

    # All data used for this recommendation
    sold_prices: list[DataRecord] = field(default_factory=list)  # Historical sales
    active_listings: list[DataRecord] = field(default_factory=list)  # Current asks
    population: Optional[DataRecord] = None  # Population/scarcity
    news_sentiment: list[DataRecord] = field(default_factory=list)  # Recent news
    liquidity_signals: dict = field(default_factory=dict)  # Listing velocity, etc.

    def data_freshness_report(self) -> dict:
        """Check freshness of all data sources in this snapshot."""
        report = {
            "snapshot_time": self.snapshot_timestamp.isoformat(),
            "data_by_type": {},
        }

        all_records = (
            self.sold_prices
            + self.active_listings
            + self.news_sentiment
            + ([self.population] if self.population else [])
        )

        for record in all_records:
            data_type = record.data_type
            if data_type not in report["data_by_type"]:
                report["data_by_type"][data_type] = {
                    "count": 0,
                    "sources": [],
                    "age_range": {"min": float("inf"), "max": 0},
                    "avg_confidence": 0.0,
                }

            info = report["data_by_type"][data_type]
            info["count"] += 1
            if record.source not in info["sources"]:
                info["sources"].append(record.source)
            info["age_range"]["min"] = min(info["age_range"]["min"], record.data_age_minutes)
            info["age_range"]["max"] = max(info["age_range"]["max"], record.data_age_minutes)
            info["avg_confidence"] = (
                info["avg_confidence"] * (info["count"] - 1) + record.confidence
            ) / info["count"]

        # Check if all critical data is current
        report["critical_data_current"] = True
        if not self.sold_prices:
            report["critical_data_current"] = False
            report["missing"] = "sold_prices"

        return report

    def can_recommend(self) -> tuple[bool, str]:
        """Determine if we have fresh enough data to make a recommendation."""
        if not self.sold_prices:
            return False, "No sold comparable data available"

        # Check age of sold prices (need data from last 30 days)
        for record in self.sold_prices:
            if not record.is_current(max_age_hours=30 * 24):
                oldest_sold = max(r.data_age_minutes for r in self.sold_prices)
                return False, f"Sold data older than 30 days (oldest: {oldest_sold} minutes)"

        if not self.active_listings:
            return False, "No active listings to establish current price"

        # Check age of active listings (need data from last 24 hours)
        for record in self.active_listings:
            if not record.is_current(max_age_hours=24):
                oldest_listing = max(r.data_age_minutes for r in self.active_listings)
                return False, f"Listing data older than 24 hours (oldest: {oldest_listing} minutes)"

        # Population data helpful but not critical
        if self.population and not self.population.is_current(max_age_hours=7 * 24):
            return False, "Population data older than 7 days (helpful for scarcity but optional)"

        return True, "All critical data current"


if __name__ == "__main__":
    # Example usage
    price_record = DataRecord.price_record(
        value=145.00,
        source="eBay (sold listing)",
        source_url="https://ebay.com/itm/...",
        sale_type="fixed-price",
        seller_rating=4.9,
        data_age_minutes=4,
        confidence=0.98,
        notes="No buyer returns, clean transaction",
    )

    listing_record = DataRecord.listing_record(
        price=150.00,
        source="eBay (active)",
        source_url="https://ebay.com/itm/...",
        seller_id="seller123",
        quantity=1,
        days_listed=3,
        data_age_minutes=2,
        confidence=0.99,
        notes="BIN price, free shipping",
    )

    population_record = DataRecord.population_record(
        population=342,
        source="PSA Set Registry",
        grade_distribution={"10": 3, "9": 41, "8": 85, "7": 120, "6": 65, "lower": 28},
        data_age_minutes=1440,  # 1 day old
        confidence=0.85,
        notes="Population may have changed slightly",
    )

    # Test records
    print("Price Record:")
    print(f"  Value: ${price_record.value}")
    print(f"  Age: {price_record.age_description()}")
    print(f"  Freshness: {price_record.recency_score():.0%}")
    print(f"  Usable: {price_record.is_usable()}")

    print("\nListing Record:")
    print(f"  Value: ${listing_record.value}")
    print(f"  Age: {listing_record.age_description()}")
    print(f"  Freshness: {listing_record.recency_score():.0%}")
    print(f"  Usable: {listing_record.is_usable()}")

    print("\nPopulation Record:")
    print(f"  Value: {population_record.value} total population")
    print(f"  Age: {population_record.age_description()}")
    print(f"  Freshness: {population_record.recency_score():.0%}")
    print(f"  Usable (7-day max): {population_record.is_usable(max_age_hours=168)}")

    # Test snapshot
    snapshot = DataSnapshot(
        card_id="mahomes-2020-prizm-rc-psa9",
        sold_prices=[price_record],
        active_listings=[listing_record],
        population=population_record,
    )

    can_rec, reason = snapshot.can_recommend()
    print(f"\nSnapshot Recommendation Check: {can_rec} ({reason})")
    print(f"Freshness Report:\n{snapshot.data_freshness_report()}")
