"""Data-type-specific freshness policies.

Replace universal freshness assumptions with policies tailored to each data type.
Different data sources have different decay rates and reliability profiles.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class DataType(Enum):
    """Types of data in the sports card system."""

    ACTIVE_LISTING = "active_listing"  # Current ask on marketplace
    AUCTION_LISTING = "auction_listing"  # Auction in progress
    SOLD_TRANSACTION = "sold_transaction"  # Completed sale (sold comp)
    POPULATION_DATA = "population_data"  # PSA population counts
    PLAYER_DATA = "player_data"  # Player info (static)
    MARKETPLACE_FEES = "marketplace_fees"  # Fee schedules
    GRADING_COST = "grading_cost"  # PSA/BGS/SGC grading fees
    NEWS_EVENT = "news_event"  # Player news, trades, etc.
    MARKET_SENTIMENT = "market_sentiment"  # Investor sentiment (if tracked)
    VALUATION_COMP = "valuation_comp"  # Fair value estimate from comps


@dataclass
class DataFreshnessPolicy:
    """Policy for when a data source is considered fresh/stale/critical."""

    data_type: DataType

    # === Thresholds ===
    max_age_hours: int  # Data older than this needs review
    warning_threshold_hours: int  # Start warning at this age
    critical_threshold_hours: int  # Data this old should block decisions

    # === Confidence Impact ===
    confidence_fresh: float = 1.0  # Confidence when data is fresh (0-1 hour old)
    confidence_warning: float = 0.7  # Confidence at warning threshold
    confidence_critical: float = 0.2  # Confidence at critical threshold
    confidence_stale: float = 0.0  # Confidence beyond max_age

    # === Validation ===
    requires_validation: bool = False  # Must be validated against other sources?
    can_be_cached: bool = True  # Can this be cached between requests?
    allows_estimates: bool = True  # Can estimates be used if live data unavailable?

    # === Notes ===
    notes: str = ""

    def get_age_hours(self, data_timestamp: datetime, as_of: Optional[datetime] = None) -> float:
        """Calculate data age in hours."""
        ref_time = as_of or datetime.now()
        return (ref_time - data_timestamp).total_seconds() / 3600.0

    def is_fresh(self, data_timestamp: datetime, as_of: Optional[datetime] = None) -> bool:
        """Is data fresh enough to use?"""
        age = self.get_age_hours(data_timestamp, as_of)
        return age < self.max_age_hours

    def is_warning(self, data_timestamp: datetime, as_of: Optional[datetime] = None) -> bool:
        """Is data in warning zone (old but usable)?"""
        age = self.get_age_hours(data_timestamp, as_of)
        return self.warning_threshold_hours <= age < self.max_age_hours

    def is_critical(self, data_timestamp: datetime, as_of: Optional[datetime] = None) -> bool:
        """Is data beyond critical threshold (should block)?"""
        age = self.get_age_hours(data_timestamp, as_of)
        return age >= self.critical_threshold_hours

    def get_confidence_multiplier(
        self, data_timestamp: datetime, as_of: Optional[datetime] = None
    ) -> float:
        """Get confidence multiplier based on data age."""
        age = self.get_age_hours(data_timestamp, as_of)

        if age <= 1.0:
            return self.confidence_fresh
        elif age < self.warning_threshold_hours:
            # Linear interpolation between fresh and warning
            pct = (age - 1.0) / (self.warning_threshold_hours - 1.0)
            return self.confidence_fresh - (self.confidence_fresh - self.confidence_warning) * pct
        elif age < self.critical_threshold_hours:
            # Linear interpolation between warning and critical
            pct = (age - self.warning_threshold_hours) / (
                self.critical_threshold_hours - self.warning_threshold_hours
            )
            return self.confidence_warning - (self.confidence_warning - self.confidence_critical) * pct
        else:
            return self.confidence_stale

    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"{self.data_type.value}: "
            f"Fresh <{self.warning_threshold_hours}h, "
            f"Warning {self.warning_threshold_hours}-{self.max_age_hours}h, "
            f"Critical >{self.critical_threshold_hours}h"
        )


# === Predefined Policies ===

ACTIVE_LISTING_POLICY = DataFreshnessPolicy(
    data_type=DataType.ACTIVE_LISTING,
    max_age_hours=2,
    warning_threshold_hours=1,
    critical_threshold_hours=4,
    confidence_fresh=1.0,
    confidence_warning=0.8,
    confidence_critical=0.3,
    confidence_stale=0.0,
    requires_validation=False,
    can_be_cached=False,
    allows_estimates=False,
    notes="Active prices change rapidly; need fresh data for buy decisions",
)

AUCTION_LISTING_POLICY = DataFreshnessPolicy(
    data_type=DataType.AUCTION_LISTING,
    max_age_hours=1,
    warning_threshold_hours=30,  # minutes
    critical_threshold_hours=2,
    confidence_fresh=1.0,
    confidence_warning=0.6,
    confidence_critical=0.1,
    confidence_stale=0.0,
    requires_validation=False,
    can_be_cached=False,
    allows_estimates=False,
    notes="Auction data is highly time-sensitive; bid amounts change by the minute",
)

SOLD_TRANSACTION_POLICY = DataFreshnessPolicy(
    data_type=DataType.SOLD_TRANSACTION,
    max_age_hours=720,  # 30 days
    warning_threshold_hours=240,  # 10 days
    critical_threshold_hours=1440,  # 60 days
    confidence_fresh=1.0,
    confidence_warning=0.9,
    confidence_critical=0.5,
    confidence_stale=0.2,
    requires_validation=False,
    can_be_cached=True,
    allows_estimates=True,
    notes="Sold comps decay slowly; seasonal variations matter",
)

POPULATION_DATA_POLICY = DataFreshnessPolicy(
    data_type=DataType.POPULATION_DATA,
    max_age_hours=2160,  # 90 days
    warning_threshold_hours=720,  # 30 days
    critical_threshold_hours=4320,  # 180 days
    confidence_fresh=1.0,
    confidence_warning=0.95,
    confidence_critical=0.7,
    confidence_stale=0.4,
    requires_validation=True,
    can_be_cached=True,
    allows_estimates=True,
    notes="PSA population data updates weekly; slow drift acceptable",
)

PLAYER_DATA_POLICY = DataFreshnessPolicy(
    data_type=DataType.PLAYER_DATA,
    max_age_hours=8760,  # 1 year
    warning_threshold_hours=2160,  # 90 days
    critical_threshold_hours=17520,  # 2 years
    confidence_fresh=1.0,
    confidence_warning=0.99,
    confidence_critical=0.8,
    confidence_stale=0.6,
    requires_validation=False,
    can_be_cached=True,
    allows_estimates=True,
    notes="Player info is mostly static; only update on major life events",
)

MARKETPLACE_FEES_POLICY = DataFreshnessPolicy(
    data_type=DataType.MARKETPLACE_FEES,
    max_age_hours=2160,  # 90 days
    warning_threshold_hours=720,  # 30 days
    critical_threshold_hours=4320,  # 180 days
    confidence_fresh=1.0,
    confidence_warning=0.98,
    confidence_critical=0.85,
    confidence_stale=0.7,
    requires_validation=True,
    can_be_cached=True,
    allows_estimates=False,
    notes="Fees change on schedule; track eBay/PWCC/Heritage announcements",
)

GRADING_COST_POLICY = DataFreshnessPolicy(
    data_type=DataType.GRADING_COST,
    max_age_hours=4320,  # 180 days
    warning_threshold_hours=2160,  # 90 days
    critical_threshold_hours=8760,  # 1 year
    confidence_fresh=1.0,
    confidence_warning=0.95,
    confidence_critical=0.80,
    confidence_stale=0.6,
    requires_validation=True,
    can_be_cached=True,
    allows_estimates=True,
    notes="Grading fees are relatively stable; update quarterly",
)

NEWS_EVENT_POLICY = DataFreshnessPolicy(
    data_type=DataType.NEWS_EVENT,
    max_age_hours=24,
    warning_threshold_hours=6,
    critical_threshold_hours=48,
    confidence_fresh=1.0,
    confidence_warning=0.7,
    confidence_critical=0.2,
    confidence_stale=0.0,
    requires_validation=True,
    can_be_cached=False,
    allows_estimates=False,
    notes="News impacts prices immediately; must verify from primary sources",
)


# === Registry ===

FRESHNESS_POLICIES = {
    DataType.ACTIVE_LISTING: ACTIVE_LISTING_POLICY,
    DataType.AUCTION_LISTING: AUCTION_LISTING_POLICY,
    DataType.SOLD_TRANSACTION: SOLD_TRANSACTION_POLICY,
    DataType.POPULATION_DATA: POPULATION_DATA_POLICY,
    DataType.PLAYER_DATA: PLAYER_DATA_POLICY,
    DataType.MARKETPLACE_FEES: MARKETPLACE_FEES_POLICY,
    DataType.GRADING_COST: GRADING_COST_POLICY,
    DataType.NEWS_EVENT: NEWS_EVENT_POLICY,
}


def get_policy(data_type: DataType) -> DataFreshnessPolicy:
    """Get freshness policy for a data type."""
    if data_type not in FRESHNESS_POLICIES:
        # Default conservative policy
        return DataFreshnessPolicy(
            data_type=data_type,
            max_age_hours=24,
            warning_threshold_hours=6,
            critical_threshold_hours=48,
            notes="Default policy (not type-specific)",
        )
    return FRESHNESS_POLICIES[data_type]
