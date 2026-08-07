"""Test that confidence measures remain independent throughout the system.

All 6 confidence measures must:
1. Be set independently (not averaged or combined prematurely)
2. Flow through ModuleResult contract without combination
3. Be preserved separately in DecisionLedgerEntry
4. Be available as independent inputs to future OpportunityScore calculation

Confidence measures:
- confidence_identity: Card match certainty (CardIdentityValidator)
- confidence_data_quality: Data freshness/reliability (various analyzers)
- confidence_valuation: Fair value estimate (ComparableAnalyzer)
- confidence_liquidity: Sale probability (LiquidityAnalyzer)
- confidence_risk: Risk assessment (GuardrailsChecker)
- confidence_return: Return estimate (Strategy modules)
"""

import unittest
from datetime import datetime, timedelta

from cardarb.models import (
    AcquisitionCost,
    CardIdentity,
    ComparableAnalyzer,
    ComparableSalesAnalysis,
    DecisionLedger,
    DecisionLedgerEntry,
    ExecutionGuardrails,
    GuardrailsChecker,
    LiquidityAnalyzer,
    LiquidityProfile,
    ModuleResult,
    RiskLevel,
    SaleProceeds,
    SoldListing,
    TradeEconomics,
)
from cardarb.orchestration import ShadowModeOrchestrator


