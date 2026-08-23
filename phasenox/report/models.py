from __future__ import annotations

from dataclasses import dataclass, field

from phasenox.audio.plugin.models import PluginIntelligenceResult


@dataclass
class ReportIssue:

    title: str

    severity: str

    description: str

    recommendation: str

    confidence: float = 0.85


@dataclass
class SoundBrainReport:

    audio_type: str

    source_type: str

    instrument: str | None

    is_full_mix: bool

    confidence: float

    semantic_labels: list[str] = field(default_factory=list)

    score: float = 0.0

    strengths: list[str] = field(default_factory=list)

    issues: list[ReportIssue] = field(default_factory=list)

    recommendations: list[str] = field(default_factory=list)

    ai_summary: str = ""

    root_causes: list = field(default_factory=list)

    prioritized_issues: list = field(default_factory=list)

    processing_chain: list = field(default_factory=list)

    explanations: list[str] = field(default_factory=list)

    confidence_scores: dict[str, float] = field(default_factory=dict)

    plugin_intelligence: PluginIntelligenceResult | None = None

    status: str = "ok"

    warnings: list[str] = field(default_factory=list)

    analysis: dict | None = None
