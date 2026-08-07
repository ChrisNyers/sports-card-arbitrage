"""V1.1 data models for sports card arbitrage.

Core Models:
- CardIdentity: Canonical card definition with confidence scoring
- DataRecord: Data provenance wrapper for all market data
- SoldListing & ComparableSalesAnalysis: Fair value analysis
- AcquisitionCost & SaleProceeds: Transaction economics
- LiquidityProfile & LiquidityAnalyzer: Market liquidity assessment
- ExecutionGuardrails & GuardrailsChecker: Execution gates
- RecommendationSnapshot & TradeOutcome: Learning feedback loop
"""

from .card_identity import CardIdentity, CardIdentityMatcher
from .comparables import (
    ComparableSalesAnalysis,
    ComparableAnalyzer,
    SoldListing,
)
from .costs import (
    AcquisitionCost,
    SaleProceeds,
    TradeEconomics,
    calculate_acquisition_cost,
    calculate_sale_proceeds,
)
from .data_record import DataRecord, DataSnapshot, DataSource
from .guardrails import (
    ExecutionGuardrails,
    GuardrailCheckResult,
    GuardrailsChecker,
    RiskLevel,
)
from .learning import (
    LearningRecorder,
    RecommendationSnapshot,
    TradeOutcome,
)
from .liquidity import (
    LiquidityAnalyzer,
    LiquidityProfile,
)
from .market_signals import (
    Catalyst,
    CatalystList,
    InventoryTrend,
    MarketSignals,
    NegativeInformation,
    PriceMomentum,
    VolumeProfile,
)
from .module_contract import (
    ModuleResult,
    RecommendationOutcome,
)
from .data_freshness import (
    DataType,
    DataFreshnessPolicy,
    FRESHNESS_POLICIES,
    get_policy,
)
from .decision_ledger import (
    DecisionLedger,
    DecisionLedgerEntry,
)

__all__ = [
    # Card identity
    "CardIdentity",
    "CardIdentityMatcher",
    # Data records
    "DataRecord",
    "DataSnapshot",
    "DataSource",
    # Comparables
    "SoldListing",
    "ComparableSalesAnalysis",
    "ComparableAnalyzer",
    # Economics
    "AcquisitionCost",
    "SaleProceeds",
    "TradeEconomics",
    "calculate_acquisition_cost",
    "calculate_sale_proceeds",
    # Liquidity
    "LiquidityProfile",
    "LiquidityAnalyzer",
    # Guardrails
    "ExecutionGuardrails",
    "GuardrailCheckResult",
    "GuardrailsChecker",
    "RiskLevel",
    # Learning
    "RecommendationSnapshot",
    "TradeOutcome",
    "LearningRecorder",
    # Market signals
    "PriceMomentum",
    "InventoryTrend",
    "Catalyst",
    "CatalystList",
    "NegativeInformation",
    "VolumeProfile",
    "MarketSignals",
    # Module contract & orchestration
    "ModuleResult",
    "RecommendationOutcome",
    "DataType",
    "DataFreshnessPolicy",
    "FRESHNESS_POLICIES",
    "get_policy",
    "DecisionLedger",
    "DecisionLedgerEntry",
]
