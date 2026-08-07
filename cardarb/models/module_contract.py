"""Standardized module result contract for all services and analyzers.

All modules (sources, analyzers, strategies, guardrails) return this contract.
Enables composition, logging, auditing, and future agent-driven orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ModuleResult:
    """Standardized output contract for all modules.

    Every module returns this contract. Enables:
    - Consistent logging and audit trails
    - Module composition and orchestration
    - Future agent access to reasoning
    - Recording of confidence at each step
    - Traceability of decisions
    """

    # === Identity ===
    module_name: str  # "CardIdentityValidator", "ComparableAnalyzer", "Strategy.CrossMarket", etc.
    module_version: str  # "1.0", "2.1", etc.
    card_id: Optional[int] = None  # Card being analyzed (None for system-level modules)

    # === Timing ===
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0  # How long the module took

    # === Result ===
    result: Any = None  # The actual output (varies by module)
    result_type: str = ""  # "recommendation", "analysis", "validation", "calculation", etc.
    status: str = "success"  # "success", "partial", "failed", "degraded"

    # === Confidence (independent measures) ===
    confidence_identity: Optional[float] = None  # 0.0-1.0, card match certainty
    confidence_data_quality: Optional[float] = None  # 0.0-1.0, data freshness/reliability
    confidence_valuation: Optional[float] = None  # 0.0-1.0, fair value estimate reliability
    confidence_liquidity: Optional[float] = None  # 0.0-1.0, sale probability
    confidence_risk: Optional[float] = None  # 0.0-1.0, risk assessment
    confidence_return: Optional[float] = None  # 0.0-1.0, return estimate

    # === Evidence & Reasoning ===
    evidence: dict = field(default_factory=dict)  # Supporting data: {key: value}
    reasoning: str = ""  # Plain-English explanation of result
    warnings: list[str] = field(default_factory=list)  # ["Data >30 days old", "Low liquidity"]

    # === Traceability ===
    source_references: list[str] = field(default_factory=list)  # ["eBay#12345", "PWCC#67890"]
    input_hash: Optional[str] = None  # Hash of inputs for reproducibility
    depends_on: list[str] = field(default_factory=list)  # ["ComparableAnalyzer@1.0", "CardIdentityValidator@2.1"]

    # === Metadata ===
    metadata: dict = field(default_factory=dict)  # Any extra context

    def is_success(self) -> bool:
        """Did this module succeed?"""
        return self.status == "success"

    def is_degraded(self) -> bool:
        """Is this result degraded (partial success, reduced confidence)?"""
        return self.status == "degraded"

    def min_confidence(self) -> Optional[float]:
        """Minimum confidence across all applicable measures."""
        confidences = [
            c for c in [
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

    def summary(self) -> str:
        """One-line summary of result."""
        status_emoji = "✓" if self.is_success() else "!" if self.is_degraded() else "✗"
        min_conf = self.min_confidence()
        conf_str = f"{min_conf:.0%}" if min_conf is not None else "—"

        return f"{status_emoji} {self.module_name}: {self.result_type} (confidence: {conf_str})"

    def to_dict(self) -> dict:
        """Serialize for ledger/database storage."""
        return {
            "module_name": self.module_name,
            "module_version": self.module_version,
            "card_id": self.card_id,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "result": str(self.result),
            "result_type": self.result_type,
            "status": self.status,
            "confidence_identity": self.confidence_identity,
            "confidence_data_quality": self.confidence_data_quality,
            "confidence_valuation": self.confidence_valuation,
            "confidence_liquidity": self.confidence_liquidity,
            "confidence_risk": self.confidence_risk,
            "confidence_return": self.confidence_return,
            "evidence": self.evidence,
            "reasoning": self.reasoning,
            "warnings": self.warnings,
            "source_references": self.source_references,
            "input_hash": self.input_hash,
            "depends_on": self.depends_on,
            "metadata": self.metadata,
        }


@dataclass
class RecommendationOutcome:
    """Actual outcome of a recommendation (appended to Decision Ledger later)."""

    recommendation_id: str  # Links to original recommendation in ledger

    # === Execution ===
    execution_timestamp: datetime
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None

    # === Actual Results ===
    actual_buy_price: Optional[float] = None  # What we actually paid
    actual_sell_price: Optional[float] = None  # What we actually received
    actual_acquisition_cost: Optional[float] = None  # All-in cost
    actual_sale_proceeds: Optional[float] = None  # Net proceeds
    actual_profit: Optional[float] = None  # Actual profit/loss
    actual_roic: Optional[float] = None  # Actual ROIC

    # === Timing ===
    actual_holding_days: Optional[int] = None  # How long we held

    # === Quality ===
    prediction_error_profit: Optional[float] = None  # Actual - predicted profit
    prediction_error_roic: Optional[float] = None  # Actual - predicted ROIC
    prediction_error_holding_days: Optional[int] = None  # Actual - predicted days

    # === Notes ===
    notes: str = ""  # Why did actual differ from prediction?

    def to_dict(self) -> dict:
        """Serialize for ledger storage."""
        return {
            "recommendation_id": self.recommendation_id,
            "execution_timestamp": self.execution_timestamp.isoformat(),
            "buy_order_id": self.buy_order_id,
            "sell_order_id": self.sell_order_id,
            "actual_buy_price": self.actual_buy_price,
            "actual_sell_price": self.actual_sell_price,
            "actual_acquisition_cost": self.actual_acquisition_cost,
            "actual_sale_proceeds": self.actual_sale_proceeds,
            "actual_profit": self.actual_profit,
            "actual_roic": self.actual_roic,
            "actual_holding_days": self.actual_holding_days,
            "prediction_error_profit": self.prediction_error_profit,
            "prediction_error_roic": self.prediction_error_roic,
            "prediction_error_holding_days": self.prediction_error_holding_days,
            "notes": self.notes,
        }
