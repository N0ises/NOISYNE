from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MixRules:
    """Thresholds and acceptance ranges for full-mix evaluation."""

    lufs_range: tuple[float, float]
    dynamic_range_min: float
    peak_max: float
    phase_high_threshold: float
    phase_low_threshold: float
    stereo_width_min: float


@dataclass(frozen=True, slots=True)
class StemRules:
    """Thresholds and acceptance ranges for isolated stem evaluation."""

    dynamic_range_min: float
    peak_max: float


@dataclass(frozen=True, slots=True)
class EngineeringRuleBase:
    """All engineering thresholds, weights, and confidence defaults."""

    mix: MixRules
    stem: StemRules
    severity_weights: dict[str, float]
    category_order: dict[str, float]
    confidence_defaults: dict[str, float]


@dataclass(frozen=True, slots=True)
class GenreProfile:
    """Engineering expectations for a musical genre."""

    name: str
    description: str = ""
    expected_spectral_centroid_range: tuple[float, float] | None = None
    expected_dynamic_range_min: float | None = None
    typical_stereo_width_min: float | None = None
    target_loudness_by_platform: dict[str, float] = field(default_factory=dict)
    common_issues: list[str] = field(default_factory=list)
    common_chain: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PlatformProfile:
    """Delivery target loudness and format requirements."""

    name: str
    target_lufs: float
    true_peak_max: float = -1.0
    format_requirements: list[str] = field(default_factory=list)
    loudness_standard: str = ""
    recommended_dynamic_range_min: float | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """Default value and valid range for a plugin parameter."""

    range_min: float
    range_max: float
    default: float
    unit: str | None = None
    step: float | None = None


@dataclass(frozen=True, slots=True)
class PluginCategoryKnowledge:
    """What a plugin category does and how it is typically used."""

    name: str
    family: str = ""
    typical_use: str = ""
    safe_order: int = 0
    parameter_order: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PluginCapabilityKnowledge:
    """Plugin taxonomy, parameter defaults, and target mappings."""

    categories: dict[str, PluginCategoryKnowledge] = field(default_factory=dict)
    parameter_defaults: dict[str, dict[str, ParameterSpec]] = field(default_factory=dict)
    target_to_category: dict[str, str] = field(default_factory=dict)
    category_to_plugin_type: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RootCauseMapping:
    """Mapping from a symptom keyword set to likely causes and priority."""

    symptom_keywords: list[str] = field(default_factory=list)
    likely_causes: list[str] = field(default_factory=list)
    priority: str = "medium"
    confidence: float = 0.80
    required_measurements: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RootCauseKnowledge:
    """Collection of root-cause mappings."""

    mappings: list[RootCauseMapping] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BestPracticeKnowledge:
    """Processing-order and explanation templates."""

    processing_order: list[str] = field(default_factory=list)
    max_chain_steps: int = 6
    explanation_templates: dict[str, str] = field(default_factory=dict)
    safety_checks: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KnowledgeBundle:
    """Complete versioned knowledge bundle for the SoundBrain runtime."""

    version: str
    engineering: EngineeringRuleBase
    genres: dict[str, GenreProfile]
    platforms: dict[str, PlatformProfile]
    plugin_capabilities: PluginCapabilityKnowledge
    root_causes: RootCauseKnowledge
    best_practices: BestPracticeKnowledge

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dictionary representation for serialization."""
        from dataclasses import asdict

        return asdict(self)
