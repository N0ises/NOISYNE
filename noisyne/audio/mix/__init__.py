"""SoundBrain deterministic Mix Intelligence.

Heavy exports are loaded lazily via ``__getattr__`` so that importing the
package models does not pull in the heuristic engines at import time.
"""

from __future__ import annotations

from .models import (
    MixIntelligenceResult,
    PrioritizedIssue,
    ProcessingStep,
    RootCause,
    RootCauseResult,
)

__all__ = [
    "ExplanationBuilder",
    "MixIntelligenceResult",
    "PrioritizedIssue",
    "PriorityEngine",
    "ProcessingChainRecommender",
    "ProcessingStep",
    "RootCause",
    "RootCauseAnalyzer",
    "RootCauseResult",
]


def __getattr__(name: str):
    if name == "RootCauseAnalyzer":
        from .root_cause import RootCauseAnalyzer

        return RootCauseAnalyzer
    if name == "PriorityEngine":
        from .priority import PriorityEngine

        return PriorityEngine
    if name == "ProcessingChainRecommender":
        from .chains import ProcessingChainRecommender

        return ProcessingChainRecommender
    if name == "ExplanationBuilder":
        from .explanation import ExplanationBuilder

        return ExplanationBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
