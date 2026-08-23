from __future__ import annotations

from typing import Any

from phasenox.audio.mix.models import MixIntelligenceResult
from phasenox.audio.plugin.models import PluginIntelligenceResult
from phasenox.report.models import SoundBrainReport

from .benchmark import BenchmarkRunner
from .metrics import (
    AnalysisQualityMetrics,
    ConfidenceEvaluationMetrics,
    KnowledgeResolutionMetrics,
    PluginRecommendationMetrics,
    RecommendationConsistencyMetrics,
    ReferenceMatchingMetrics,
)
from .models import BenchmarkCase, BenchmarkResult, EvaluationResult
from .scoring import ScoreAggregator


class EvaluationService:
    """
    Isolated Evaluation layer for NØISYNE outputs.

    The service consumes existing outputs (reports, comparisons, intelligence
    results) and produces scores. It never influences analysis decisions.
    """

    def __init__(
        self,
        knowledge_resolver: Any | None = None,
        memory_resolver: Any | None = None,
        threshold: float = 0.6,
    ) -> None:
        self._knowledge_resolver = knowledge_resolver
        self._memory_resolver = memory_resolver
        self._aggregator = ScoreAggregator(threshold=threshold)
        self._analysis_metrics = AnalysisQualityMetrics()
        self._consistency_metrics = RecommendationConsistencyMetrics()
        self._confidence_metrics = ConfidenceEvaluationMetrics()
        self._reference_metrics = ReferenceMatchingMetrics()
        self._plugin_metrics = PluginRecommendationMetrics()
        self._knowledge_metrics = KnowledgeResolutionMetrics()

    def evaluate_response(
        self,
        response: Any,
        evaluation_id: str | None = None,
    ) -> EvaluationResult:
        """Evaluate a complete NØISYNE analysis response."""
        report = getattr(response, "report", None)
        comparison = getattr(response, "comparison", None)
        mix = getattr(response, "mix_intelligence", None)
        plugin = getattr(response, "plugin_intelligence", None)

        if not isinstance(report, SoundBrainReport):
            raise TypeError("response.report must be a SoundBrainReport")

        return self.evaluate_components(
            report=report,
            comparison=comparison,
            mix_intelligence=mix,
            plugin_intelligence=plugin,
            evaluation_id=evaluation_id or "evaluation-1",
        )

    def evaluate_components(
        self,
        report: SoundBrainReport,
        *,
        comparison: Any | None = None,
        mix_intelligence: MixIntelligenceResult | None = None,
        plugin_intelligence: PluginIntelligenceResult | None = None,
        evaluation_id: str = "evaluation-1",
    ) -> EvaluationResult:
        """Evaluate individual components without requiring a response object."""
        metrics = [
            self._analysis_metrics.evaluate(report),
            self._consistency_metrics.evaluate(report),
            self._confidence_metrics.evaluate(report, mix_intelligence, plugin_intelligence),
            self._reference_metrics.evaluate(comparison),
            self._plugin_metrics.evaluate(plugin_intelligence),
            self._knowledge_metrics.evaluate(self._knowledge_resolver),
        ]

        notes: list[str] = []
        if self._memory_resolver is not None:
            notes.append("memory resolver available but not evaluated in this sprint")

        return self._aggregator.aggregate(metrics, evaluation_id, notes=notes)

    def benchmark(
        self,
        cases: list[BenchmarkCase],
        benchmark_id: str = "benchmark-1",
    ) -> BenchmarkResult:
        """Run a benchmark over multiple evaluation cases."""
        runner = BenchmarkRunner(evaluator=self, aggregator=self._aggregator)
        return runner.run(cases, benchmark_id=benchmark_id)
