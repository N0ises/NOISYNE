from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import BenchmarkCase, BenchmarkResult, EvaluationResult
from .scoring import ScoreAggregator


@dataclass(frozen=True, slots=True)
class BenchmarkRunner:
    """Run evaluation over a collection of benchmark cases."""

    evaluator: Any
    aggregator: ScoreAggregator = field(default_factory=ScoreAggregator)

    def run(
        self,
        cases: list[BenchmarkCase],
        benchmark_id: str = "benchmark-1",
    ) -> BenchmarkResult:
        evaluations: list[EvaluationResult] = []
        for case in cases:
            result = self.evaluator.evaluate_response(
                case.response,
                evaluation_id=case.case_id,
            )
            evaluations.append(result)

        aggregated_scores: dict[str, list[float]] = {}
        for result in evaluations:
            for metric in result.metrics:
                if metric.applicable:
                    aggregated_scores.setdefault(metric.name, []).append(metric.score)

        averaged_scores: dict[str, float] = {}
        for name, scores in aggregated_scores.items():
            averaged_scores[name] = sum(scores) / len(scores)

        overall = 0.0
        if averaged_scores:
            overall = sum(averaged_scores.values()) / len(averaged_scores)
        overall = max(0.0, min(1.0, overall))

        passed = all(result.passed for result in evaluations) and overall >= 0.6

        return BenchmarkResult(
            benchmark_id=benchmark_id,
            evaluations=evaluations,
            aggregated_scores=averaged_scores,
            overall_score=overall,
            passed=passed,
            notes=[
                f"evaluated {len(cases)} case(s)",
                f"passed cases: {sum(1 for r in evaluations if r.passed)}/{len(evaluations)}",
            ],
        )
