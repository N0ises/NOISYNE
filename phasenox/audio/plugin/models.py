from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProcessingGoal:
    """What the processing chain should achieve for a detected root cause."""

    id: str
    description: str
    target: str
    root_cause: str | None
    action: str
    confidence: float


@dataclass(slots=True)
class PluginCategory:
    """Taxonomy entry for a plugin category."""

    name: str
    family: str


@dataclass(slots=True)
class ParameterRecommendation:
    """Suggested parameter value for a plugin category."""

    name: str
    value: Any
    unit: str | None = None
    range_min: float | None = None
    range_max: float | None = None
    confidence: float = 0.85
    reason: str = ""


@dataclass(slots=True)
class PluginMatch:
    """A concrete plugin product from the registry. Decision logic must be blind to brand."""

    brand: str
    name: str
    formats: list[str] = field(default_factory=list)
    category: str = ""
    identifier: str | None = None


@dataclass(slots=True)
class PluginIntelligenceStep:
    """One enriched step in the plugin-aware processing chain."""

    order: int
    goal: ProcessingGoal
    plugin_category: str
    plugin_type: str
    parameter_recommendations: list[ParameterRecommendation] = field(default_factory=list)
    plugin_options: list[PluginMatch] = field(default_factory=list)
    suggestion: str = ""
    estimated_impact: str = "low"
    confidence: float = 0.85


@dataclass(slots=True)
class PluginIntelligenceResult:
    """All deterministic Plugin Intelligence outputs for a single analysis."""

    goals: list[ProcessingGoal] = field(default_factory=list)
    steps: list[PluginIntelligenceStep] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)
    explanations: list[str] = field(default_factory=list)
