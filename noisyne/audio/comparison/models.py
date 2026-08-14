from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MetricDifference:

    name: str

    reference: float

    current: float

    difference: float

    percent: float


@dataclass(slots=True)
class ComparisonResult:

    score: float

    metrics: list[MetricDifference] = field(default_factory=list)

    recommendations: list[str] = field(default_factory=list)