"""Orchestration layer for coordinating independent modules.

Coordinates composition of strategy, guardrails, analysis, and learning modules
without replacing their business logic. Enables testing, validation, and learning
feedback without executing trades.
"""

from .shadow_mode import (
    OrchestrationContext,
    ShadowModeOrchestrator,
)

__all__ = [
    "OrchestrationContext",
    "ShadowModeOrchestrator",
]
