from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(str, Enum):
    FREQUENCY = "frequency"
    DYNAMICS = "dynamics"
    STEREO = "stereo"
    LOUDNESS = "loudness"
    TRANSIENT = "transient"
    PHASE = "phase"
    TONAL = "tonal"
    CLIPPING = "clipping"
    ARTIFACT = "artifact"
    SEMANTIC = "semantic"


class DecisionType(str, Enum):
    TECHNICAL_ISSUE = "technical_issue"
    STYLISTIC_DIFFERENCE = "stylistic_difference"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(slots=True)
class ReferenceMetric:

    name: str

    reference: float

    current: float

    difference: float

    unit: str

    tolerance: float

    passed: bool

    severity: Severity


@dataclass(slots=True)
class ReferenceIntent:
    """User-provided intent for reference comparison."""

    genre: str | None = None

    mood: str | None = None

    target: str | None = None

    focus_areas: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SegmentDeviation:
    """Time-range where current mix deviates from the reference profile."""

    start_time: float

    end_time: float

    metric: str

    reference_value: float

    current_value: float

    severity: str


@dataclass(slots=True)
class EngineerDecision:

    title: str

    description: str

    category: Category

    severity: Severity

    confidence: float

    recommendation: str

    plugin: str | None = None

    parameters: dict[str, Any] = field(default_factory=dict)

    decision_type: DecisionType = DecisionType.TECHNICAL_ISSUE


@dataclass(slots=True)
class BandDifference:

    band: str

    start_hz: float

    end_hz: float

    reference_energy: float

    current_energy: float

    difference_db: float

    severity: Severity


@dataclass(slots=True)
class ReferenceComparison:

    similarity: float

    confidence: float

    frequency_score: float

    dynamic_score: float

    stereo_score: float

    loudness_score: float

    transient_score: float

    phase_score: float

    tonal_score: float

    semantic_score: float

    band_differences: list[BandDifference]

    engineer_decisions: list[EngineerDecision]

    metrics: list[ReferenceMetric]

    references: list[str] = field(default_factory=list)

    reference_similarities: dict[str, float] = field(default_factory=dict)

    metric_variance: dict[str, float] = field(default_factory=dict)

    segment_deviations: list[SegmentDeviation] = field(default_factory=list)


@dataclass(slots=True)
class ReferenceReport:

    comparison: ReferenceComparison

    summary: str

    strengths: list[str]

    weaknesses: list[str]

    priorities: list[str]

    next_actions: list[str]

    intent: ReferenceIntent | None = None
