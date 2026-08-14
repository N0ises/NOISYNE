"""SoundBrain deterministic Plugin Intelligence.

The decision logic in this package is category-first and brand-blind.
Concrete plugin products are only read from the registry.
"""

from __future__ import annotations

from .models import (
    ParameterRecommendation,
    PluginCategory,
    PluginIntelligenceResult,
    PluginIntelligenceStep,
    PluginMatch,
    ProcessingGoal,
)
from .service import PluginIntelligenceService

__all__ = [
    "ParameterRecommendation",
    "PluginCategory",
    "PluginIntelligenceResult",
    "PluginIntelligenceService",
    "PluginIntelligenceStep",
    "PluginMatch",
    "ProcessingGoal",
]
