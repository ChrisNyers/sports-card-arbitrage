"""Liquidity analysis: how easily and quickly can we sell a card?

Liquidity metrics:
- Historical sales frequency (30/60/90 day)
- Days on market (how long typically listed before sale)
- Active listings (current supply)
- Probability of sale (by timeframe)
- Liquidity score (0-100)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .comparables import SoldListing


@dataclass
class LiquidityProfile:
    """Complete liquidity assessment for a card."""

    # Historical sales activity
    sales_30_days: int
    sales_60_days: int
    sales_90_days: int

    # Timing metrics
    median_days_on_market: float  # How long typically listed before sale
    median_days_between_sales: float  # Time between successive sales

    # Current market
    active_listings: int
    active_sellers: int

    # Market depth
    sell_through_rate: float  # % of listings that actually sell
    listing_price_dispersion: float  # Std dev of asking prices (%)

    # Probability of sale at different timeframes
    prob_sell_7_days: float  # 0.0-1.0
    prob_sell_14_days: float
    prob_sell_30_days: float
    prob_sell_90_days: float

    # Composite score
    liquidity_score: int  # 0-100, higher = more liquid

    def is_liquid_enough(self, required_prob: float = 0.70) -> bool:
        """Is this card liquid enough to trade?"""
        return self.prob_sell_30_days >= required_prob

    def liquidity_summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Sales Activity:",
            f"  30 days: {self.sales_30_days} sales",
            f"  60 days: {self.sales_60_days} sales",
            f"  90 days: {self.sales_90_days} sales",
            f"  Median days on market: {self.median_days_on_market:.0f} days",
            f"  Median days between sales: {self.median_days_between_sales:.0f} days",
            f"",
            f"Current Market:",
            f"  Active listings: {self.active_listings}",
            f"  Active sellers: {self.active_sellers}",
            f"  Sell-through rate: {self.sell_through_rate:.0%}",
            f"  Price dispersion: {self.listing_price_dispersion:.1f}%",
            f"",
            f"Probability of Sale:",
            f"  Within 7 days: {self.prob_sell_7_days:.0%}",
            f"  Within 14 days: {self.prob_sell_14_days:.0%}",
            f"  Within 30 days: {self.prob_sell_30_days:.0%}",
            f"  Within 90 days: {self.prob_sell_90_days:.0%}",
            f"",
            f"Liquidity Score: {self.liquidity_score}/100",
            f"Assessment: {'LIQUID' if self.liquidity_score >= 60 else 'MODERATE' if self.liquidity_score >= 40 else 'ILLIQUID'}",
        ]
        return "\n".join(lines)


class LiquidityAnalyzer:
    """Analyze sold listings to assess market liquidity."""

    @staticmethod
    def analyze(
        sold_listings: list[SoldListing],
        active_listings: Optional[list[dict]] = None,
    ) -> LiquidityProfile:
        """Analyze liquidity from sold transaction history.

        Args:
            sold_listings: Historical sold transactions
            active_listings: Optional current active listings

        Returns:
            LiquidityProfile with liquidity assessment
        """
        if not sold_listings:
            return LiquidityAnalyzer._empty_profile()

        # Count sales by time period
        now = datetime.now()
        sales_30 = [s for s in sold_listings if s.days_ago(now) <= 30]
        sales_60 = [s for s in sold_listings if s.days_ago(now) <= 60]
        sales_90 = [s for s in sold_listings if s.days_ago(now) <= 90]

        # Calculate timing metrics
        if sold_listings:
            sold_dates = [s.sold_date for s in sold_listings]
            days_between = [
                (sold_dates[i] - sold_dates[i + 1]).days
                for i in range(len(sold_dates) - 1)
            ]
            median_days_between = statistics.median(days_between) if days_between else 30
        else:
            median_days_between = 30

        # Estimate days on market (proxy: use sold date spacing)
        median_dom = median_days_between * 0.5  # Assume listed ~half the time between sales

        # Current market metrics
        active_count = len(active_listings) if active_listings else 0
        seller_set = set()
        if active_listings:
            seller_set = set(a.get("seller_id") for a in active_listings if a.get("seller_id"))
        seller_count = len(seller_set)

        # Price dispersion
        if active_listings and len(active_listings) > 1:
            prices = [float(a.get("price", 0)) for a in active_listings if a.get("price")]
            if prices:
                dispersion = (statistics.stdev(prices) / statistics.mean(prices)) * 100
            else:
                dispersion = 0.0
        else:
            dispersion = 0.0

        # Sell-through rate
        if active_listings:
            sell_through = len(sold_listings) / (len(sold_listings) + active_count) if (len(sold_listings) + active_count) > 0 else 0
        else:
            sell_through = 0.5  # Default assumption

        # Probability of sale at different timeframes
        prob_7 = LiquidityAnalyzer._estimate_prob_sale(median_days_between, 7, active_count)
        prob_14 = LiquidityAnalyzer._estimate_prob_sale(median_days_between, 14, active_count)
        prob_30 = LiquidityAnalyzer._estimate_prob_sale(median_days_between, 30, active_count)
        prob_90 = LiquidityAnalyzer._estimate_prob_sale(median_days_between, 90, active_count)

        # Liquidity score (0-100)
        score = LiquidityAnalyzer._calculate_liquidity_score(
            sales_count=len(sold_listings),
            median_dom=median_dom,
            active_listings=active_count,
            sell_through_rate=sell_through,
            prob_30_days=prob_30,
        )

        return LiquidityProfile(
            sales_30_days=len(sales_30),
            sales_60_days=len(sales_60),
            sales_90_days=len(sales_90),
            median_days_on_market=median_dom,
            median_days_between_sales=median_days_between,
            active_listings=active_count,
            active_sellers=seller_count,
            sell_through_rate=sell_through,
            listing_price_dispersion=dispersion,
            prob_sell_7_days=prob_7,
            prob_sell_14_days=prob_14,
            prob_sell_30_days=prob_30,
            prob_sell_90_days=prob_90,
            liquidity_score=score,
        )

    @staticmethod
    def _estimate_prob_sale(median_days_between: float, target_days: int, active_listings: int) -> float:
        """Estimate probability of sale within target_days.

        Uses:
        - Historical sales frequency
        - Current active listings
        - Time horizon
        """
        if median_days_between == 0:
            return 0.5  # Default if no history

        # Base probability: longer timeframe = higher probability
        prob = min(1.0, (target_days / median_days_between) * 0.95)

        # Adjust for supply
        if active_listings <= 1:
            prob *= 1.2  # Low supply = higher probability
        elif active_listings >= 5:
            prob *= 0.8  # High supply = lower probability

        return min(1.0, max(0.1, prob))

    @staticmethod
    def _calculate_liquidity_score(
        sales_count: int,
        median_dom: float,
        active_listings: int,
        sell_through_rate: float,
        prob_30_days: float,
    ) -> int:
        """Calculate liquidity score (0-100).

        Components:
        - Recent sales (20 points): >5 sales/month
        - Fast sales (20 points): <14 days median
        - Supply (20 points): 2-4 active listings
        - Sell-through (20 points): >50% sell through
        - Probability (20 points): >70% prob 30-day sale
        """
        score = 0

        # Recent sales component
        if sales_count >= 5:
            score += 20
        elif sales_count >= 3:
            score += 15
        elif sales_count >= 1:
            score += 10

        # Speed component
        if median_dom < 7:
            score += 20
        elif median_dom < 14:
            score += 15
        elif median_dom < 30:
            score += 10

        # Supply component (sweet spot: 2-4 listings)
        if 2 <= active_listings <= 4:
            score += 20
        elif 1 <= active_listings <= 6:
            score += 15
        elif active_listings >= 1:
            score += 10

        # Sell-through component
        if sell_through_rate >= 0.60:
            score += 20
        elif sell_through_rate >= 0.40:
            score += 15
        elif sell_through_rate >= 0.20:
            score += 10

        # Probability component
        if prob_30_days >= 0.70:
            score += 20
        elif prob_30_days >= 0.50:
            score += 15
        elif prob_30_days >= 0.30:
            score += 10

        return min(100, max(0, score))

    @staticmethod
    def _empty_profile() -> LiquidityProfile:
        """Return empty profile when no data available."""
        return LiquidityProfile(
            sales_30_days=0,
            sales_60_days=0,
            sales_90_days=0,
            median_days_on_market=0.0,
            median_days_between_sales=0.0,
            active_listings=0,
            active_sellers=0,
            sell_through_rate=0.0,
            listing_price_dispersion=0.0,
            prob_sell_7_days=0.0,
            prob_sell_14_days=0.0,
            prob_sell_30_days=0.0,
            prob_sell_90_days=0.0,
            liquidity_score=0,
        )


if __name__ == "__main__":
    # Example: Analyze Mahomes card liquidity
    from datetime import datetime, timedelta

    listings = [
        SoldListing(
            price=145.00,
            sold_date=datetime.now() - timedelta(days=3),
            sale_type="fixed-price",
            transaction_id="ebay-1",
            seller_rating=4.9,
            source="eBay",
        ),
        SoldListing(
            price=142.50,
            sold_date=datetime.now() - timedelta(days=10),
            sale_type="auction",
            transaction_id="ebay-2",
            seller_rating=4.8,
            source="eBay",
        ),
        SoldListing(
            price=148.00,
            sold_date=datetime.now() - timedelta(days=17),
            sale_type="fixed-price",
            transaction_id="pwcc-1",
            seller_rating=5.0,
            source="PWCC",
        ),
        SoldListing(
            price=140.00,
            sold_date=datetime.now() - timedelta(days=24),
            sale_type="auction",
            transaction_id="ebay-3",
            seller_rating=4.7,
            source="eBay",
        ),
        SoldListing(
            price=146.00,
            sold_date=datetime.now() - timedelta(days=52),
            sale_type="fixed-price",
            transaction_id="ebay-4",
            seller_rating=4.9,
            source="eBay",
        ),
    ]

    active = [
        {"price": "150", "seller_id": "seller1"},
        {"price": "145", "seller_id": "seller2"},
        {"price": "152", "seller_id": "seller1"},
    ]

    liquidity = LiquidityAnalyzer.analyze(listings, active)
    print(liquidity.liquidity_summary())
    print(f"\nLiquid enough? {liquidity.is_liquid_enough()}")
