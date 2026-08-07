"""Relative Value Strategy: Buy underpriced, hold for normalization.

Find cards trading below their fair value (established by recent comps).
Buy when discount is meaningful (5-20% below comps) and liquidity is good.

This is lower-risk than cross-market because:
- No need to predict another market's prices
- Price normalization is passive (market forces)
- Shorter holding periods than grading strategies
- Direct feedback loop (comps tell us when to sell)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from cardarb.models import (
    CardIdentity,
    ComparableAnalyzer,
    ExecutionGuardrails,
    GuardrailsChecker,
    LiquidityAnalyzer,
    RecommendationSnapshot,
    SoldListing,
    TradeEconomics,
    calculate_acquisition_cost,
    calculate_sale_proceeds,
)


@dataclass
class RelativeValueOpportunity:
    """An opportunity to buy underpriced and hold for normalization."""

    card: CardIdentity
    current_ask_price: float  # What we'd pay now
    fair_value: float  # What comps say it should be worth
    discount_pct: float  # How much below fair value (0.05 = 5% discount)

    sold_listings: list[SoldListing]
    active_listings: list[dict]

    economics: TradeEconomics
    guardrails_result: object  # GuardrailCheckResult

    recommendation: str  # "BUY", "PASS", "RESEARCH"
    rank_score: float  # For sorting (typically discount % or ROIC)


class RelativeValueStrategy:
    """Find and rank relative value opportunities."""

    def __init__(self, guardrails: Optional[ExecutionGuardrails] = None):
        """Initialize strategy with guardrails configuration."""
        self.guardrails = guardrails or ExecutionGuardrails()
        self.opportunities: list[RelativeValueOpportunity] = []

    def find_opportunities(
        self,
        candidates: list[dict],
        current_positions: Optional[dict] = None,
    ) -> list[RelativeValueOpportunity]:
        """Find underpriced cards with good upside.

        Args:
            candidates: List of card candidates
                Each candidate should have:
                - card: CardIdentity
                - current_ask_price: float (lowest current asking price)
                - sold_listings: list[SoldListing] (recent comps)
                - active_listings: list[dict] (for liquidity assessment)

            current_positions: Current portfolio state for guardrail checks

        Returns:
            Sorted list of RelativeValueOpportunity objects
        """
        if current_positions is None:
            current_positions = {}

        self.opportunities = []

        for candidate in candidates:
            opportunity = self._analyze_candidate(
                candidate,
                current_positions,
            )

            if opportunity:
                self.opportunities.append(opportunity)

        # Sort by discount % descending (biggest discounts first)
        # These have more upside potential
        self.opportunities.sort(
            key=lambda o: o.discount_pct,
            reverse=True,
        )

        return self.opportunities

    def _analyze_candidate(
        self,
        candidate: dict,
        current_positions: dict,
    ) -> Optional[RelativeValueOpportunity]:
        """Analyze a single candidate for underpricing."""

        card = candidate["card"]
        current_ask_price = candidate.get("current_ask_price", 0)
        sold_listings = candidate.get("sold_listings", [])
        active_listings = candidate.get("active_listings", [])

        # Step 1: Validate card identity
        if not card.is_valid():
            return None

        # Step 2: Analyze comparables to establish fair value
        if not sold_listings or len(sold_listings) < 3:
            return None  # Need minimum sample size

        comparable = ComparableAnalyzer.analyze(sold_listings)
        fair_value = comparable.median_price

        # Step 3: Calculate discount
        if current_ask_price <= 0 or current_ask_price >= fair_value:
            return None  # Not underpriced, or price data missing

        discount_pct = (fair_value - current_ask_price) / fair_value
        discount_amount = fair_value - current_ask_price

        # Step 4: Filter for meaningful discounts
        # Need at least 5% discount to make it worth the fees
        if discount_pct < 0.05:
            return None

        # Step 5: Calculate economics
        # Buying at current_ask_price, selling at fair_value
        acq_cost = calculate_acquisition_cost("ebay", purchase_price=current_ask_price)
        sale_proceeds = calculate_sale_proceeds("ebay", sale_price=fair_value)

        economics = TradeEconomics(
            acquisition_cost=acq_cost,
            expected_sale_proceeds=sale_proceeds,
            expected_holding_days=self._estimate_holding_days(active_listings, discount_pct),
        )

        # Step 6: Check guardrails
        liquidity = LiquidityAnalyzer.analyze(sold_listings, active_listings)

        guardrails_result = GuardrailsChecker.check(
            card=card,
            comparable_analysis=comparable,
            liquidity=liquidity,
            economics=economics,
            current_positions=current_positions,
            guardrails=self.guardrails,
        )

        # Step 7: Determine recommendation
        if economics.expected_net_profit < self.guardrails.min_expected_profit:
            recommendation = "PASS"
        elif economics.expected_roic < self.guardrails.min_expected_roic:
            recommendation = "PASS"
        elif not guardrails_result.passed_all_checks:
            recommendation = "PASS"
        else:
            recommendation = "BUY"

        # Step 8: Create opportunity record
        opportunity = RelativeValueOpportunity(
            card=card,
            current_ask_price=current_ask_price,
            fair_value=fair_value,
            discount_pct=discount_pct,
            sold_listings=sold_listings,
            active_listings=active_listings,
            economics=economics,
            guardrails_result=guardrails_result,
            recommendation=recommendation,
            rank_score=discount_pct,  # Rank by discount % (higher = better)
        )

        return opportunity

    def _estimate_holding_days(self, active_listings: list[dict], discount_pct: float) -> int:
        """Estimate holding time for underpriced card to normalize.

        Bigger discounts take longer to normalize. More active listings = faster.
        """
        listing_count = len(active_listings) if active_listings else 0

        # Bigger discount = longer hold (market needs time to recognize value)
        if discount_pct > 0.20:
            base_days = 45  # 20%+ discount takes time
        elif discount_pct > 0.10:
            base_days = 30  # 10-20% discount
        else:
            base_days = 15  # 5-10% discount normalizes faster

        # More competition = faster normalization
        if listing_count >= 10:
            return base_days // 2
        elif listing_count >= 5:
            return base_days
        elif listing_count >= 2:
            return base_days + 15
        else:
            return base_days + 30

    def generate_recommendation_snapshot(
        self,
        opportunity: RelativeValueOpportunity,
        approval_by: Optional[str] = None,
    ) -> RecommendationSnapshot:
        """Convert opportunity to a full recommendation snapshot."""

        return RecommendationSnapshot(
            rec_id=f"RELVAL-{opportunity.card.player_name}-{opportunity.card.year}-{datetime.now().timestamp()}",
            generated_at=datetime.now(),
            card_identity=opportunity.card,
            predicted_fair_value=opportunity.fair_value,
            predicted_sale_price=opportunity.fair_value,
            predicted_days_to_sale=opportunity.economics.expected_holding_days,
            predicted_profit=opportunity.economics.expected_net_profit,
            predicted_roic=opportunity.economics.expected_roic,
            predicted_confidence=0.80,  # Slightly lower (depends on comps stability)
            strategy_type="relative-value",
            market_platform="eBay",
            comparable_analysis=ComparableAnalyzer.analyze(opportunity.sold_listings),
            liquidity_profile=LiquidityAnalyzer.analyze(opportunity.sold_listings, opportunity.active_listings),
            target_buy_price=opportunity.current_ask_price,
            max_buy_price=opportunity.current_ask_price,
            expected_acquisition_cost=opportunity.economics.acquisition_cost,
            expected_sale_proceeds=opportunity.economics.expected_sale_proceeds,
            guardrails_passed=opportunity.guardrails_result.passed_all_checks,
            guardrails_failed=opportunity.guardrails_result.failed_checks,
            approved_by=approval_by,
            approved_at=datetime.now() if approval_by else None,
        )

    def summary(self) -> str:
        """Generate summary of opportunities found."""
        if not self.opportunities:
            return "No underpriced opportunities found."

        buys = [o for o in self.opportunities if o.recommendation == "BUY"]
        passes = [o for o in self.opportunities if o.recommendation == "PASS"]

        lines = [
            f"Relative Value Opportunities: {len(self.opportunities)} candidates analyzed",
            f"  BUY recommendations: {len(buys)}",
            f"  PASS recommendations: {len(passes)}",
            f"",
        ]

        if buys:
            lines.append("Top 5 BUY Opportunities (by discount %):")
            for i, opp in enumerate(buys[:5], 1):
                lines.append(
                    f"  {i}. {opp.card.short_description()}"
                    f" | Current ask ${opp.current_ask_price:.2f}"
                    f" | Fair value ${opp.fair_value:.2f}"
                    f" | Discount {opp.discount_pct:.1%}"
                    f" | Profit ${opp.economics.expected_net_profit:.2f}"
                    f" | ROIC {opp.economics.expected_roic:.1%}"
                )

        return "\n".join(lines)
