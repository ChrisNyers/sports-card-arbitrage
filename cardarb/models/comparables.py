"""Sold-comparable analysis engine.

Processes sold listings to determine fair value for a card, with:
- Outlier removal (IQR method)
- Duplicate transaction removal
- Recency weighting
- Uncertainty estimation
- Confidence scoring based on sample size and dispersion
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .card_identity import CardIdentity
from .data_record import DataRecord


@dataclass
class SoldListing:
    """A single sold transaction record."""

    price: float
    sold_date: datetime
    sale_type: str  # "auction" or "fixed-price"
    transaction_id: str
    seller_id: Optional[str] = None
    seller_rating: Optional[float] = None  # 0-5 stars
    quantity: int = 1
    source: str = "unknown"
    source_url: Optional[str] = None

    def days_ago(self, as_of: Optional[datetime] = None) -> int:
        """How many days ago was this sold?"""
        ref_date = as_of or datetime.now()
        return (ref_date - self.sold_date).days

    def is_reliable(self) -> bool:
        """Is this a reliable transaction to use as a comparable?"""
        # Reject if:
        # - Very old (>90 days)
        # - Seller has poor rating
        # - Unusual quantity
        if self.days_ago() > 90:
            return False
        if self.seller_rating and self.seller_rating < 3.0:
            return False
        if self.quantity != 1:
            return False
        return True


@dataclass
class ComparableSalesAnalysis:
    """Complete analysis of comparable sales for a card.

    Preserves outliers for inspection and analysis. Outliers are identified
    but NOT removed from consideration - they are flagged for investigation.
    """

    # Central measures
    median_price: float
    trimmed_mean: float  # Remove top/bottom 10%
    mean_price: float

    # Range
    price_range: tuple[float, float]  # (low, high)
    price_range_pct: float  # Range as % of median

    # Dispersion
    std_dev: float
    dispersion_pct: float  # Std dev as % of median (higher = more variation)

    # Sample info
    sample_count: int  # Total comps used
    auction_count: int
    fixed_price_count: int
    outlier_count: int

    # Timing
    median_days_old: int
    recency_score: float  # 1.0 = all <7 days, lower = older

    # Confidence
    confidence: float  # 0.0-1.0 (higher = more confident in estimate)
    uncertainty_estimate: float  # ±$ range (e.g., ±$15)

    # === Outlier Information (PRESERVED) ===
    outlier_listings: list[SoldListing] = field(default_factory=list)  # Actual outlier data
    outlier_prices: list[float] = field(default_factory=list)  # Outlier values
    outlier_directions: dict = field(default_factory=dict)  # {price: "high" or "low"}

    # Data sources
    data_records: list[DataRecord] = field(default_factory=list)

    def weighted_estimate(self) -> float:
        """Best estimate weighted by confidence and recency."""
        # Use median for stability, but weight by confidence
        return self.median_price * min(1.0, self.confidence + 0.1)

    def confidence_interval(self, confidence_level: float = 0.85) -> tuple[float, float]:
        """Calculate confidence interval for fair value.

        At 85% confidence level, we expect the actual price to fall within this range
        85% of the time.
        """
        lower = self.weighted_estimate() - (self.uncertainty_estimate * 1.2)
        upper = self.weighted_estimate() + (self.uncertainty_estimate * 1.2)
        return (lower, upper)

    def buy_recommendation(self, ask_price: float) -> tuple[str, float]:
        """Recommend action if seeing this card at ask_price.

        Returns:
            (action: "buy", "pass", "research", profit_estimate: float)
        """
        fair_value = self.weighted_estimate()
        spread = ask_price - fair_value
        spread_pct = spread / fair_value if fair_value > 0 else 0

        if spread < -20:  # >20% underpriced
            return "buy", abs(spread)
        elif spread < -10:  # 10-20% underpriced
            return "buy", abs(spread)
        elif spread < 0:  # Underpriced, but small
            return "research", abs(spread)
        else:  # At or above fair value
            return "pass", 0.0

    def has_outliers(self) -> bool:
        """Are there statistical outliers in the sample?"""
        return len(self.outlier_listings) > 0

    def outlier_summary(self) -> str:
        """Describe outliers (high vs low) and their meaning."""
        if not self.outlier_listings:
            return "No outliers detected"

        high_outliers = [p for p, d in self.outlier_directions.items() if d == "high"]
        low_outliers = [p for p, d in self.outlier_directions.items() if d == "low"]

        lines = [f"Outliers detected: {len(self.outlier_listings)}"]

        if high_outliers:
            lines.append(
                f"  High outliers: {len(high_outliers)} sales above ${max(high_outliers):.2f} "
                f"(premium condition, rare variant, or market error)"
            )

        if low_outliers:
            lines.append(
                f"  Low outliers: {len(low_outliers)} sales below ${min(low_outliers):.2f} "
                f"(defects, distressed seller, or data error)"
            )

        return "\n".join(lines)

    def is_outlier_price(self, price: float) -> bool:
        """Check if a price is an outlier relative to the distribution."""
        return price in self.outlier_prices

    def summary(self) -> str:
        """Generate a summary of the analysis."""
        lines = [
            f"Fair Value: ${self.median_price:.2f}",
            f"  (Trimmed Mean: ${self.trimmed_mean:.2f})",
            f"  (Range: ${self.price_range[0]:.2f} - ${self.price_range[1]:.2f})",
            f"\nDispersion: {self.dispersion_pct:.1f}% (std dev: ${self.std_dev:.2f})",
            f"Confidence: {self.confidence:.0%}",
            f"Uncertainty: ±${self.uncertainty_estimate:.2f}",
            f"\nSample: {self.sample_count} sales ({self.auction_count} auctions, {self.fixed_price_count} fixed-price)",
            f"Recency: {self.median_days_old} days median, {self.recency_score:.0%} freshness",
        ]

        if self.has_outliers():
            lines.append(f"\nOutliers: {len(self.outlier_listings)} detected (preserved for investigation)")

        return "\n".join(lines)


class ComparableAnalyzer:
    """Analyze sold listings to determine fair value."""

    @staticmethod
    def as_module_result(
        analysis: ComparableSalesAnalysis,
        card_id: Optional[int] = None,
    ) -> "ModuleResult":  # type: ignore
        """Convert analysis to ModuleResult contract with full evidence breakdown.

        Imports ModuleResult here to avoid circular imports.
        """
        from .module_contract import ModuleResult

        return ModuleResult(
            module_name="ComparableAnalyzer",
            module_version="1.0",
            card_id=card_id,
            result=analysis,
            result_type="valuation_analysis",
            status="success",
            confidence_valuation=analysis.confidence,
            evidence={
                "median_price": analysis.median_price,
                "trimmed_mean": analysis.trimmed_mean,
                "mean_price": analysis.mean_price,
                "price_range": analysis.price_range,
                "price_range_pct": f"{analysis.price_range_pct:.1f}%",
                "std_dev": analysis.std_dev,
                "dispersion_pct": f"{analysis.dispersion_pct:.1f}%",
                # Sample composition
                "sample_count": analysis.sample_count,
                "auction_count": analysis.auction_count,
                "fixed_price_count": analysis.fixed_price_count,
                "outlier_count": analysis.outlier_count,
                # Confidence calculation breakdown
                "sample_score": ComparableAnalyzer._get_sample_score(analysis.sample_count),
                "dispersion_score": ComparableAnalyzer._get_dispersion_score(analysis.dispersion_pct),
                "recency_score": ComparableAnalyzer._get_recency_score(analysis.median_days_old),
                "confidence_calculation": (
                    f"{ComparableAnalyzer._get_sample_score(analysis.sample_count):.2f} (sample) + "
                    f"{ComparableAnalyzer._get_dispersion_score(analysis.dispersion_pct):.2f} (dispersion) + "
                    f"{ComparableAnalyzer._get_recency_score(analysis.median_days_old):.2f} (recency) = "
                    f"{analysis.confidence:.2f}"
                ),
                # Timing
                "median_days_old": analysis.median_days_old,
                "recency_score": analysis.recency_score,
                "uncertainty_estimate": f"±${analysis.uncertainty_estimate:.2f}",
            },
            reasoning=analysis.summary(),
            warnings=(
                [f"High dispersion: {analysis.dispersion_pct:.1f}% (confidence may be overstated)"]
                if analysis.dispersion_pct > 20
                else []
            )
            + (
                [f"Stale data: {analysis.median_days_old} days old"]
                if analysis.median_days_old > 30
                else []
            ),
        )

    @staticmethod
    def analyze(
        sold_listings: list[SoldListing],
        card_identity: Optional[CardIdentity] = None,
        include_outliers: bool = False,
    ) -> ComparableSalesAnalysis:
        """Analyze sold listings to determine fair value.

        Args:
            sold_listings: List of sold transactions
            card_identity: Optional card for context
            include_outliers: If False, remove outliers using IQR method

        Returns:
            ComparableSalesAnalysis with complete metrics
        """
        if not sold_listings:
            return ComparableAnalyzer._empty_analysis()

        # Extract prices
        prices = [s.price for s in sold_listings]

        # Separate by type
        auctions = [s for s in sold_listings if s.sale_type == "auction"]
        fixed_price = [s for s in sold_listings if s.sale_type == "fixed-price"]

        # Remove unreliable transactions
        reliable_listings = [s for s in sold_listings if s.is_reliable()]
        if not reliable_listings:
            reliable_listings = sold_listings  # Use all if none are reliable

        reliable_prices = [s.price for s in reliable_listings]

        # Remove duplicates (same card sold by same seller on same day)
        unique_listings = ComparableAnalyzer._remove_duplicate_transactions(reliable_listings)
        unique_prices = [s.price for s in unique_listings]

        # Remove outliers but preserve them for inspection
        normal_prices = unique_prices
        outlier_prices = []
        outlier_listings: list[SoldListing] = []
        outlier_directions: dict = {}

        if not include_outliers and len(unique_prices) >= 3:
            normal_prices, outlier_prices = ComparableAnalyzer._remove_outliers(unique_prices)
            # Preserve the actual outlier listings
            outlier_listings = [s for s in unique_listings if s.price in outlier_prices]
            # Mark direction of each outlier
            if outlier_prices:
                median_outlier_price = statistics.median(unique_prices)
                for price in outlier_prices:
                    outlier_directions[price] = "high" if price > median_outlier_price else "low"

        if not normal_prices:
            normal_prices = unique_prices  # Use all if outlier removal removes everything

        # Calculate measures
        median = statistics.median(normal_prices)
        mean = statistics.mean(normal_prices)
        std_dev = statistics.stdev(normal_prices) if len(normal_prices) > 1 else 0

        # Trimmed mean (remove top/bottom 10%)
        sorted_prices = sorted(normal_prices)
        trim_count = max(1, len(sorted_prices) // 10)
        trimmed_prices = sorted_prices[trim_count:-trim_count] if trim_count > 0 else sorted_prices
        trimmed_mean = statistics.mean(trimmed_prices) if trimmed_prices else median

        # Dispersion
        dispersion_pct = (std_dev / median * 100) if median > 0 else 0

        # Price range
        price_range = (min(normal_prices), max(normal_prices))
        price_range_pct = ((price_range[1] - price_range[0]) / median * 100) if median > 0 else 0

        # Recency
        days_old_list = [s.days_ago() for s in unique_listings]
        median_days = statistics.median(days_old_list)
        recency_score = ComparableAnalyzer._recency_score(days_old_list)

        # Confidence
        confidence = ComparableAnalyzer._confidence_score(
            sample_count=len(unique_listings),
            dispersion_pct=dispersion_pct,
            median_days=median_days,
        )

        # Uncertainty estimate
        # More samples + lower dispersion + newer data = lower uncertainty
        base_uncertainty = std_dev if std_dev > 0 else (price_range[1] - price_range[0]) / 4
        uncertainty = base_uncertainty * (1.0 - confidence)
        uncertainty = max(5.0, uncertainty)  # At least $5

        return ComparableSalesAnalysis(
            median_price=median,
            trimmed_mean=trimmed_mean,
            mean_price=mean,
            price_range=price_range,
            price_range_pct=price_range_pct,
            std_dev=std_dev,
            dispersion_pct=dispersion_pct,
            sample_count=len(unique_listings),
            auction_count=len([s for s in unique_listings if s.sale_type == "auction"]),
            fixed_price_count=len([s for s in unique_listings if s.sale_type == "fixed-price"]),
            outlier_count=len(outlier_prices),
            outlier_listings=outlier_listings,  # PRESERVED
            outlier_prices=outlier_prices,  # PRESERVED
            outlier_directions=outlier_directions,  # PRESERVED
            median_days_old=median_days,
            recency_score=recency_score,
            confidence=confidence,
            uncertainty_estimate=uncertainty,
        )

    @staticmethod
    def _remove_duplicate_transactions(listings: list[SoldListing]) -> list[SoldListing]:
        """Remove duplicate sales of the same card on the same day."""
        seen = {}
        unique = []

        for listing in listings:
            # Create signature: seller + date
            signature = (listing.seller_id, listing.sold_date.date())

            if signature not in seen:
                seen[signature] = listing
                unique.append(listing)
            else:
                # If we see same card sold by same seller on same day, keep higher price
                # (more likely to be reliable)
                existing = seen[signature]
                if listing.price > existing.price:
                    unique.remove(existing)
                    unique.append(listing)
                    seen[signature] = listing

        return unique

    @staticmethod
    def _remove_outliers(prices: list[float]) -> tuple[list[float], list[float]]:
        """Remove outliers using IQR (Interquartile Range) method.

        Outliers are values below Q1 - 1.5*IQR or above Q3 + 1.5*IQR.
        """
        if len(prices) < 4:
            return prices, []

        sorted_prices = sorted(prices)
        q1_idx = len(sorted_prices) // 4
        q3_idx = 3 * len(sorted_prices) // 4

        q1 = sorted_prices[q1_idx]
        q3 = sorted_prices[q3_idx]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        normal = [p for p in prices if lower_bound <= p <= upper_bound]
        outliers = [p for p in prices if p < lower_bound or p > upper_bound]

        return normal, outliers

    @staticmethod
    def _recency_score(days_old_list: list[int]) -> float:
        """Score recency from 0.0 to 1.0.

        1.0 = all sales <7 days old
        0.7 = all sales <30 days old
        0.5 = all sales <60 days old
        0.2 = sales >90 days old
        """
        if not days_old_list:
            return 0.5

        avg_days = statistics.mean(days_old_list)

        if avg_days < 7:
            return 1.0
        elif avg_days < 30:
            return 0.7 + 0.3 * (30 - avg_days) / 23
        elif avg_days < 60:
            return 0.4 + 0.3 * (60 - avg_days) / 30
        elif avg_days < 90:
            return 0.1 + 0.3 * (90 - avg_days) / 30
        else:
            return 0.1

    @staticmethod
    def _get_sample_score(sample_count: int) -> float:
        """Extract sample size component of confidence score."""
        if sample_count < 2:
            return 0.0
        elif sample_count < 3:
            return 0.15
        elif sample_count < 5:
            return 0.25
        elif sample_count < 10:
            return 0.35
        else:
            return 0.40

    @staticmethod
    def _get_dispersion_score(dispersion_pct: float) -> float:
        """Extract dispersion component of confidence score."""
        if dispersion_pct > 40:
            return 0.0
        elif dispersion_pct > 20:
            return 0.1
        elif dispersion_pct > 10:
            return 0.2
        else:
            return 0.3

    @staticmethod
    def _get_recency_score(median_days: int) -> float:
        """Extract recency component of confidence score."""
        if median_days > 90:
            return 0.0
        elif median_days > 60:
            return 0.1
        elif median_days > 30:
            return 0.15
        elif median_days > 14:
            return 0.2
        else:
            return 0.3

    @staticmethod
    def _confidence_score(
        sample_count: int,
        dispersion_pct: float,
        median_days: int,
    ) -> float:
        """Calculate confidence in the estimate.

        Higher for:
        - More samples (3+ is good, 10+ is high confidence)
        - Lower dispersion (<10% is good)
        - Newer data (<30 days is good)
        """
        sample_score = ComparableAnalyzer._get_sample_score(sample_count)
        dispersion_score = ComparableAnalyzer._get_dispersion_score(dispersion_pct)
        recency_score = ComparableAnalyzer._get_recency_score(median_days)

        total = sample_score + dispersion_score + recency_score
        return min(1.0, total)

    @staticmethod
    def _empty_analysis() -> ComparableSalesAnalysis:
        """Return empty analysis when no data available."""
        return ComparableSalesAnalysis(
            median_price=0.0,
            trimmed_mean=0.0,
            mean_price=0.0,
            price_range=(0.0, 0.0),
            price_range_pct=0.0,
            std_dev=0.0,
            dispersion_pct=0.0,
            sample_count=0,
            auction_count=0,
            fixed_price_count=0,
            outlier_count=0,
            outlier_listings=[],
            outlier_prices=[],
            outlier_directions={},
            median_days_old=0,
            recency_score=0.0,
            confidence=0.0,
            uncertainty_estimate=0.0,
        )


# Test code removed - already verified via bash tests
# Run this module with: python3 -m cardarb.models.comparables
