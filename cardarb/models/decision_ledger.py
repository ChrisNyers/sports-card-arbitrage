"""Permanent Recommendation Decision Ledger.

Records every recommendation made in testing and shadow mode.
Enables outcome tracking, prediction verification, and learning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .module_contract import RecommendationOutcome


@dataclass
class DecisionLedgerEntry:
    """Complete record of a single recommendation decision.

    Records which modules actually influenced the recommendation,
    enabling auditability and reproducibility of decisions.
    """

    # === Identification ===
    recommendation_id: str  # Unique ID (UUID or hash)
    card_id: int  # Which card
    timestamp: datetime  # When recommendation was made

    # === Input Context ===
    data_snapshot: dict  # Complete snapshot of all input data
    module_outputs: list[dict]  # All ModuleResult outputs (serialized)

    # === Module Usage (Auditability) ===
    modules_consulted: list[str] = field(default_factory=list)  # Which modules influenced this decision

    # === Confidence Measures (INDEPENDENT) ===
    confidence_identity: Optional[float] = None  # Card match certainty
    confidence_data_quality: Optional[float] = None  # Data freshness/reliability
    confidence_valuation: Optional[float] = None  # Fair value estimate
    confidence_liquidity: Optional[float] = None  # Sale probability
    confidence_risk: Optional[float] = None  # Risk assessment
    confidence_return: Optional[float] = None  # Return estimate

    # === Recommendation ===
    strategy: str = ""  # "CrossMarket", "RelativeValue", etc.
    recommendation: str = "PASS"  # "BUY", "PASS", "WATCH"
    buy_market: Optional[str] = None
    buy_price: Optional[float] = None
    sell_market: Optional[str] = None
    sell_price_estimate: Optional[float] = None

    # === Expected Economics ===
    expected_acquisition_cost: Optional[float] = None
    expected_sale_proceeds: Optional[float] = None
    expected_profit: Optional[float] = None
    expected_roic: Optional[float] = None
    expected_holding_days: Optional[int] = None

    # === Reasoning ===
    reasoning: str = ""  # Why this recommendation?
    guardrail_result: Optional[dict] = None  # Guardrail check result

    # === Execution Status ===
    status: str = "pending"  # "pending", "executed", "expired", "cancelled"
    executed_timestamp: Optional[datetime] = None

    # === Outcome (appended later) ===
    outcome: Optional[RecommendationOutcome] = None

    # === Analysis ===
    metadata: dict = field(default_factory=dict)

    def get_prediction_accuracy(self) -> Optional[dict]:
        """Calculate prediction accuracy if outcome available."""
        if not self.outcome:
            return None

        return {
            "profit_error": self.outcome.prediction_error_profit,
            "roic_error": self.outcome.prediction_error_roic,
            "holding_days_error": self.outcome.prediction_error_holding_days,
            "profit_accurate": (
                abs(self.outcome.prediction_error_profit or 0) < (self.expected_profit or 0) * 0.2
                if self.expected_profit
                else None
            ),
            "roic_accurate": (
                abs(self.outcome.prediction_error_roic or 0) < (self.expected_roic or 0) * 0.2
                if self.expected_roic
                else None
            ),
        }

    def min_confidence(self) -> Optional[float]:
        """Minimum confidence across all measures."""
        confidences = [
            c
            for c in [
                self.confidence_identity,
                self.confidence_data_quality,
                self.confidence_valuation,
                self.confidence_liquidity,
                self.confidence_risk,
                self.confidence_return,
            ]
            if c is not None
        ]
        return min(confidences) if confidences else None

    def to_dict(self) -> dict:
        """Serialize for storage."""
        return {
            "recommendation_id": self.recommendation_id,
            "card_id": self.card_id,
            "timestamp": self.timestamp.isoformat(),
            "modules_consulted": self.modules_consulted,
            "data_snapshot": self.data_snapshot,
            "module_outputs": self.module_outputs,
            "confidence_identity": self.confidence_identity,
            "confidence_data_quality": self.confidence_data_quality,
            "confidence_valuation": self.confidence_valuation,
            "confidence_liquidity": self.confidence_liquidity,
            "confidence_risk": self.confidence_risk,
            "confidence_return": self.confidence_return,
            "strategy": self.strategy,
            "recommendation": self.recommendation,
            "buy_market": self.buy_market,
            "buy_price": self.buy_price,
            "sell_market": self.sell_market,
            "sell_price_estimate": self.sell_price_estimate,
            "expected_acquisition_cost": self.expected_acquisition_cost,
            "expected_sale_proceeds": self.expected_sale_proceeds,
            "expected_profit": self.expected_profit,
            "expected_roic": self.expected_roic,
            "expected_holding_days": self.expected_holding_days,
            "reasoning": self.reasoning,
            "guardrail_result": self.guardrail_result,
            "status": self.status,
            "executed_timestamp": self.executed_timestamp.isoformat() if self.executed_timestamp else None,
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "metadata": self.metadata,
        }


class DecisionLedger:
    """In-memory decision ledger for testing/shadow mode.

    Production version would use persistent storage (SQLite, PostgreSQL, etc.).
    This version is suitable for shadow mode validation and testing.
    """

    def __init__(self):
        """Initialize empty ledger."""
        self.entries: list[DecisionLedgerEntry] = []
        self._by_id: dict[str, DecisionLedgerEntry] = {}

    def record(self, entry: DecisionLedgerEntry) -> None:
        """Record a new recommendation."""
        self.entries.append(entry)
        self._by_id[entry.recommendation_id] = entry

    def get(self, recommendation_id: str) -> Optional[DecisionLedgerEntry]:
        """Retrieve a recommendation by ID."""
        return self._by_id.get(recommendation_id)

    def append_outcome(self, recommendation_id: str, outcome: RecommendationOutcome) -> bool:
        """Append actual outcome to a recommendation."""
        entry = self.get(recommendation_id)
        if not entry:
            return False

        entry.outcome = outcome
        entry.status = "executed"
        entry.executed_timestamp = outcome.execution_timestamp
        return True

    def get_by_card(self, card_id: int) -> list[DecisionLedgerEntry]:
        """Get all recommendations for a card."""
        return [e for e in self.entries if e.card_id == card_id]

    def get_by_status(self, status: str) -> list[DecisionLedgerEntry]:
        """Get all recommendations with a given status."""
        return [e for e in self.entries if e.status == status]

    def get_with_outcomes(self) -> list[DecisionLedgerEntry]:
        """Get all recommendations with recorded outcomes."""
        return [e for e in self.entries if e.outcome is not None]

    def get_accuracy_stats(self) -> dict:
        """Calculate accuracy statistics across all recommendations with outcomes."""
        with_outcomes = self.get_with_outcomes()
        if not with_outcomes:
            return {}

        accuracy_results = [e.get_prediction_accuracy() for e in with_outcomes]
        accuracy_results = [r for r in accuracy_results if r]

        if not accuracy_results:
            return {}

        profit_errors = [r["profit_error"] for r in accuracy_results if r.get("profit_error") is not None]
        roic_errors = [r["roic_error"] for r in accuracy_results if r.get("roic_error") is not None]

        return {
            "total_recommendations": len(self.entries),
            "with_outcomes": len(with_outcomes),
            "average_profit_error": sum(profit_errors) / len(profit_errors) if profit_errors else None,
            "average_roic_error": sum(roic_errors) / len(roic_errors) if roic_errors else None,
            "mean_absolute_profit_error": (
                sum(abs(e) for e in profit_errors) / len(profit_errors) if profit_errors else None
            ),
            "mean_absolute_roic_error": (
                sum(abs(e) for e in roic_errors) / len(roic_errors) if roic_errors else None
            ),
            "profit_accuracy_count": sum(1 for r in accuracy_results if r.get("profit_accurate")),
            "roic_accuracy_count": sum(1 for r in accuracy_results if r.get("roic_accurate")),
        }

    def export(self) -> list[dict]:
        """Export all entries as dicts (for serialization)."""
        return [e.to_dict() for e in self.entries]

    def summary(self) -> str:
        """Human-readable summary of ledger state."""
        pending = self.get_by_status("pending")
        executed = self.get_by_status("executed")
        stats = self.get_accuracy_stats()

        lines = [
            f"Decision Ledger: {len(self.entries)} total",
            f"  Pending: {len(pending)}",
            f"  Executed: {len(executed)}",
        ]

        if stats.get("average_profit_error") is not None:
            lines.append(f"  Avg profit error: ${stats['average_profit_error']:.2f}")
        if stats.get("average_roic_error") is not None:
            lines.append(f"  Avg ROIC error: {stats['average_roic_error']:.1%}")

        return "\n".join(lines)
