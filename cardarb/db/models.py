from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Card:
    card_id: int
    player_name: str
    year: int
    set_name: str
    card_number: str | None
    variant: str | None
    sport: str
    grade: str


@dataclass(frozen=True)
class ListingRecord:
    card_id: int
    source: str
    listing_type: str  # "sold" | "active"
    price: float
    listed_at: datetime
    sold_at: datetime | None = None


@dataclass(frozen=True)
class SocialMentionRecord:
    card_id: int
    source: str  # "twitter" | "reddit"
    mention_count: int
    sentiment_score: float
    window_start: date
    window_end: date


@dataclass(frozen=True)
class PSAPopRecord:
    card_id: int
    grade: str
    population: int
    population_change_30d: int


@dataclass(frozen=True)
class NewsRecord:
    card_id: int
    headline: str
    sentiment_score: float
    published_at: datetime


@dataclass(frozen=True)
class ListingVelocityRecord:
    """Track listing activity over time."""
    card_id: int
    new_listings_today: int
    avg_listings_7day: float
    velocity_multiplier: float  # today / 7day avg (>1.0 = increasing, <1.0 = decreasing)
    velocity_signal: str  # "spike_up", "normal", "drying_up"
    as_of_date: date


@dataclass(frozen=True)
class EventRecord:
    """Sports events affecting player card value."""
    card_id: int
    event_type: str  # "injury", "trade", "milestone", "season_start", "playoff"
    severity: str | None = None  # For injuries: "OUT", "DAY_TO_DAY", "PROBABLE"
    detail: str | None = None  # Trade destination, milestone description
    impact: str = "NEUTRAL"  # "NEGATIVE", "NEUTRAL", "POSITIVE"
    confidence: float = 0.8  # 0.0-1.0, how confident are we about impact
    event_date: datetime | None = None
    detected_at: datetime | None = None


@dataclass(frozen=True)
class PSAPopulationDetail:
    """Detailed population breakdown by grade."""
    card_id: int
    total_population: int
    gem_mint_10: int = 0
    mint_9: int = 0
    near_mint_8: int = 0
    excellent_7: int = 0
    vg_6: int = 0
    good_or_lower: int = 0
    premium_pct: float = 0.0  # % at 9.0 or higher
    scarcity_index: float = 0.0  # 0-1.0, higher = scarcer at premium grades
    as_of_date: date = None
