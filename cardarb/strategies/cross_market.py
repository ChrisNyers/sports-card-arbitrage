"""Cross-Market Arbitrage Strategy: Buy at Market A, Sell at Market B.

Buy an identical card at one marketplace (e.g., eBay) and sell it at another
(e.g., PWCC) for a profit after all acquisition, holding, and sale costs.

This is the simplest and lowest-risk strategy because:
- No auction price prediction needed
- No grading risk
- No event dependency
- Clear buy/sell prices upfront
- Fastest feedback loop (days to weeks, not months)
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
class CrossMarketOpportunity:
    """A potential cross-market arbitrage opportunity."""

    card: CardIdentity
    buy_market: str  # "ebay", "pwcc", "comc", etc.
    buy_price: float
    sell_market: str
    sell_price_estimate: float

    sold_listings: list[SoldListing]
    economics: TradeEconomics
    guardrails_result: object  # GuardrailCheckResult

    recommendation: str  # "BUY", "PASS", "RESEARCH"
    rank_score: float  # For sorting (typically ROIC)


class CrossMarketStrategy:
    """Find and rank cross-market arbitrage opportunities."""

    def __init__(self, guardrails: Optional[ExecutionGuardrails] = None):
        """Initialize strategy with guardrails configuration."""
        self.guardrails = guardrails or ExecutionGuardrails()
        self.opportunities: list[CrossMarketOpportunity] = []

    def find_opportunities(
        self,
        candidates: list[dict],
        current_positions: Optional[dict] = None,
    ) -> list[CrossMarketOpportunity]:
        """Find profitable cross-market opportunities.

        Args:
            candidates: List of card candidates with market prices
                Each candidate should have:
                - card: CardIdentity
                - buy_market: str (market to buy from)
                - buy_price: float
                - sell_market: str (market to sell to)
                - comparable_sales: list[SoldListing]
                - active_listings: list[dict] (for liquidity)

            current_positions: Current portfolio state for guardrail checks

        Returns:
            Sorted list of CrossMarketOpportunity objects
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

        # Sort by rank score (ROIC) descending
        self.opportunities.sort(
            key=lambda o: o.rank_score,
            reverse=True,
        )

        return self.opportunities

    def _analyze_candidate(
        self,
        candidate: dict,
        current_positions: dict,
    ) -> Optional[CrossMarketOpportunity]:
        """Analyze a single candidate for profitability and guardrails."""

        card = candidate["card"]
        buy_market = candidate["buy_market"]
        buy_price = candidate["buy_price"]
        sell_market = candidate["sell_market"]
        sold_listings = candidate.get("comparable_sales", [])
        active_listings = candidate.get("active_listings", [])

        # Step 1: Validate card identity
        if not card.is_valid():
            return None  # Confidence too low

        # Step 2: Analyze comparable sales
        if not sold_listings:
            return None  # No data to establish fair value

        comparable = ComparableAnalyzer.analyze(sold_listings)

        if comparable.sample_count < 3:
            return None  # Too few comparables

        # Use comparable median as fair value estimate
        # (In real trading, this comes from Card Ladder/Card Hedge sold data)
        fair_value = comparable.median_price

        # For synthetic testing, use the actual sell price if provided
        # In real system, this would always use comparable median
        if "sell_price_synthetic" in candidate:
            sell_price_estimate = candidate["sell_price_synthetic"]
        else:
            sell_price_estimate = fair_value

        # Step 3: Calculate economics
        acq_cost = calculate_acquisition_cost(buy_market, purchase_price=buy_price)
        sale_proceeds = calculate_sale_proceeds(sell_market, sale_price=sell_price_estimate)

        economics = TradeEconomics(
            acquisition_cost=acq_cost,
            expected_sale_proceeds=sale_proceeds,
            expected_holding_days=self._estimate_holding_days(active_listings),
        )

        # Step 4: Check guardrails
        liquidity = LiquidityAnalyzer.analyze(sold_listings, active_listings)

        guardrails_result = GuardrailsChecker.check(
            card=card,
            comparable_analysis=comparable,
            liquidity=liquidity,
            economics=economics,
            current_positions=current_positions,
            guardrails=self.guardrails,
        )

        # Step 5: Determine recommendation
        if economics.expected_net_profit < self.guardrails.min_expected_profit:
            recommendation = "PASS"
        elif economics.expected_roic < self.guardrails.min_expected_roic:
            recommendation = "PASS"
        elif not guardrails_result.passed_all_checks:
            recommendation = "PASS"
        else:
            recommendation = "BUY"

        # Step 6: Create opportunity record
        opportunity = CrossMarketOpportunity(
            card=card,
            buy_market=buy_market,
            buy_price=buy_price,
            sell_market=sell_market,
            sell_price_estimate=sell_price_estimate,
            sold_listings=sold_listings,
            economics=economics,
            guardrails_result=guardrails_result,
            recommendation=recommendation,
            rank_score=economics.expected_roic,  # Rank by ROIC
        )

        return opportunity

    def _estimate_holding_days(self, active_listings: list[dict]) -> int:
        """Estimate how many days the card will be held before sale."""
        # Heuristic: More active listings = faster sale
        listing_count = len(active_listings) if active_listings else 0

        if listing_count >= 5:
            return 7  # High competition, fast sale
        elif listing_count >= 3:
            return 14
        elif listing_count >= 1:
            return 21
        else:
            return 30  # Low supply, slower sale

    def generate_recommendation_snapshot(
        self,
        opportunity: CrossMarketOpportunity,
        approval_by: Optional[str] = None,
    ) -> RecommendationSnapshot:
        """Convert opportunity to a full recommendation snapshot for tracking."""

        return RecommendationSnapshot(
            rec_id=f"CROSS-{opportunity.card.player_name}-{opportunity.card.year}-{datetime.now().timestamp()}",
            generated_at=datetime.now(),
            card_identity=opportunity.card,
            predicted_fair_value=opportunity.economics.expected_sale_proceeds.sale_price,
            predicted_sale_price=opportunity.economics.expected_sale_proceeds.sale_price,
            predicted_days_to_sale=opportunity.economics.expected_holding_days,
            predicted_profit=opportunity.economics.expected_net_profit,
            predicted_roic=opportunity.economics.expected_roic,
            predicted_confidence=0.85,  # Average confidence for cross-market
            strategy_type="same-card-cross-market",
            market_platform=f"{opportunity.buy_market.upper()}→{opportunity.sell_market.upper()}",
            comparable_analysis=ComparableAnalyzer.analyze(opportunity.sold_listings),
            liquidity_profile=LiquidityAnalyzer.analyze(opportunity.sold_listings),
            target_buy_price=opportunity.buy_price,
            max_buy_price=opportunity.economics.break_even_sale_price() * 0.95,
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
            return "No opportunities found."

        # Count by recommendation
        buys = [o for o in self.opportunities if o.recommendation == "BUY"]
        passes = [o for o in self.opportunities if o.recommendation == "PASS"]

        lines = [
            f"Cross-Market Opportunities: {len(self.opportunities)} candidates analyzed",
            f"  BUY recommendations: {len(buys)}",
            f"  PASS recommendations: {len(passes)}",
            f"",
        ]

        if buys:
            lines.append("Top 5 BUY Opportunities (by ROIC):")
            for i, opp in enumerate(buys[:5], 1):
                lines.append(
                    f"  {i}. {opp.card.short_description()}"
                    f" | Buy ${opp.buy_price:.2f} @ {opp.buy_market.upper()}"
                    f" | Sell ${opp.sell_price_estimate:.2f} @ {opp.sell_market.upper()}"
                    f" | Profit ${opp.economics.expected_net_profit:.2f}"
                    f" | ROIC {opp.rank_score:.1%}"
                )

        return "\n".join(lines)
