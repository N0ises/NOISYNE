"""PHASENOX reference comparison package.

Heavy exports are loaded lazily via ``__getattr__`` so that importing
``phasenox.reference.models`` does not pull in the full engine stack at import time.
"""

from __future__ import annotations

from .models import (
    BandDifference,
    Category,
    EngineerDecision,
    ReferenceComparison,
    ReferenceMetric,
    ReferenceReport,
    Severity,
)

__all__ = [
    "BandDifference",
    "Category",
    "EngineerDecision",
    "ReferenceComparison",
    "ReferenceMetric",
    "ReferenceReport",
    "Severity",
]


def __getattr__(name: str):
    if name == "ReferenceEngine":
        from .engine import ReferenceEngine

        return ReferenceEngine
    if name == "ReferencePipeline":
        from .pipeline import ReferencePipeline

        return ReferencePipeline
    if name == "ReferenceReasoner":
        from .reasoner import ReferenceReasoner

        return ReferenceReasoner
    if name == "ReferenceReportBuilder":
        from .report_builder import ReferenceReportBuilder

        return ReferenceReportBuilder
    if name == "ReferenceService":
        from .service import ReferenceService

        return ReferenceService
    if name == "ReferenceComparator":
        from .comparator import ReferenceComparator

        return ReferenceComparator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return __all__ + [
        "ReferenceEngine",
        "ReferencePipeline",
        "ReferenceReasoner",
        "ReferenceReportBuilder",
        "ReferenceService",
        "ReferenceComparator",
    ]
