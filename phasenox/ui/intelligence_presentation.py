"""Qt-free presentation state for retained intelligence results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contracts import (
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    IntelligenceItem,
    ReferenceFinding,
)
from .presentation_state import PresentationState


@dataclass(frozen=True, slots=True)
class IntelligenceCapabilityState:
    lifecycle: CapabilityLifecycle | None = None
    availability: Availability = Availability.UNKNOWN
    reason: str = "Capability status has not been reported."


@dataclass(frozen=True, slots=True)
class IntelligenceWorkspaceState:
    source_path: Path | None = None
    engineering: tuple[IntelligenceItem, ...] = ()
    mix: tuple[IntelligenceItem, ...] = ()
    plugin: tuple[IntelligenceItem, ...] = ()
    reasoning: str = ""
    reference_findings: tuple[ReferenceFinding, ...] = ()
    warnings: tuple[str, ...] = ()
    capabilities: tuple[tuple[str, IntelligenceCapabilityState], ...] = ()

    def capability(self, section: str) -> IntelligenceCapabilityState:
        return dict(self.capabilities)[section]


SECTION_CAPABILITIES = (
    ("engineering", "engineering_analysis"),
    ("mix", "mix_intelligence"),
    ("plugin", "plugin_intelligence"),
    ("reasoning", "llm_reasoning"),
)


def build_intelligence_workspace(state: PresentationState) -> IntelligenceWorkspaceState:
    analysis = state.session.last_analysis_result
    reference = state.session.last_reference_result
    capabilities = tuple(
        (section, _capability_state(state.runtime.capabilities, capability_id))
        for section, capability_id in SECTION_CAPABILITIES
    )
    if analysis is None:
        return IntelligenceWorkspaceState(
            reference_findings=reference.findings if reference else (),
            capabilities=capabilities,
        )
    snapshot = analysis.intelligence
    return IntelligenceWorkspaceState(
        source_path=analysis.source_path,
        engineering=snapshot.engineering,
        mix=snapshot.mix,
        plugin=snapshot.plugin,
        reasoning=snapshot.reasoning,
        reference_findings=reference.findings if reference else (),
        warnings=analysis.warnings,
        capabilities=capabilities,
    )


def _capability_state(
    capabilities: tuple[CapabilitySnapshot, ...], capability_id: str
) -> IntelligenceCapabilityState:
    capability = next((item for item in capabilities if item.id == capability_id), None)
    if capability is None:
        return IntelligenceCapabilityState()
    return IntelligenceCapabilityState(
        lifecycle=capability.lifecycle,
        availability=capability.availability,
        reason=capability.reason or "No availability reason was supplied.",
    )

