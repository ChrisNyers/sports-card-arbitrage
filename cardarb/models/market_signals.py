"""Market signals: price momentum, inventory trends, catalysts, and negative information.

MarketSignals EXTRACTS and CLASSIFIES signals from market data.
Strategies INTERPRET these signals and make BUY/WATCH/PASS decisions.

This module is responsible for:
- Identifying price momentum (UP, DOWN, FLAT)
- Classifying inventory trends (RISING, STABLE, FALLING)
- Detecting catalysts and negative information
- Assessing signal confidence

This module is NOT responsible for:
- Making trading decisions
- Determining if an opportunity is "good" or "bad"
- Interpreting signals in context of strategy goals

Strategies will use signal classifications to adjust confidence multipliers
and make final BUY/WATCH/PASS decisions based on their logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class PriceMomentum:
    """Track price direction and trend."""

    current_price: float
    price_7_days_ago: Optional[float] = None
    price_30_days_ago: Optional[float] = None
    price_90_days_ago: Optional[float] = None

    # Calculated
    trend_7_day: str = ""  # "UP", "DOWN", "FLAT"
    trend_30_day: str = ""  # "UP", "DOWN", "FLAT"
    momentum_score: float = 0.0  # -1.0 (falling) to +1.0 (rising)

    def analyze(self) -> None:
        """Calculate momentum metrics."""
        if self.price_7_days_ago:
            change = (self.current_price - self.price_7_days_ago) / self.price_7_days_ago
            self.trend_7_day = "UP" if change > 0.02 else ("DOWN" if change < -0.02 else "FLAT")
            self.momentum_score = max(-1.0, min(1.0, change * 10))

        if self.price_30_days_ago:
            change = (self.current_price - self.price_30_days_ago) / self.price_30_days_ago
            self.trend_30_day = "UP" if change > 0.02 else ("DOWN" if change < -0.02 else "FLAT")

    def is_falling_knife(self) -> bool:
        """Is price actively falling? (value trap indicator)"""
        return self.trend_7_day == "DOWN" and self.trend_30_day == "DOWN"

    def is_stable(self) -> bool:
        """Is price stable? (safe for mean reversion)"""
        return self.trend_7_day in ["FLAT", "UP"] or self.trend_7_day is None


@dataclass
class InventoryTrend:
    """Track listing supply changes."""

    listings_today: int
    listings_7_days_ago: Optional[int] = None
    listings_30_days_ago: Optional[int] = None

    # Calculated
    trend: str = ""  # "RISING", "STABLE", "FALLING"
    change_pct: float = 0.0
    interpretation: str = ""  # "FORCED_SELLING", "NORMAL", "DEMAND_UP"

    def analyze(self) -> None:
        """Determine inventory trend."""
        if self.listings_7_days_ago:
            self.change_pct = (self.listings_today - self.listings_7_days_ago) / self.listings_7_days_ago

            if self.change_pct > 0.25:  # >25% increase
                self.trend = "RISING"
                self.interpretation = "FORCED_SELLING"
            elif self.change_pct < -0.25:  # >25% decrease
                self.trend = "FALLING"
                self.interpretation = "DEMAND_UP"
            else:
                self.trend = "STABLE"
                self.interpretation = "NORMAL"

    def is_danger_signal(self) -> bool:
        """Inventory buildup = danger signal (avoid)"""
        return self.trend == "RISING" and self.change_pct > 0.40


@dataclass
class Catalyst:
    """A specific event that could trigger price change."""

    catalyst_type: str  # "SEASON_CHANGE", "PLAYER_MILESTONE", "SET_ANNIVERSARY", "NEWS", "UNKNOWN"
    description: str
    days_until: int  # Estimate of when it happens
    confidence: float  # 0.0-1.0 how certain
    expected_impact: str  # "POSITIVE", "NEGATIVE", "NEUTRAL"

    def is_near_term(self) -> bool:
        """Is catalyst within 90 days?"""
        return 0 <= self.days_until <= 90

    def is_realistic(self) -> bool:
        """Is this a real catalyst or speculation?"""
        return self.confidence >= 0.7 and self.days_until >= 0


@dataclass
class CatalystList:
    """Collection of catalysts for a card."""

    catalysts: list[Catalyst] = field(default_factory=list)

    def has_near_term_catalyst(self) -> bool:
        """Is there a realistic catalyst within 90 days?"""
        return any(c.is_near_term() and c.is_realistic() for c in self.catalysts)

    def best_catalyst(self) -> Optional[Catalyst]:
        """Most confident nearest-term catalyst."""
        realistic = [c for c in self.catalysts if c.is_realistic()]
        if not realistic:
            return None
        return min(realistic, key=lambda c: c.days_until)

    def catalyst_summary(self) -> str:
        """Human-readable summary."""
        if not self.catalysts:
            return "No identified catalysts"
        if self.has_near_term_catalyst():
            best = self.best_catalyst()
            return f"{best.catalyst_type}: {best.description} ({best.days_until} days, {best.confidence:.0%} confidence)"
        return f"{len(self.catalysts)} catalysts identified (all >90 days out)"


@dataclass
class NegativeInformation:
    """Known issues that might explain the discount."""

    counterfeit_alert: bool = False
    counterfeit_alert_severity: str = ""  # "HIGH", "MEDIUM", "LOW"

    player_scandal: bool = False
    scandal_type: str = ""  # "BANNED", "RETIRED", "CONTROVERSY", etc.

    known_restoration: bool = False
    restoration_type: str = ""  # "COSMETIC", "STRUCTURAL", "PROFESSIONAL", etc.

    set_recall: bool = False
    recall_reason: str = ""

    grading_concern: bool = False
    grading_issue: str = ""  # "FAKE_CERT", "GRADE_INFLATION", "COMPANY_DELISTED", etc.

    other_issues: list[str] = field(default_factory=list)

    def has_serious_issues(self) -> bool:
        """Does this card have legitimate reasons for the discount?"""
        return (
            self.counterfeit_alert
            or self.player_scandal
            or self.set_recall
            or self.grading_concern
            or len(self.other_issues) > 0
        )

    def issue_summary(self) -> str:
        """Human-readable summary."""
        issues = []
        if self.counterfeit_alert:
            issues.append(f"⚠️ Counterfeit alert ({self.counterfeit_alert_severity})")
        if self.player_scandal:
            issues.append(f"⚠️ Player {self.scandal_type}")
        if self.known_restoration:
            issues.append(f"⚠️ Known {self.restoration_type} restoration")
        if self.set_recall:
            issues.append(f"⚠️ Set recall ({self.recall_reason})")
        if self.grading_concern:
            issues.append(f"⚠️ Grading issue ({self.grading_issue})")
        issues.extend([f"⚠️ {issue}" for issue in self.other_issues])

        return ", ".join(issues) if issues else "✅ No known issues"


@dataclass
class VolumeProfile:
    """Breakdown of sales by price level."""

    fair_value: float
    fair_value_band: tuple[float, float]  # e.g., ($95, $105)

    sales_at_fair_value: int  # Sales within band
    sales_below_fair_value: int  # Discount range
    sales_above_fair_value: int  # Premium range

    # Calculated
    volume_ratio: float = 0.0  # Fair value sales / discount sales

    def analyze(self) -> None:
        """Calculate volume metrics."""
        total_discount_sales = self.sales_below_fair_value if self.sales_below_fair_value > 0 else 1
        self.volume_ratio = self.sales_at_fair_value / total_discount_sales

    def confirms_discount(self) -> bool:
        """Do buyers actually purchase at fair value?"""
        # If 20%+ of sales at fair value, market accepts that price
        return self.volume_ratio >= 0.2

    def volume_summary(self) -> str:
        """Human-readable summary."""
        return (
            f"Sales: {self.sales_at_fair_value} @ fair value | "
            f"{self.sales_below_fair_value} @ discount | "
            f"{self.sales_above_fair_value} @ premium | "
            f"Ratio: {self.volume_ratio:.2f}"
        )


@dataclass
class MarketSignals:
    """Complete market signal analysis."""

    # Core signals
    price_momentum: Optional[PriceMomentum] = None
    inventory_trend: Optional[InventoryTrend] = None
    catalysts: Optional[CatalystList] = None
    negative_info: Optional[NegativeInformation] = None
    volume_profile: Optional[VolumeProfile] = None

    # Comp freshness
    comp_age_days: int = 0  # How old are comparables?
    comp_freshness_score: float = 1.0  # 0.0-1.0

    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.now)

    def calculate_freshness_score(self) -> float:
        """Freshness score for comps."""
        if self.comp_age_days < 7:
            return 1.0
        elif self.comp_age_days < 14:
            return 0.9
        elif self.comp_age_days < 30:
            return 0.75
        elif self.comp_age_days < 60:
            return 0.5
        else:
            return 0.25

    def classify_signals(self) -> bool:
        """Classify signals: Do key indicators pass basic checks?

        This is signal CLASSIFICATION, not a trading decision.
        Strategies interpret these classifications and decide.

        Returns:
            True if no major red flags detected in signals
            False if serious risks detected

        Note: Strategies may override this classification based on their logic.
        This is just a signal classification, not a final recommendation.
        """
        # Key signal checks (for classification only)
        checks = [
            self.price_momentum is None or not self.price_momentum.is_falling_knife(),
            self.inventory_trend is None or not self.inventory_trend.is_danger_signal(),
            self.catalysts is None or self.catalysts.has_near_term_catalyst(),
            self.negative_info is None or not self.negative_info.has_serious_issues(),
            self.comp_freshness_score >= 0.6,
            self.volume_profile is None or self.volume_profile.confirms_discount(),
        ]

        return all(checks)

    def is_safe_opportunity(self) -> bool:
        """Deprecated: use classify_signals() instead.

        This method name was misleading - it suggested trading logic.
        Use classify_signals() to extract signal classifications.
        Strategies make the final decision based on these signals.
        """
        return self.classify_signals()

    def risk_summary(self) -> str:
        """Human-readable risk assessment of SIGNALS.

        This describes risks detected in market signals, NOT trading recommendations.
        Strategies interpret these signal risks and make final decisions.
        """
        risks = []

        if self.price_momentum and self.price_momentum.is_falling_knife():
            risks.append("🔴 FALLING KNIFE - Price actively declining")

        if self.inventory_trend and self.inventory_trend.is_danger_signal():
            risks.append(f"🔴 INVENTORY DUMP - Supply up {self.inventory_trend.change_pct:.0%}")

        if self.catalysts and not self.catalysts.has_near_term_catalyst():
            risks.append("🟡 NO CATALYST - What triggers recovery?")

        if self.negative_info and self.negative_info.has_serious_issues():
            risks.append(f"🔴 NEGATIVE INFO - {self.negative_info.issue_summary()}")

        if self.comp_freshness_score < 0.6:
            risks.append(f"🟡 STALE COMPS - {self.comp_age_days} days old")

        if self.volume_profile and not self.volume_profile.confirms_discount():
            risks.append("🟡 NO VOLUME - Few buyers at fair value")

        return "\n".join(risks) if risks else "✅ No major risks detected"
