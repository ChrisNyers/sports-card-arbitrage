"""Learning loop: capture predictions and outcomes for continuous improvement.

The system learns by comparing:
- What we predicted at recommendation time (snapshot)
- What actually happened (outcome)
- Gap analysis (where we were wrong and why)

This data trains the next iteration of models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .card_identity import CardIdentity
from .comparables import ComparableSalesAnalysis
from .costs import AcquisitionCost, SaleProceeds
from .liquidity import LiquidityProfile


@dataclass
class RecommendationSnapshot:
    """Immutable record of what we predicted at recommendation time.

    This snapshot captures everything about the recommendation so we can
    later compare predictions to actual outcomes.
    """

    rec_id: str  # Unique ID for tracking
    generated_at: datetime

    # Card identity
    card_identity: CardIdentity

    # Predictions we made
    predicted_fair_value: float
    predicted_sale_price: float
    predicted_days_to_sale: int
    predicted_profit: float
    predicted_roic: float
    predicted_confidence: float

    # Strategy & execution
    strategy_type: str  # "same-card-cross-market", "auction-to-fixed", etc.
    market_platform: str  # Where we plan to execute

    # Input data used for prediction
    comparable_analysis: ComparableSalesAnalysis
    liquidity_profile: LiquidityProfile
    news_sentiment_score: Optional[float] = None

    # Guardrails & approval
    guardrails_passed: bool = True
    guardrails_failed: list[str] = field(default_factory=list)
    required_human_approval: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Acquisition plan
    target_buy_price: float = 0.0
    max_buy_price: float = 0.0
    expected_acquisition_cost: Optional[AcquisitionCost] = None
    expected_sale_proceeds: Optional[SaleProceeds] = None

    def is_approved(self) -> bool:
        """Has this recommendation been approved?"""
        return self.approved_by is not None

    def summary(self) -> str:
        """Summary of the recommendation."""
        lines = [
            f"Recommendation ID: {self.rec_id}",
            f"Generated: {self.generated_at.isoformat()}",
            f"Card: {self.card_identity.short_description()}",
            f"Strategy: {self.strategy_type}",
            f"",
            f"Predictions:",
            f"  Fair value: ${self.predicted_fair_value:.2f}",
            f"  Expected sale: ${self.predicted_sale_price:.2f}",
            f"  Expected profit: ${self.predicted_profit:.2f}",
            f"  Expected ROIC: {self.predicted_roic:.1%}",
            f"  Days to sale: {self.predicted_days_to_sale}",
            f"  Confidence: {self.predicted_confidence:.0%}",
            f"",
            f"Status: {'APPROVED' if self.is_approved() else 'PENDING APPROVAL'}",
        ]
        return "\n".join(lines)


@dataclass
class TradeOutcome:
    """What actually happened after we made the recommendation.

    This captures the complete outcome so we can compare predictions
    to reality and measure forecast accuracy.
    """

    rec_id: str  # Links back to RecommendationSnapshot
    outcome_recorded_at: datetime = field(default_factory=datetime.now)

    # Execution: was the recommendation actually executed?
    was_executed: bool = False
    execution_notes: str = ""

    # Purchase (if executed)
    purchased_price: Optional[float] = None
    purchased_date: Optional[datetime] = None
    purchase_notes: str = ""

    # Sale (if executed)
    sold_price: Optional[float] = None
    sold_date: Optional[datetime] = None
    sale_notes: str = ""

    # Actual results
    actual_profit: Optional[float] = None
    actual_roic: Optional[float] = None
    days_held: Optional[int] = None
    was_profitable: Optional[bool] = None

    # Gap analysis
    prediction_error_price: Optional[float] = None  # Predicted - actual
    prediction_error_days: Optional[int] = None
    prediction_error_profit: Optional[float] = None

    # What happened in the market
    market_surprises: str = ""

    def is_complete(self) -> bool:
        """Has this trade been executed and completed?"""
        return self.was_executed and self.sold_date is not None

    def prediction_accuracy(self) -> dict:
        """Measure how accurate our predictions were."""
        return {
            "executed": self.was_executed,
            "price_error": self.prediction_error_price,
            "days_error": self.prediction_error_days,
            "profit_error": self.prediction_error_profit,
            "profitable": self.was_profitable,
            "complete": self.is_complete(),
        }

    def summary(self) -> str:
        """Summary of the outcome."""
        lines = [
            f"Outcome for: {self.rec_id}",
            f"Recorded: {self.outcome_recorded_at.isoformat()}",
            f"",
        ]

        if not self.was_executed:
            lines.append("Status: NOT EXECUTED")
            lines.append(f"Reason: {self.execution_notes}")
        elif not self.is_complete():
            lines.append("Status: EXECUTED, AWAITING SALE")
            lines.append(f"Purchased: ${self.purchased_price:.2f} on {self.purchased_date}")
        else:
            lines.append("Status: COMPLETED")
            lines.append(f"")
            lines.append(f"Execution:")
            lines.append(f"  Purchased: ${self.purchased_price:.2f} on {self.purchased_date}")
            lines.append(f"  Sold: ${self.sold_price:.2f} on {self.sold_date}")
            lines.append(f"  Held: {self.days_held} days")
            lines.append(f"")
            lines.append(f"Results:")
            lines.append(f"  Profit: ${self.actual_profit:.2f}")
            lines.append(f"  ROIC: {self.actual_roic:.1%}")
            lines.append(f"  Profitable: {'YES' if self.was_profitable else 'NO'}")
            lines.append(f"")
            lines.append(f"Prediction Accuracy:")
            lines.append(f"  Price error: ${self.prediction_error_price:.2f}")
            lines.append(f"  Days error: {self.prediction_error_days} days")
            lines.append(f"  Profit error: ${self.prediction_error_profit:.2f}")

        return "\n".join(lines)


@dataclass
class LearningRecorder:
    """Record recommendations and outcomes for learning."""

    recommendations: dict = field(default_factory=dict)  # rec_id -> RecommendationSnapshot
    outcomes: dict = field(default_factory=dict)  # rec_id -> TradeOutcome

    def save_recommendation(self, snapshot: RecommendationSnapshot):
        """Save a recommendation snapshot."""
        self.recommendations[snapshot.rec_id] = snapshot

    def save_outcome(self, outcome: TradeOutcome):
        """Save an outcome for a recommendation."""
        self.outcomes[outcome.rec_id] = outcome

    def get_recommendation(self, rec_id: str) -> Optional[RecommendationSnapshot]:
        """Retrieve a recommendation by ID."""
        return self.recommendations.get(rec_id)

    def get_outcome(self, rec_id: str) -> Optional[TradeOutcome]:
        """Retrieve an outcome by ID."""
        return self.outcomes.get(rec_id)

    def link_outcome_to_recommendation(self, rec_id: str) -> Optional[dict]:
        """Link outcome back to recommendation for gap analysis."""
        rec = self.get_recommendation(rec_id)
        outcome = self.get_outcome(rec_id)

        if not rec or not outcome:
            return None

        if not outcome.is_complete():
            return {
                "rec_id": rec_id,
                "status": "incomplete",
                "recommendation": rec.summary(),
                "outcome": outcome.summary(),
            }

        # Calculate gaps
        gap = {
            "rec_id": rec_id,
            "status": "complete",
            "recommendation": rec,
            "outcome": outcome,
            "gaps": {
                "price_prediction_error": outcome.prediction_error_price or 0.0,
                "days_prediction_error": outcome.prediction_error_days or 0,
                "profit_prediction_error": outcome.prediction_error_profit or 0.0,
                "was_profitable": outcome.was_profitable,
                "matched_prediction": (
                    outcome.was_profitable and rec.predicted_profit > 0
                    or not outcome.was_profitable and rec.predicted_profit <= 0
                ),
            },
        }

        return gap

    def calculate_model_performance(self) -> dict:
        """Calculate overall model performance on completed trades."""
        completed = [
            o for o in self.outcomes.values()
            if o.is_complete()
        ]

        if not completed:
            return {"status": "insufficient_data", "completed_trades": 0}

        # Accuracy metrics
        price_errors = [
            abs(o.prediction_error_price) for o in completed
            if o.prediction_error_price is not None
        ]
        days_errors = [
            abs(o.prediction_error_days) for o in completed
            if o.prediction_error_days is not None
        ]
        profit_errors = [
            abs(o.prediction_error_profit) for o in completed
            if o.prediction_error_profit is not None
        ]

        profitable = sum(1 for o in completed if o.was_profitable)
        win_rate = profitable / len(completed) if completed else 0.0

        import statistics

        return {
            "completed_trades": len(completed),
            "win_rate": win_rate,
            "avg_price_error": statistics.mean(price_errors) if price_errors else 0.0,
            "avg_days_error": statistics.mean(days_errors) if days_errors else 0.0,
            "avg_profit_error": statistics.mean(profit_errors) if profit_errors else 0.0,
            "median_price_error": statistics.median(price_errors) if price_errors else 0.0,
            "median_days_error": statistics.median(days_errors) if days_errors else 0.0,
        }

    def performance_summary(self) -> str:
        """Summary of learning performance."""
        perf = self.calculate_model_performance()

        if perf.get("status") == "insufficient_data":
            return "Not enough completed trades for performance analysis yet."

        lines = [
            f"Model Performance Summary",
            f"Completed Trades: {perf['completed_trades']}",
            f"Win Rate: {perf['win_rate']:.1%}",
            f"",
            f"Prediction Accuracy:",
            f"  Avg price error: ${perf['avg_price_error']:.2f}",
            f"  Median price error: ${perf['median_price_error']:.2f}",
            f"  Avg days error: {perf['avg_days_error']:.0f} days",
            f"  Median days error: {perf['median_days_error']:.0f} days",
            f"  Avg profit error: ${perf['avg_profit_error']:.2f}",
        ]

        return "\n".join(lines)