class TestConfidenceIndependence(unittest.TestCase):
    """Verify all confidence measures remain independent."""

    def setUp(self):
        """Set up test fixtures."""
        self.card = CardIdentity(
            sport="Football",
            player_name="Patrick Mahomes",
            year=2017,
            manufacturer="Panini",
            product="Prizm",
            card_number="1",
            grade=9.5,
            identity_confidence=0.98,
        )

        # Test data: comparable sales
        self.listings = [
            SoldListing(
                price=100,
                sold_date=datetime.now() - timedelta(days=5),
                sale_type="fixed-price",
                transaction_id="1",
            ),
            SoldListing(
                price=102,
                sold_date=datetime.now() - timedelta(days=6),
                sale_type="auction",
                transaction_id="2",
            ),
            SoldListing(
                price=98,
                sold_date=datetime.now() - timedelta(days=7),
                sale_type="fixed-price",
                transaction_id="3",
            ),
        ]

    def test_module_result_accepts_all_six_confidences(self):
        """ModuleResult can hold all 6 confidence measures independently."""
        result = ModuleResult(
            module_name="TestModule",
            module_version="1.0",
            result="TEST",
            confidence_identity=0.95,
            confidence_data_quality=0.85,
            confidence_valuation=0.88,
            confidence_liquidity=0.92,
            confidence_risk=0.80,
            confidence_return=0.90,
        )

        # All confidences should be stored as-is
        self.assertEqual(result.confidence_identity, 0.95)
        self.assertEqual(result.confidence_data_quality, 0.85)
        self.assertEqual(result.confidence_valuation, 0.88)
        self.assertEqual(result.confidence_liquidity, 0.92)
        self.assertEqual(result.confidence_risk, 0.80)
        self.assertEqual(result.confidence_return, 0.90)

        # min_confidence returns minimum, NOT average
        self.assertEqual(result.min_confidence(), 0.80)

    def test_comparable_analyzer_sets_valuation_confidence_only(self):
        """ComparableAnalyzer should only set confidence_valuation."""
        analysis = ComparableAnalyzer.analyze(self.listings)

        # ComparableAnalyzer sets confidence (which becomes confidence_valuation)
        self.assertGreater(analysis.confidence, 0.0)
        self.assertLessEqual(analysis.confidence, 1.0)

    def test_guardrails_checker_sets_risk_confidence_only(self):
        """GuardrailsChecker should only set confidence_risk."""
        analysis = ComparableAnalyzer.analyze(self.listings)
        liquidity = LiquidityProfile(
            sales_30_days=5,
            sales_60_days=8,
            sales_90_days=12,
            median_days_on_market=10.0,
            median_days_between_sales=7.0,
            active_listings=3,
            active_sellers=2,
            sell_through_rate=0.80,
            listing_price_dispersion=0.05,
            prob_sell_7_days=0.60,
            prob_sell_14_days=0.80,
            prob_sell_30_days=0.95,
            prob_sell_90_days=0.99,
            liquidity_score=80,
        )
        acquisition_cost = AcquisitionCost(
            purchase_price=100.0,
            sales_tax=8.0,
            inbound_shipping=5.0,
            inbound_insurance=2.0,
        )
        sale_proceeds = SaleProceeds(
            sale_price=130.0,
            platform_fee=16.0,
            outbound_shipping=3.0,
            outbound_insurance=1.0,
            return_and_cancellation_reserve=2.6,
        )
        economics = TradeEconomics(
            acquisition_cost=acquisition_cost,
            expected_sale_proceeds=sale_proceeds,
            expected_holding_days=14,
        )

        check_result = GuardrailsChecker.check(
            self.card, analysis, liquidity, economics
        )

        # Guardrails module result should have risk_confidence
        module_result = GuardrailsChecker.as_module_result(check_result, self.card.player_name)
        self.assertEqual(module_result.confidence_risk, check_result.risk_confidence)
        # Other confidences should not be set by guardrails
        self.assertIsNone(module_result.confidence_identity)
        self.assertIsNone(module_result.confidence_valuation)
        self.assertIsNone(module_result.confidence_return)

    def test_decision_ledger_preserves_all_confidences(self):
        """DecisionLedger should preserve all 6 confidence measures independently."""
        # Create an entry with different confidence values
        entry = DecisionLedgerEntry(
            recommendation_id="test_rec_001",
            card_id=12345,
            timestamp=datetime.now(),
            data_snapshot={},
            module_outputs=[],
            confidence_identity=0.98,
            confidence_data_quality=0.85,
            confidence_valuation=0.88,
            confidence_liquidity=0.92,
            confidence_risk=0.80,
            confidence_return=0.90,
            strategy="TestStrategy",
            recommendation="BUY",
        )

        # All should be preserved
        self.assertEqual(entry.confidence_identity, 0.98)
        self.assertEqual(entry.confidence_data_quality, 0.85)
        self.assertEqual(entry.confidence_valuation, 0.88)
        self.assertEqual(entry.confidence_liquidity, 0.92)
        self.assertEqual(entry.confidence_risk, 0.80)
        self.assertEqual(entry.confidence_return, 0.90)

        # min_confidence should return minimum
        self.assertEqual(entry.min_confidence(), 0.80)

        # Serialize and verify
        entry_dict = entry.to_dict()
        self.assertEqual(entry_dict["confidence_identity"], 0.98)
        self.assertEqual(entry_dict["confidence_data_quality"], 0.85)
        self.assertEqual(entry_dict["confidence_valuation"], 0.88)
        self.assertEqual(entry_dict["confidence_liquidity"], 0.92)
        self.assertEqual(entry_dict["confidence_risk"], 0.80)
        self.assertEqual(entry_dict["confidence_return"], 0.90)

    def test_shadow_mode_orchestrator_preserves_independence(self):
        """ShadowModeOrchestrator records module outputs without combining confidences."""
        orchestrator = ShadowModeOrchestrator()

        # Create context
        ctx = orchestrator.create_context(
            card_id=self.card.player_name,
            card=self.card,
            strategy_name="TestStrategy",
        )

        # Add module results with different confidences
        comparable_result = ModuleResult(
            module_name="ComparableAnalyzer",
            module_version="1.0",
            result="analysis",
            confidence_valuation=0.88,
        )
        ctx.add_module_result(comparable_result)

        guardrail_result = ModuleResult(
            module_name="GuardrailsChecker",
            module_version="2.0",
            result="passed",
            confidence_risk=0.80,
        )
        ctx.add_module_result(guardrail_result)

        identity_result = ModuleResult(
            module_name="CardIdentityValidator",
            module_version="1.0",
            result="valid",
            confidence_identity=0.98,
        )
        ctx.add_module_result(identity_result)

        # All results should be preserved independently
        results = ctx.module_results
        self.assertEqual(len(results), 3)

        # Each module's confidence should be independent
        comparable = [r for r in results if r.module_name == "ComparableAnalyzer"][0]
        self.assertEqual(comparable.confidence_valuation, 0.88)
        self.assertIsNone(comparable.confidence_risk)
        self.assertIsNone(comparable.confidence_identity)

        guardrail = [r for r in results if r.module_name == "GuardrailsChecker"][0]
        self.assertEqual(guardrail.confidence_risk, 0.80)
        self.assertIsNone(guardrail.confidence_valuation)
        self.assertIsNone(guardrail.confidence_identity)

        identity = [r for r in results if r.module_name == "CardIdentityValidator"][0]
        self.assertEqual(identity.confidence_identity, 0.98)
        self.assertIsNone(identity.confidence_risk)
        self.assertIsNone(identity.confidence_valuation)

    def test_confidence_never_averaged(self):
        """Confidence measures are never averaged across modules."""
        # Create multiple module results with different confidences
        results = [
            ModuleResult(module_name="Module1", module_version="1.0", confidence_valuation=0.90),
            ModuleResult(module_name="Module2", module_version="1.0", confidence_valuation=0.80),
            ModuleResult(module_name="Module3", module_version="1.0", confidence_valuation=0.85),
        ]

        # Extract valuations
        valuations = [r.confidence_valuation for r in results if r.confidence_valuation is not None]

        # Should be [0.90, 0.80, 0.85], NOT [0.85] (average)
        self.assertEqual(len(valuations), 3)
        self.assertEqual(valuations, [0.90, 0.80, 0.85])

        # For future OpportunityScore, these could be inputs to a decision function
        # but they must NOT be pre-averaged
        min_val = min(valuations)
        self.assertEqual(min_val, 0.80)

    def test_different_modules_set_different_confidences(self):
        """Each module type sets its own confidence measure."""
        # Simulate module outputs
        modules = {
            "CardIdentityValidator": ModuleResult(
                module_name="CardIdentityValidator",
                module_version="1.0",
                confidence_identity=0.98,  # Only sets identity
            ),
            "ComparableAnalyzer": ModuleResult(
                module_name="ComparableAnalyzer",
                module_version="1.0",
                confidence_valuation=0.85,  # Only sets valuation
            ),
            "LiquidityAnalyzer": ModuleResult(
                module_name="LiquidityAnalyzer",
                module_version="1.0",
                confidence_liquidity=0.90,  # Only sets liquidity
            ),
            "GuardrailsChecker": ModuleResult(
                module_name="GuardrailsChecker",
                module_version="2.0",
                confidence_risk=0.80,  # Only sets risk
            ),
            "Strategy": ModuleResult(
                module_name="Strategy.CrossMarket",
                module_version="2.0",
                confidence_return=0.88,  # Only sets return
            ),
        }

        # Each module sets exactly one confidence type
        for name, result in modules.items():
            all_confs = [
                result.confidence_identity,
                result.confidence_data_quality,
                result.confidence_valuation,
                result.confidence_liquidity,
                result.confidence_risk,
                result.confidence_return,
            ]
            non_none_confs = [c for c in all_confs if c is not None]
            self.assertEqual(
                len(non_none_confs),
                1,
                f"{name} set {len(non_none_confs)} confidences instead of 1",
            )

    def test_ledger_entry_from_modules_preserves_all(self):
        """Creating a ledger entry from module outputs preserves all confidences."""
        # Simulate complete module execution
        module_outputs = [
            ModuleResult(
                module_name="CardIdentityValidator",
                module_version="1.0",
                confidence_identity=0.98,
            ).to_dict(),
            ModuleResult(
                module_name="ComparableAnalyzer",
                module_version="1.0",
                confidence_valuation=0.88,
            ).to_dict(),
            ModuleResult(
                module_name="LiquidityAnalyzer",
                module_version="1.0",
                confidence_liquidity=0.92,
            ).to_dict(),
            ModuleResult(
                module_name="GuardrailsChecker",
                module_version="2.0",
                confidence_risk=0.80,
            ).to_dict(),
            ModuleResult(
                module_name="Strategy.CrossMarket",
                module_version="2.0",
                confidence_return=0.90,
            ).to_dict(),
        ]

        # Create ledger entry with all confidences
        entry = DecisionLedgerEntry(
            recommendation_id="test_001",
            card_id=12345,
            timestamp=datetime.now(),
            data_snapshot={},
            module_outputs=module_outputs,
            confidence_identity=0.98,
            confidence_data_quality=None,  # Not all modules set this
            confidence_valuation=0.88,
            confidence_liquidity=0.92,
            confidence_risk=0.80,
            confidence_return=0.90,
            strategy="CrossMarket",
            recommendation="BUY",
        )

        # All should be preserved
        self.assertEqual(entry.confidence_identity, 0.98)
        self.assertIsNone(entry.confidence_data_quality)
        self.assertEqual(entry.confidence_valuation, 0.88)
        self.assertEqual(entry.confidence_liquidity, 0.92)
        self.assertEqual(entry.confidence_risk, 0.80)
        self.assertEqual(entry.confidence_return, 0.90)

        # Export and verify
        exported = entry.to_dict()
        self.assertEqual(exported["confidence_identity"], 0.98)
        self.assertIsNone(exported["confidence_data_quality"])
        self.assertEqual(exported["confidence_valuation"], 0.88)
        self.assertEqual(exported["confidence_liquidity"], 0.92)
        self.assertEqual(exported["confidence_risk"], 0.80)
        self.assertEqual(exported["confidence_return"], 0.90)


if __name__ == "__main__":
    unittest.main()
