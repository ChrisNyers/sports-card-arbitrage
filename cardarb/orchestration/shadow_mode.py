"""ShadowModeOrchestrator: coordination layer without execution.

Orchestrates strategy decisions in non-binding mode:
- Runs all modules independently
- Records recommendations without executing trades
- Enables prediction validation and learning feedback
- Future-ready for multi-agent coordination

This is the future coordination/control layer referenced in Phase 1 roadmap.
Business logic stays in modules (strategies, guardrails, analyzers).
Orchestration logic only coordinates composition and recording.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from cardarb.models import (
    CardIdentity,
    ComparableAnalyzer,
    DecisionLedger,
    DecisionLedgerEntry,
    ExecutionGuardrails,
    GuardrailsChecker,
    LiquidityAnalyzer,
    ModuleResult,
    RiskLevel,
)


@dataclass
class OrchestrationContext:
    """Context for a single orchestration run."""

    run_id: str  # Unique run identifier
    timestamp: datetime
    mode: str  # "shadow", "backtest", "live"
    card_id: int
    card: CardIdentity
    strategy_name: str

    # Module outputs (kept independent)
    module_results: list[ModuleResult] = field(default_factory=list)

    # Recommendation decision
    recommendation: str = "PASS"  # "BUY", "PASS", "WATCH"
    recommendation_id: Optional[str] = None

    # Metadata
    metadata: dict = field(default_factory=dict)

    def add_module_result(self, result: ModuleResult) -> None:
        """Record module output."""
        self.module_results.append(result)

    def get_module_results(self, module_name: str) -> list[ModuleResult]:
        """Get results from a specific module."""
        return [r for r in self.module_results if r.module_name == module_name]

    def min_confidence(self) -> Optional[float]:
        """Minimum confidence across all modules."""
        confidences = []
        for result in self.module_results:
            if result.min_confidence() is not None:
                confidences.append(result.min_confidence())

        return min(confidences) if confidences else None


class ShadowModeOrchestrator:
    """Non-binding orchestration layer for strategy testing and validation.

    Key responsibilities:
    1. Compose independent module calls (strategies, guardrails, analyzers)
    2. Record recommendations to decision ledger with complete context
    3. Enable outcome tracking and prediction validation
    4. Prepare system for future multi-agent coordination

    Does NOT:
    - Execute trades
    - Make autonomous decisions
    - Combine confidence measures prematurely
    - Replace module business logic
    """

    def __init__(self, ledger: Optional[DecisionLedger] = None):
        """Initialize orchestrator with optional ledger.

        Args:
            ledger: DecisionLedger for recording recommendations. If None,
                   in-memory ledger is created.
        """
        self.ledger = ledger or DecisionLedger()
        self.contexts: dict[str, OrchestrationContext] = {}

    def create_context(
        self,
        card_id: int,
        card: CardIdentity,
        strategy_name: str,
        mode: str = "shadow",
    ) -> OrchestrationContext:
        """Create context for a strategy evaluation run."""
        run_id = str(uuid.uuid4())
        ctx = OrchestrationContext(
            run_id=run_id,
            timestamp=datetime.now(),
            mode=mode,
            card_id=card_id,
            card=card,
            strategy_name=strategy_name,
        )
        self.contexts[run_id] = ctx
        return ctx

    def run_strategy(
        self,
        strategy_module: "ModuleResult",  # type: ignore
        context: OrchestrationContext,
    ) -> Optional[str]:
        """Run strategy and record decision.

        Args:
            strategy_module: ModuleResult from strategy execution
            context: OrchestrationContext for this run

        Returns:
            recommendation_id if recorded to ledger, None if rejected
        """
        context.add_module_result(strategy_module)

        # Extract recommendation from strategy result
        if hasattr(strategy_module.result, "recommendation"):
            context.recommendation = strategy_module.result.recommendation
        elif isinstance(strategy_module.result, str):
            context.recommendation = strategy_module.result

        # Don't record if strategy says PASS (no opportunity)
        if context.recommendation == "PASS":
            return None

        # Generate recommendation ID
        rec_id = str(uuid.uuid4())
        context.recommendation_id = rec_id

        return rec_id

    def run_guardrails(
        self,
        guardrails_module: ModuleResult,
        context: OrchestrationContext,
    ) -> bool:
        """Run guardrails and record risk assessment.

        Args:
            guardrails_module: ModuleResult from guardrails check
            context: OrchestrationContext for this run

        Returns:
            True if guardrails passed, False otherwise
        """
        context.add_module_result(guardrails_module)

        # Extract pass/fail from guardrails result
        if hasattr(guardrails_module.result, "passed_all_checks"):
            return guardrails_module.result.passed_all_checks

        return guardrails_module.status == "success"

    def record_decision(
        self,
        context: OrchestrationContext,
        expected_profit: Optional[float] = None,
        expected_roic: Optional[float] = None,
        expected_holding_days: Optional[int] = None,
        reasoning: str = "",
        data_snapshot: Optional[dict] = None,
    ) -> Optional[str]:
        """Record recommendation to decision ledger.

        Args:
            context: OrchestrationContext with all module results
            expected_profit: Expected profit from strategy
            expected_roic: Expected ROIC from strategy
            expected_holding_days: Expected holding period
            reasoning: Explanation of recommendation
            data_snapshot: Complete data input snapshot

        Returns:
            recommendation_id of recorded entry, or None if not recorded
        """
        if not context.recommendation_id:
            return None

        # Track which modules were consulted (influenced the decision)
        modules_consulted = [result.module_name for result in context.module_results]

        # Extract key confidence measures from modules
        identity_conf = None
        data_quality_conf = None
        valuation_conf = None
        liquidity_conf = None
        risk_conf = None
        return_conf = None

        for result in context.module_results:
            if result.confidence_identity is not None:
                identity_conf = result.confidence_identity
            if result.confidence_data_quality is not None:
                data_quality_conf = result.confidence_data_quality
            if result.confidence_valuation is not None:
                valuation_conf = result.confidence_valuation
            if result.confidence_liquidity is not None:
                liquidity_conf = result.confidence_liquidity
            if result.confidence_risk is not None:
                risk_conf = result.confidence_risk
            if result.confidence_return is not None:
                return_conf = result.confidence_return

        # Create ledger entry
        entry = DecisionLedgerEntry(
            recommendation_id=context.recommendation_id,
            card_id=context.card_id,
            timestamp=context.timestamp,
            modules_consulted=modules_consulted,
            data_snapshot=data_snapshot or {},
            module_outputs=[r.to_dict() for r in context.module_results],
            confidence_identity=identity_conf,
            confidence_data_quality=data_quality_conf,
            confidence_valuation=valuation_conf,
            confidence_liquidity=liquidity_conf,
            confidence_risk=risk_conf,
            confidence_return=return_conf,
            strategy=context.strategy_name,
            recommendation=context.recommendation,
            expected_profit=expected_profit,
            expected_roic=expected_roic,
            expected_holding_days=expected_holding_days,
            reasoning=reasoning,
            status="pending",
            metadata={
                "run_id": context.run_id,
                "mode": context.mode,
            },
        )

        # Record to ledger
        self.ledger.record(entry)
        return context.recommendation_id

    def get_ledger_summary(self) -> str:
        """Get summary of recorded decisions."""
        return self.ledger.summary()

    def get_accuracy_analysis(self) -> dict:
        """Get prediction accuracy for decisions with outcomes."""
        return self.ledger.get_accuracy_stats()

    def export_decisions(self) -> list[dict]:
        """Export all recorded decisions as dicts."""
        return self.ledger.export()
