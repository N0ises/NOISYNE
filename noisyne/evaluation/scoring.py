from __future__ import annotations

from typing import Any

from .models import EvaluationMetric, EvaluationResult


class ScoreAggregator:
    """Aggregate weighted metrics into a single overall score and pass/fail."""

    def __init__(self, threshold: float = 0.6) -> None:
        self._threshold = threshold

    def aggregate(
        self,
        metrics: list[EvaluationMetric],
        evaluation_id: str,
        notes: list[str] | None = None,
    ) -> EvaluationResult:
        applicable = [m for m in metrics if m.applicable]
        if not applicable:
            return EvaluationResult(
                evaluation_id=evaluation_id,
                metrics=metrics,
                overall_score=0.0,
                passed=False,
                threshold=self._threshold,
                notes=notes or ["no applicable metrics"],
            )

        total_weight = sum(m.weight for m in applicable)
        if total_weight == 0.0:
            overall = 0.0
        else:
            overall = sum(m.score * m.weight for m in applicable) / total_weight

        overall = max(0.0, min(1.0, overall))
        passed = overall >= self._threshold

        return EvaluationResult(
            evaluation_id=evaluation_id,
            metrics=metrics,
            overall_score=overall,
            passed=passed,
            threshold=self._threshold,
            notes=notes or [],
        )

    def aggregate_metric_scores(
        self,
        scores: dict[str, float],
        weights: dict[str, float],
    ) -> float:
        """Utility to aggregate a plain mapping of scores and weights."""
        total_weight = 0.0
        weighted_sum = 0.0
        for name, score in scores.items():
            weight = weights.get(name, 1.0)
            total_weight += weight
            weighted_sum += score * weight
        if total_weight == 0.0:
            return 0.0
        return max(0.0, min(1.0, weighted_sum / total_weight))

    def metric_summary(self, result: EvaluationResult) -> dict[str, Any]:
        """Return a compact summary dict for a result."""
        return {
            "evaluation_id": result.evaluation_id,
            "overall_score": result.overall_score,
            "passed": result.passed,
            "threshold": result.threshold,
            "metric_scores": {m.name: round(m.score, 4) for m in result.metrics if m.applicable},
            "skipped_metrics": [m.name for m in result.metrics if not m.applicable],
            "notes": result.notes,
        }
