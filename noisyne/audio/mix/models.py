from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RootCause:
    """Root cause explanation for a detected mix issue."""

    symptom: str
    likely_causes: list[str]
    priority: str
    confidence: float


@dataclass(slots=True)
class RootCauseResult:
    """Collection of root causes and aggregate confidence scores."""

    causes: list[RootCause] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class PrioritizedIssue:
    """Engineering issue ranked for user action."""

    title: str
    severity: str
    priority_score: float
    user_action_order: int
    category: str
    description: str
    recommendation: str
    confidence: float


@dataclass(slots=True)
class ProcessingStep:
    """Non-destructive processing recommendation in the mix chain."""

    order: int
    target: str
    plugin_type: str
    suggestion: str
    estimated_impact: str
    confidence: float


@dataclass(slots=True)
class MixIntelligenceResult:
    """All deterministic Mix Intelligence outputs for a single analysis."""

    root_causes: list[RootCause] = field(default_factory=list)
    prioritized_issues: list[PrioritizedIssue] = field(default_factory=list)
    processing_chain: list[ProcessingStep] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)
