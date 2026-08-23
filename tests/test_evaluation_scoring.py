from __future__ import annotations

from phasenox.evaluation.models import EvaluationMetric
from phasenox.evaluation.scoring import ScoreAggregator


def test_aggregator_computes_weighted_average() -> None:
    aggregator = ScoreAggregator(threshold=0.6)
    metrics = [
        EvaluationMetric(name="a", score=1.0, weight=1.0),
        EvaluationMetric(name="b", score=0.0, weight=1.0),
    ]
    result = aggregator.aggregate(metrics, evaluation_id="e1")

    assert result.overall_score == 0.5
    assert not result.passed


def test_aggregator_ignores_non_applicable_metrics() -> None:
    aggregator = ScoreAggregator(threshold=0.6)
    metrics = [
        EvaluationMetric(name="a", score=1.0, weight=1.0, applicable=True),
        EvaluationMetric(name="b", score=0.0, weight=1.0, applicable=False),
    ]
    result = aggregator.aggregate(metrics, evaluation_id="e2")

    assert result.overall_score == 1.0
    assert result.passed


def test_aggregator_returns_zero_when_no_applicable_metrics() -> None:
    aggregator = ScoreAggregator(threshold=0.6)
    metrics = [
        EvaluationMetric(name="a", score=1.0, weight=1.0, applicable=False),
    ]
    result = aggregator.aggregate(metrics, evaluation_id="e3")

    assert result.overall_score == 0.0
    assert not result.passed


def test_aggregator_summary() -> None:
    aggregator = ScoreAggregator(threshold=0.6)
    metrics = [
        EvaluationMetric(name="a", score=1.0, weight=1.0),
        EvaluationMetric(name="b", score=0.5, weight=1.0),
    ]
    result = aggregator.aggregate(metrics, evaluation_id="e4")
    summary = aggregator.metric_summary(result)

    assert summary["evaluation_id"] == "e4"
    assert summary["overall_score"] == 0.75
    assert summary["metric_scores"]["a"] == 1.0
    assert summary["metric_scores"]["b"] == 0.5
    assert summary["skipped_metrics"] == []
