from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EvaluationMetric:
    """One named, weighted metric scored between 0.0 and 1.0."""

    name: str
    score: float
    weight: float
    applicable: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Result of evaluating a single SoundBrain output."""

    evaluation_id: str
    metrics: list[EvaluationMetric]
    overall_score: float
    passed: bool
    threshold: float = 0.6
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """A single case for benchmark evaluation."""

    case_id: str
    response: Any
    expected: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Aggregated results over multiple benchmark cases."""

    benchmark_id: str
    evaluations: list[EvaluationResult]
    aggregated_scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    passed: bool = False
    notes: list[str] = field(default_factory=list)
