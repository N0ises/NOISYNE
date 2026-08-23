from __future__ import annotations

from dataclasses import dataclass

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.comparison.report_models import ComparisonReport


@dataclass(slots=True)
class ReferenceReasoningContext:
    """
    Context for reference-vs-current reasoning.
    """

    reference: AnalysisResult

    current: AnalysisResult

    comparison: ComparisonReport

    question: str