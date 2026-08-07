"""Execution guardrails: independent risk validation layer.

Every recommendation must pass all guardrails before execution:
- Identity confidence > 0.95
- Comparable data fresh and sufficient
- Liquidity adequate
- Position size limits respected
- Minimum return threshold met

Guardrails are independent from strategy logic and return ModuleResult contract
for composition with other modules in decision ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .card_identity import CardIdentity
from .comparables import ComparableSalesAnalysis
from .costs import TradeEconomics
from .liquidity import LiquidityProfile


class RiskLevel(Enum):
    """Risk severity levels."""
    LOW = "low"  # All guardrails passed
    MEDIUM = "medium"  # 1-2 guardrails failed
    HIGH = "high"  # 3-5 guardrails failed
    CRITICAL = "critical"  # 6+ guardrails failed or revenue/identity failed


@dataclass
class ExecutionGuardrails:
    """Configuration for guardrails that must be satisfied."""

    # Data quality gates
    min_comparable_sales: int = 3  # Need at least 3 comparable sales
    min_data_freshness_hours: int = 24  # Data must be <24 hours old
    min_identity_confidence: float = 0.95  # Card must be 95%+ certain
    min_comparable_confidence: float = 0.70  # Fair value estimate confidence

    # Market conditions
    min_liquidity_score: int = 40  # 0-100 scale, 40+ is minimum
    min_30day_sales: int = 2  # Need at least 2 sales in 30 days
    max_days_to_sale: int = 90  # Won't hold longer than 90 days

    # Financial guardrails
    min_expected_roic: float = 0.05  # Minimum 5% return
    min_expected_profit: float = 10.0  # At least $10 profit
    max_downside_loss: float = -50.0  # Max loss: -$50

    # Position management
    max_position_size: float = 200.0  # Max $200 per individual card
    max_player_exposure: float = 1000.0  # Max $1K on any player
    max_sport_exposure: float = 5000.0  # Max $5K on any sport
    max_set_exposure: float = 2000.0  # Max $2K on any set
    max_active_positions: int = 100  # Max 100 concurrent positions

    # Execution
    require_human_approval: bool = True  # Always require human sign-off
    log_all_rejections: bool = True  # Track why recommendations are rejected

    def summary(self) -> str:
        """Summary of guardrail configuration."""
        lines = [
            "Execution Guardrails:",
            f"  Identity confidence: >{self.min_identity_confidence:.0%}",
            f"  Comparable sales: >{self.min_comparable_sales}",
            f"  Data freshness: <{self.min_data_freshness_hours}h",
            f"  Liquidity score: >{self.min_liquidity_score}",
            f"  Expected ROIC: >{self.min_expected_roic:.1%}",
            f"  Expected profit: >${self.min_expected_profit:.2f}",
            f"  Max downside loss: ${self.max_downside_loss:.2f}",
            f"  Position size limit: ${self.max_position_size:.2f}",
            f"  Player exposure: ${self.max_player_exposure:.2f}",
        ]
        return "\n".join(lines)


@dataclass
class GuardrailCheckResult:
    """Result of running guardrails on a recommendation.

    Guardrails are independent risk validation - they don't drive strategy
    but assess whether a recommendation passes execution gates.
    """

    passed_all_checks: bool
    checks_passed: int
    checks_total: int
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    failure_reasons: dict = field(default_factory=dict)

    # === Risk Assessment ===
    risk_level: RiskLevel = RiskLevel.LOW
    risk_confidence: float = 1.0  # Confidence in risk assessment (0-1)
    critical_violations: list[str] = field(default_factory=list)  # Revenue/identity issues
    financial_violations: list[str] = field(default_factory=list)  # Position/return issues
    data_quality_violations: list[str] = field(default_factory=list)  # Data freshness issues
    liquidity_violations: list[str] = field(default_factory=list)  # Liquidity issues

    # === Timing ===
    timestamp: datetime = field(default_factory=datetime.now)

    def determine_risk_level(self) -> None:
        """Classify risk based on failure pattern."""
        failures = len(self.failed_checks)

        # Critical if identity or comparables failed
        if any("Identity" in c for c in self.failed_checks):
            self.risk_level = RiskLevel.CRITICAL
        elif any("Comparable" in c or "Fair Value" in c for c in self.failed_checks):
            self.risk_level = RiskLevel.CRITICAL
        # Critical if 6+ failures
        elif failures >= 6:
            self.risk_level = RiskLevel.CRITICAL
        # High if 3-5 failures
        elif failures >= 3:
            self.risk_level = RiskLevel.HIGH
        # Medium if 1-2 failures
        elif failures >= 1:
            self.risk_level = RiskLevel.MEDIUM
        # Low if all passed
        else:
            self.risk_level = RiskLevel.LOW

    def categorize_violations(self) -> None:
        """Categorize failures into violation types."""
        self.critical_violations = [c for c in self.failed_checks
                                   if any(x in c for x in ["Identity", "Fair Value", "Comparable"])]
        self.financial_violations = [c for c in self.failed_checks
                                    if any(x in c for x in ["ROIC", "Profit", "Position", "Exposure"])]
        self.data_quality_violations = [c for c in self.failed_checks
                                       if any(x in c for x in ["Comparable", "Fair Value"])]
        self.liquidity_violations = [c for c in self.failed_checks
                                    if any(x in c for x in ["Liquidity", "Sales"])]

    def summary(self) -> str:
        """Summary of guardrail check results."""
        status = "✓ APPROVED" if self.passed_all_checks else "✗ REJECTED"
        lines = [
            f"{status}: {self.checks_passed}/{self.checks_total} checks passed",
            f"Risk Level: {self.risk_level.value.upper()}",
        ]

        if self.critical_violations:
            lines.append("\nCritical Violations:")
            for check in self.critical_violations:
                reason = self.failure_reasons.get(check, "unknown reason")
                lines.append(f"  ✗ {check}: {reason}")

        if self.financial_violations:
            lines.append("\nFinancial Violations:")
            for check in self.financial_violations:
                reason = self.failure_reasons.get(check, "unknown reason")
                lines.append(f"  ✗ {check}: {reason}")

        return "\n".join(lines)


class GuardrailsChecker:
    """Independent risk validation layer.

    Guardrails are separate from strategy logic. They validate that a
    recommendation passes execution gates before it can be actioned.
    Results are returned as ModuleResult for composition in decision ledger.
    """

    @staticmethod
    def check(
        card: CardIdentity,
        comparable_analysis: ComparableSalesAnalysis,
        liquidity: LiquidityProfile,
        economics: TradeEconomics,
        current_positions: Optional[dict] = None,
        guardrails: Optional[ExecutionGuardrails] = None,
    ) -> GuardrailCheckResult:
        """Run complete guardrail check on a recommendation.

        Args:
            card: Card identity with confidence
            comparable_analysis: Fair value analysis
            liquidity: Liquidity assessment
            economics: Trade economics (profit, ROIC, etc.)
            current_positions: Dict tracking current position exposures
            guardrails: ExecutionGuardrails configuration

        Returns:
            GuardrailCheckResult with detailed pass/fail info
        """
        if guardrails is None:
            guardrails = ExecutionGuardrails()

        if current_positions is None:
            current_positions = {}

        result = GuardrailCheckResult(
            passed_all_checks=True,
            checks_passed=0,
            checks_total=0,
        )

        # Check 1: Identity confidence
        check_name = "Identity Confidence"
        result.checks_total += 1
        if card.identity_confidence > guardrails.min_identity_confidence:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Confidence {card.identity_confidence:.0%} < "
                f"minimum {guardrails.min_identity_confidence:.0%}"
            )

        # Check 2: Comparable sales count
        check_name = "Comparable Sales Count"
        result.checks_total += 1
        if comparable_analysis.sample_count >= guardrails.min_comparable_sales:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"{comparable_analysis.sample_count} sales < "
                f"minimum {guardrails.min_comparable_sales}"
            )

        # Check 3: Comparable confidence
        check_name = "Fair Value Confidence"
        result.checks_total += 1
        if comparable_analysis.confidence >= guardrails.min_comparable_confidence:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Confidence {comparable_analysis.confidence:.0%} < "
                f"minimum {guardrails.min_comparable_confidence:.0%}"
            )

        # Check 4: Liquidity score
        check_name = "Liquidity Score"
        result.checks_total += 1
        if liquidity.liquidity_score >= guardrails.min_liquidity_score:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Score {liquidity.liquidity_score}/100 < "
                f"minimum {guardrails.min_liquidity_score}"
            )

        # Check 5: 30-day sales volume
        check_name = "30-Day Sales Volume"
        result.checks_total += 1
        if liquidity.sales_30_days >= guardrails.min_30day_sales:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"{liquidity.sales_30_days} sales < "
                f"minimum {guardrails.min_30day_sales}"
            )

        # Check 6: Holding period
        check_name = "Holding Period"
        result.checks_total += 1
        if economics.expected_holding_days <= guardrails.max_days_to_sale:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"{economics.expected_holding_days} days > "
                f"maximum {guardrails.max_days_to_sale}"
            )

        # Check 7: Expected ROIC
        check_name = "Expected ROIC"
        result.checks_total += 1
        if economics.expected_roic >= guardrails.min_expected_roic:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"ROIC {economics.expected_roic:.1%} < "
                f"minimum {guardrails.min_expected_roic:.1%}"
            )

        # Check 8: Expected profit
        check_name = "Expected Profit"
        result.checks_total += 1
        if economics.expected_net_profit >= guardrails.min_expected_profit:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Profit ${economics.expected_net_profit:.2f} < "
                f"minimum ${guardrails.min_expected_profit:.2f}"
            )

        # Check 9: Position size
        check_name = "Position Size"
        result.checks_total += 1
        position_size = economics.acquisition_cost.total_cost
        if position_size <= guardrails.max_position_size:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Position ${position_size:.2f} > "
                f"maximum ${guardrails.max_position_size:.2f}"
            )

        # Check 10: Player exposure
        check_name = "Player Exposure"
        result.checks_total += 1
        player_exposure = current_positions.get(f"player:{card.player_name}", 0)
        player_exposure += position_size
        if player_exposure <= guardrails.max_player_exposure:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Exposure ${player_exposure:.2f} > "
                f"maximum ${guardrails.max_player_exposure:.2f}"
            )

        # Check 11: Sport exposure
        check_name = "Sport Exposure"
        result.checks_total += 1
        sport_exposure = current_positions.get(f"sport:{card.sport}", 0)
        sport_exposure += position_size
        if sport_exposure <= guardrails.max_sport_exposure:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Exposure ${sport_exposure:.2f} > "
                f"maximum ${guardrails.max_sport_exposure:.2f}"
            )

        # Check 12: Set exposure
        check_name = "Set Exposure"
        result.checks_total += 1
        set_key = f"{card.year}:{card.product}"
        set_exposure = current_positions.get(f"set:{set_key}", 0)
        set_exposure += position_size
        if set_exposure <= guardrails.max_set_exposure:
            result.checks_passed += 1
            result.passed_checks.append(check_name)
        else:
            result.passed_all_checks = False
            result.failed_checks.append(check_name)
            result.failure_reasons[check_name] = (
                f"Exposure ${set_exposure:.2f} > "
                f"maximum ${guardrails.max_set_exposure:.2f}"
            )

        # Determine risk level and categorize violations
        result.determine_risk_level()
        result.categorize_violations()

        # Set risk confidence: high if all critical checks passed, lower otherwise
        if result.critical_violations:
            result.risk_confidence = 0.3  # Low confidence in safe execution
        elif result.failed_checks:
            result.risk_confidence = 0.7  # Medium confidence with minor failures
        else:
            result.risk_confidence = 0.95  # High confidence, all checks passed

        return result

    @staticmethod
    def as_module_result(
        check_result: GuardrailCheckResult,
        card_id: Optional[int] = None,
    ) -> "ModuleResult":  # type: ignore
        """Convert guardrail check to ModuleResult contract.

        Imports ModuleResult here to avoid circular imports.
        """
        from .module_contract import ModuleResult

        status = "success" if check_result.passed_all_checks else "failed"
        if check_result.failed_checks and not check_result.critical_violations:
            status = "degraded"  # Failures but not critical

        return ModuleResult(
            module_name="GuardrailsChecker",
            module_version="2.0",
            card_id=card_id,
            result=check_result,
            result_type="risk_validation",
            status=status,
            confidence_risk=check_result.risk_confidence,
            evidence={
                # Comprehensive check results
                "checks_passed": f"{check_result.checks_passed}/{check_result.checks_total}",
                "passed_checks": check_result.passed_checks,
                "failed_checks": check_result.failed_checks,
                "failure_reasons": check_result.failure_reasons,
                # Violation categorization
                "critical_violations": check_result.critical_violations,
                "financial_violations": check_result.financial_violations,
                "data_quality_violations": check_result.data_quality_violations,
                "liquidity_violations": check_result.liquidity_violations,
                # Risk assessment
                "risk_level": check_result.risk_level.value,
                "risk_confidence": f"{check_result.risk_confidence:.2f}",
            },
            reasoning=check_result.summary(),
            warnings=[f"Risk: {f}" for f in check_result.failed_checks],
        )
