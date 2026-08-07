"""Enhanced Relative Value Strategy with market signal validation.

Adds critical checks missing from v1:
1. Price momentum (detect falling knives)
2. Inventory trend (detect forced selling)
3. Catalyst identification (what triggers recovery?)
4. Negative information (legitimate reasons for discount)
5. Comp freshness (is fair value still accurate?)
6. Volume confirmation (do buyers exist at fair value?)
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
from cardarb.models.market_signals import (
    Catalyst,
    CatalystList,
    InventoryTrend,
    MarketSignals,
    NegativeInformation,
    PriceMomentum,
    VolumeProfile,
)


@dataclass
class RelativeValueOpportunityV2:
    """Enhanced opportunity with market signal assessment."""

    card: CardIdentity
    current_ask_price: float
    fair_value: float
    discount_pct: float

    sold_listings: list[SoldListing]
    active_listings: list[dict]

    economics: TradeEconomics
    guardrails_result: object

    # NEW: Market signals
    recommendation: str = "PASS"  # "BUY", "PASS", "RESEARCH"
    market_signals: Optional[MarketSignals] = None
    signal_confidence: float = 1.0
    rank_score: float = 0.0


class RelativeValueStrategyV2:
    """Enhanced relative value strategy with market validation."""

    def __init__(self, guardrails: Optional[ExecutionGuardrails] = None):
        """Initialize strategy."""
        self.guardrails = guardrails or ExecutionGuardrails()
        self.opportunities: list[RelativeValueOpportunityV2] = []

    def find_opportunities(
        self,
        candidates: list[dict],
        current_positions: Optional[dict] = None,
    ) -> list[RelativeValueOpportunityV2]:
        """Find underpriced cards validated by market signals.

        Args:
            candidates: List with:
                - card: CardIdentity
                - current_ask_price: float
                - sold_listings: list[SoldListing]
                - active_listings: list[dict]
                - market_signals: MarketSignals (NEW)

            current_positions: Portfolio state
        """
        if current_positions is None:
            current_positions = {}

        self.opportunities = []

        for candidate in candidates:
            opportunity = self._analyze_candidate(candidate, current_positions)
            if opportunity:
                self.opportunities.append(opportunity)

        # Rank by signal-confidence-adjusted discount
        # Higher discount + higher confidence = better rank
        self.opportunities.sort(
            key=lambda o: o.discount_pct * o.signal_confidence,
            reverse=True,
        )

        return self.opportunities

    def _analyze_candidate(
        self,
        candidate: dict,
        current_positions: dict,
    ) -> Optional[RelativeValueOpportunityV2]:
        """Analyze with market signal validation."""

        card = candidate["card"]
        current_ask_price = candidate.get("current_ask_price", 0)
        sold_listings = candidate.get("sold_listings", [])
        active_listings = candidate.get("active_listings", [])
        market_signals = candidate.get("market_signals", MarketSignals())

        # Step 1: Identity validation
        if not card.is_valid():
            return None

        # Step 2: Fair value from comps
        if not sold_listings or len(sold_listings) < 3:
            return None

        comparable = ComparableAnalyzer.analyze(sold_listings)
        fair_value = comparable.median_price

        # Step 3: Detect underpricing
        if current_ask_price <= 0 or current_ask_price >= fair_value:
            return None

        discount_pct = (fair_value - current_ask_price) / fair_value

        # Step 4: Filter for meaningful discount
        if discount_pct < 0.05:
            return None

        # NEW STEP 5: VALIDATE WITH MARKET SIGNALS
        signal_confidence = self._assess_market_signals(market_signals, discount_pct)

        # If market signals are VERY negative, reject
        if signal_confidence < 0.3:
            return None

        # Step 6: Calculate economics
        acq_cost = calculate_acquisition_cost("ebay", purchase_price=current_ask_price)
        sale_proceeds = calculate_sale_proceeds("ebay", sale_price=fair_value)

        # Adjust holding days based on catalyst timeline
        holding_days = self._estimate_holding_days(active_listings, discount_pct, market_signals)

        economics = TradeEconomics(
            acquisition_cost=acq_cost,
            expected_sale_proceeds=sale_proceeds,
            expected_holding_days=holding_days,
        )

        # Step 7: Check guardrails
        liquidity = LiquidityAnalyzer.analyze(sold_listings, active_listings)

        guardrails_result = GuardrailsChecker.check(
            card=card,
            comparable_analysis=comparable,
            liquidity=liquidity,
            economics=economics,
            current_positions=current_positions,
            guardrails=self.guardrails,
        )

        # Step 8: Determine recommendation
        if not market_signals.is_safe_opportunity():
            recommendation = "RESEARCH"  # Not safe yet
        elif economics.expected_net_profit < self.guardrails.min_expected_profit:
            recommendation = "PASS"
        elif economics.expected_roic < self.guardrails.min_expected_roic:
            recommendation = "PASS"
        elif not guardrails_result.passed_all_checks:
            recommendation = "PASS"
        else:
            recommendation = "BUY"

        # Step 9: Create enhanced opportunity
        opportunity = RelativeValueOpportunityV2(
            card=card,
            current_ask_price=current_ask_price,
            fair_value=fair_value,
            discount_pct=discount_pct,
            sold_listings=sold_listings,
            active_listings=active_listings,
            economics=economics,
            guardrails_result=guardrails_result,
            market_signals=market_signals,
            signal_confidence=signal_confidence,
            recommendation=recommendation,
            rank_score=discount_pct * signal_confidence,
        )

        return opportunity

    def _assess_market_signals(self, signals: MarketSignals, discount_pct: float) -> float:
        """Assess how much we trust this opportunity based on market signals.

        Returns:
            confidence: 0.0-1.0, where 1.0 = fully trusted, 0.0 = ignore
        """
        confidence = 1.0

        # 1. Price momentum check
        if signals.price_momentum:
            signals.price_momentum.analyze()
            if signals.price_momentum.is_falling_knife():
                confidence *= 0.2  # Big red flag
            elif signals.price_momentum.is_stable():
                confidence *= 1.0  # Good
            else:
                confidence *= 0.8

        # 2. Inventory trend check
        if signals.inventory_trend:
            signals.inventory_trend.analyze()
            if signals.inventory_trend.is_danger_signal():
                confidence *= 0.1  # Critical risk
            elif signals.inventory_trend.trend == "STABLE":
                confidence *= 1.0  # Good
            else:
                confidence *= 0.8

        # 3. Catalyst check
        if signals.catalysts:
            if signals.catalysts.has_near_term_catalyst():
                confidence *= 1.2  # Strong catalyst = accelerated recovery
            else:
                confidence *= 0.5  # No catalyst = speculation

        # 4. Negative information check
        if signals.negative_info:
            if signals.negative_info.has_serious_issues():
                confidence *= 0.0  # Hard reject
            else:
                confidence *= 1.0  # Good

        # 5. Comp freshness check
        if signals.comp_age_days > 30:
            confidence *= signals.comp_freshness_score
        else:
            confidence *= 1.0  # Recent comps

        # 6. Volume confirmation check
        if signals.volume_profile:
            signals.volume_profile.analyze()
            if signals.volume_profile.confirms_discount():
                confidence *= 1.0  # Market confirms fair value
            else:
                confidence *= 0.4  # No buyers at fair value

        # Bigger discounts need higher confidence
        if discount_pct < 0.10:  # 5-10% discount
            confidence_required = 0.7
        elif discount_pct < 0.20:  # 10-20% discount
            confidence_required = 0.6
        elif discount_pct < 0.40:  # 20-40% discount
            confidence_required = 0.5
        else:  # 40%+ discount
            confidence_required = 0.4

        # Adjust if we're below required threshold
        if confidence < confidence_required:
            confidence *= 0.8  # Further reduce confidence

        return max(0.0, min(1.0, confidence))

    def _estimate_holding_days(
        self, active_listings: list[dict], discount_pct: float, signals: MarketSignals
    ) -> int:
        """Estimate holding time, adjusted for catalysts."""

        listing_count = len(active_listings) if active_listings else 0

        # Base estimate from discount size
        if discount_pct > 0.20:
            base_days = 45
        elif discount_pct > 0.10:
            base_days = 30
        else:
            base_days = 15

        # Adjust for active listings
        if listing_count >= 10:
            base_days = base_days // 2
        elif listing_count >= 5:
            pass  # No change
        elif listing_count >= 2:
            base_days += 15
        else:
            base_days += 30

        # NEW: Adjust for catalyst timeline
        if signals.catalysts and signals.catalysts.has_near_term_catalyst():
            best = signals.catalysts.best_catalyst()
            if best:
                # Use catalyst timeline as guidance
                base_days = min(base_days, best.days_until + 7)

        return base_days

    def summary(self) -> str:
        """Generate summary with signal assessment."""
        if not self.opportunities:
            return "No opportunities found."

        buys = [o for o in self.opportunities if o.recommendation == "BUY"]
        research = [o for o in self.opportunities if o.recommendation == "RESEARCH"]
        passes = [o for o in self.opportunities if o.recommendation == "PASS"]

        lines = [
            f"Relative Value V2: {len(self.opportunities)} candidates analyzed",
            f"  BUY recommendations: {len(buys)}",
            f"  RESEARCH (needs signals): {len(research)}",
            f"  PASS recommendations: {len(passes)}",
            f"",
        ]

        if buys:
            lines.append("Top 3 BUY (validated by market signals):")
            for i, opp in enumerate(buys[:3], 1):
                lines.append(
                    f"  {i}. {opp.card.short_description()} | "
                    f"Discount {opp.discount_pct:.0%} | "
                    f"Signal confidence {opp.signal_confidence:.0%} | "
                    f"Profit ${opp.economics.expected_net_profit:.2f}"
                )

        return "\n".join(lines)
