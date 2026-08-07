"""Enhanced Cross-Market Strategy with market signal validation.

Adds critical checks missing from v1:
1. Price momentum on BOTH markets (detect falling knives)
2. Inventory trend on BOTH markets (detect forced selling)
3. Negative information (legitimate reasons for discount)
4. Comp freshness (is fair value still accurate?)

Note: Catalyst detection less critical here (Market B price is the catalyst)
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
    InventoryTrend,
    MarketSignals,
    NegativeInformation,
    PriceMomentum,
)


@dataclass
class CrossMarketOpportunityV2:
    """Enhanced cross-market opportunity with market signal validation."""

    card: CardIdentity
    buy_market: str
    buy_price: float
    sell_market: str
    sell_price_estimate: float

    sold_listings: list[SoldListing]
    economics: TradeEconomics
    guardrails_result: object

    # NEW: Market signals for buy and sell markets
    recommendation: str = "PASS"  # "BUY", "PASS", "RESEARCH"
    buy_market_signals: Optional[MarketSignals] = None
    sell_market_signals: Optional[MarketSignals] = None
    signal_confidence: float = 1.0
    rank_score: float = 0.0


class CrossMarketStrategyV2:
    """Enhanced cross-market strategy with market validation.

    Interprets market signals and makes buy/pass/watch decisions.
    Signals adjust strategy confidence but don't make decisions themselves.
    """

    def __init__(self, guardrails: Optional[ExecutionGuardrails] = None):
        """Initialize strategy."""
        self.guardrails = guardrails or ExecutionGuardrails()
        self.opportunities: list[CrossMarketOpportunityV2] = []

    def find_opportunities(
        self,
        candidates: list[dict],
        current_positions: Optional[dict] = None,
    ) -> list[CrossMarketOpportunityV2]:
        """Find profitable cross-market opportunities validated by market signals.

        Args:
            candidates: List with:
                - card: CardIdentity
                - buy_market: str
                - buy_price: float
                - sell_market: str
                - comparable_sales: list[SoldListing]
                - active_listings: list[dict]
                - buy_market_signals: MarketSignals (NEW)
                - sell_market_signals: MarketSignals (NEW)

            current_positions: Portfolio state
        """
        if current_positions is None:
            current_positions = {}

        self.opportunities = []

        for candidate in candidates:
            opportunity = self._analyze_candidate(candidate, current_positions)
            if opportunity:
                self.opportunities.append(opportunity)

        # Sort by ROIC (capital efficiency)
        self.opportunities.sort(
            key=lambda o: o.rank_score * o.signal_confidence,
            reverse=True,
        )

        return self.opportunities

    def _analyze_candidate(
        self,
        candidate: dict,
        current_positions: dict,
    ) -> Optional[CrossMarketOpportunityV2]:
        """Analyze with market signal validation."""

        card = candidate["card"]
        buy_market = candidate["buy_market"]
        buy_price = candidate["buy_price"]
        sell_market = candidate["sell_market"]
        sold_listings = candidate.get("comparable_sales", [])
        active_listings = candidate.get("active_listings", [])
        buy_market_signals = candidate.get("buy_market_signals", MarketSignals())
        sell_market_signals = candidate.get("sell_market_signals", MarketSignals())

        # Step 1: Identity validation
        if not card.is_valid():
            return None

        # Step 2: Fair value from comps
        if not sold_listings or len(sold_listings) < 3:
            return None

        comparable = ComparableAnalyzer.analyze(sold_listings)
        fair_value = comparable.median_price

        # Use sell price if provided, otherwise use comps
        if "sell_price_synthetic" in candidate:
            sell_price_estimate = candidate["sell_price_synthetic"]
        else:
            sell_price_estimate = fair_value

        # NEW STEP 3: VALIDATE MARKET SIGNALS
        signal_confidence = self._assess_market_signals(
            buy_market_signals, sell_market_signals, buy_price, sell_price_estimate
        )

        # If market signals are VERY negative, reject
        if signal_confidence < 0.3:
            return None

        # Step 4: Calculate economics
        acq_cost = calculate_acquisition_cost(buy_market, purchase_price=buy_price)
        sale_proceeds = calculate_sale_proceeds(sell_market, sale_price=sell_price_estimate)

        economics = TradeEconomics(
            acquisition_cost=acq_cost,
            expected_sale_proceeds=sale_proceeds,
            expected_holding_days=self._estimate_holding_days(active_listings),
        )

        # Step 5: Check guardrails
        liquidity = LiquidityAnalyzer.analyze(sold_listings, active_listings)

        guardrails_result = GuardrailsChecker.check(
            card=card,
            comparable_analysis=comparable,
            liquidity=liquidity,
            economics=economics,
            current_positions=current_positions,
            guardrails=self.guardrails,
        )

        # Step 6: Determine recommendation
        if signal_confidence < 0.5:
            recommendation = "RESEARCH"  # Risky based on signals
        elif economics.expected_net_profit < self.guardrails.min_expected_profit:
            recommendation = "PASS"
        elif economics.expected_roic < self.guardrails.min_expected_roic:
            recommendation = "PASS"
        elif not guardrails_result.passed_all_checks:
            recommendation = "PASS"
        else:
            recommendation = "BUY"

        # Step 7: Create enhanced opportunity
        opportunity = CrossMarketOpportunityV2(
            card=card,
            buy_market=buy_market,
            buy_price=buy_price,
            sell_market=sell_market,
            sell_price_estimate=sell_price_estimate,
            sold_listings=sold_listings,
            economics=economics,
            guardrails_result=guardrails_result,
            buy_market_signals=buy_market_signals,
            sell_market_signals=sell_market_signals,
            signal_confidence=signal_confidence,
            recommendation=recommendation,
            rank_score=economics.expected_roic,
        )

        return opportunity

    def _assess_market_signals(
        self, buy_signals: MarketSignals, sell_signals: MarketSignals, buy_price: float, sell_price: float
    ) -> float:
        """Assess market health on both sides and adjust confidence.

        INTERPRETATION of signals by strategy logic (NOT signal classification).
        - Signals classify market conditions
        - Strategy INTERPRETS those classifications and adjusts confidence
        - Strategy makes final BUY/WATCH/PASS decision

        Returns:
            confidence: 0.0-1.0 multiplier for this strategy
        """
        confidence = 1.0
        spread_pct = (sell_price - buy_price) / buy_price if buy_price > 0 else 0

        # Check BUY market (where we acquire)
        if buy_signals.price_momentum:
            buy_signals.price_momentum.analyze()
            if buy_signals.price_momentum.is_falling_knife():
                # Good for us (lower acquisition cost)
                confidence *= 1.1
            elif buy_signals.price_momentum.trend_7_day == "UP":
                # Bad (prices rising, our cost will rise)
                confidence *= 0.8

        if buy_signals.inventory_trend:
            buy_signals.inventory_trend.analyze()
            if buy_signals.inventory_trend.trend == "RISING":
                # Good for us (falling prices, better acquisition)
                confidence *= 1.1
            elif buy_signals.inventory_trend.trend == "FALLING":
                # Bad (competition, prices rising)
                confidence *= 0.8

        # Check SELL market (where we liquidate)
        if sell_signals.price_momentum:
            sell_signals.price_momentum.analyze()
            if sell_signals.price_momentum.is_falling_knife():
                # Bad for us (sell prices falling)
                confidence *= 0.7
            elif sell_signals.price_momentum.trend_7_day == "UP":
                # Good (our sell price improving)
                confidence *= 1.1

        if sell_signals.inventory_trend:
            sell_signals.inventory_trend.analyze()
            if sell_signals.inventory_trend.trend == "RISING":
                # Bad (supply up, prices falling)
                confidence *= 0.7
            elif sell_signals.inventory_trend.trend == "FALLING":
                # Good (supply down, prices rising)
                confidence *= 1.1

        # Check negative info on both sides
        for signals, market_name in [(buy_signals, "buy"), (sell_signals, "sell")]:
            if signals.negative_info and signals.negative_info.has_serious_issues():
                confidence *= 0.2  # Hard reject

        # Check comp freshness
        if buy_signals.comp_age_days > 30:
            confidence *= buy_signals.comp_freshness_score
        if sell_signals.comp_age_days > 30:
            confidence *= sell_signals.comp_freshness_score

        # Bigger spreads need lower confidence (more risk)
        if spread_pct > 0.70:  # 70%+ spread
            confidence_required = 0.6
        elif spread_pct > 0.40:  # 40-70% spread
            confidence_required = 0.7
        else:  # <40% spread
            confidence_required = 0.8

        if confidence < confidence_required:
            confidence *= 0.8

        return max(0.0, min(1.0, confidence))

    def _estimate_holding_days(self, active_listings: list[dict]) -> int:
        """Estimate holding days (same as v1)."""
        listing_count = len(active_listings) if active_listings else 0

        if listing_count >= 5:
            return 7
        elif listing_count >= 3:
            return 14
        elif listing_count >= 1:
            return 21
        else:
            return 30

    def summary(self) -> str:
        """Generate summary with signal assessment."""
        if not self.opportunities:
            return "No opportunities found."

        buys = [o for o in self.opportunities if o.recommendation == "BUY"]
        research = [o for o in self.opportunities if o.recommendation == "RESEARCH"]
        passes = [o for o in self.opportunities if o.recommendation == "PASS"]

        lines = [
            f"Cross-Market V2: {len(self.opportunities)} candidates analyzed",
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
                    f"Buy ${opp.buy_price:.2f} @ {opp.buy_market.upper()} "
                    f"Sell ${opp.sell_price_estimate:.2f} @ {opp.sell_market.upper()} | "
                    f"Signal confidence {opp.signal_confidence:.0%} | "
                    f"Profit ${opp.economics.expected_net_profit:.2f}"
                )

        return "\n".join(lines)

    @staticmethod
    def as_module_result(opportunity: CrossMarketOpportunityV2) -> "ModuleResult":  # type: ignore
        """Convert strategy opportunity to ModuleResult contract with full reasoning.

        Imports ModuleResult here to avoid circular imports.
        """
        from cardarb.models import ModuleResult

        # Calculate spread and margin
        spread = opportunity.sell_price_estimate - opportunity.buy_price
        spread_pct = (spread / opportunity.buy_price * 100) if opportunity.buy_price > 0 else 0

        return ModuleResult(
            module_name="Strategy.CrossMarket",
            module_version="2.0",
            card_id=opportunity.card.player_name,
            result=opportunity,
            result_type="opportunity_recommendation",
            status="success",
            confidence_return=opportunity.signal_confidence if opportunity.recommendation == "BUY" else None,
            evidence={
                # Market and pricing
                "buy_market": opportunity.buy_market,
                "buy_price": f"${opportunity.buy_price:.2f}",
                "sell_market": opportunity.sell_market,
                "sell_price_estimate": f"${opportunity.sell_price_estimate:.2f}",
                "spread": f"${spread:.2f}",
                "spread_pct": f"{spread_pct:.1f}%",
                # Economics
                "expected_acquisition_cost": f"${opportunity.economics.acquisition_cost.total_cost:.2f}",
                "expected_sale_proceeds": f"${opportunity.economics.expected_sale_proceeds.net_proceeds:.2f}",
                "expected_profit": f"${opportunity.economics.expected_net_profit:.2f}",
                "expected_roic": f"{opportunity.economics.expected_roic:.1%}",
                "expected_holding_days": opportunity.economics.expected_holding_days,
                # Signal assessment
                "signal_confidence": f"{opportunity.signal_confidence:.2f}",
                # Decision reasoning
                "recommendation": opportunity.recommendation,
                "rank_score": f"{opportunity.rank_score:.2f}",
            },
            reasoning=(
                f"CrossMarket opportunity: buy {opportunity.card.player_name} at ${opportunity.buy_price:.2f} "
                f"({opportunity.buy_market}), sell at ${opportunity.sell_price_estimate:.2f} "
                f"({opportunity.sell_market}). "
                f"Expected profit: ${opportunity.economics.expected_net_profit:.2f} ({opportunity.economics.expected_roic:.1%}). "
                f"Signal confidence: {opportunity.signal_confidence:.1%}. "
                f"Recommendation: {opportunity.recommendation}"
            ),
            warnings=(
                [] if opportunity.recommendation != "RESEARCH"
                else [f"Market signals concern: {opportunity.signal_confidence:.1%} confidence (threshold 50%)"]
            ),
        )
