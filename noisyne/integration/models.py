from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from noisyne.audio.mix.models import MixIntelligenceResult
from noisyne.audio.plugin.models import PluginIntelligenceResult
from noisyne.reference.models import ReferenceComparison
from noisyne.report.models import SoundBrainReport


@dataclass(frozen=True, slots=True)
class WorkflowSession:
    """Session context for a target DAW project."""

    daw_name: str
    project_name: str = ""
    sample_rate: int | None = None
    bpm: float | None = None
    time_signature: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DAWCapability:
    """A feature the adapter can claim to support in this contract sprint."""

    name: str
    description: str
    available: bool = False


@dataclass(frozen=True, slots=True)
class ExportRequest:
    """Payload describing what should be exported to a workflow."""

    session: WorkflowSession
    output_dir: Path
    report: SoundBrainReport | None = None
    plugin_intelligence: PluginIntelligenceResult | None = None
    mix_intelligence: MixIntelligenceResult | None = None
    reference_comparison: ReferenceComparison | None = None


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Result of a single export operation."""

    adapter_name: str
    export_type: str
    success: bool
    files: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
