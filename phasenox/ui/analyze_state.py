"""Qt-free deterministic state and DTO construction for the Analyze workflow."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from .contracts import (
    AnalysisCommand,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
)


class AnalyzePhase(str, Enum):
    EMPTY = "empty"
    SELECTED = "selected"
    INVALID = "invalid"
    READY = "ready"
    REVIEW = "review"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    field: str
    label: str
    capability_ids: tuple[str, ...]


FEATURE_DEFINITIONS = (
    FeatureDefinition(
        "include_semantic_analysis",
        "Semantic analysis",
        ("clap_embedding", "semantic_analysis", "semantic_intelligence"),
    ),
    FeatureDefinition("include_reasoning", "Reasoning", ("reasoning", "llm_reasoning")),
    FeatureDefinition("include_rag", "Knowledge / RAG", ("rag", "knowledge_rag", "rag_retrieval")),
    FeatureDefinition(
        "include_mix_intelligence",
        "Mix intelligence",
        ("mix_intelligence", "audio_intelligence"),
    ),
    FeatureDefinition(
        "include_plugin_intelligence",
        "Plugin intelligence",
        ("plugin_intelligence",),
    ),
)


@dataclass(frozen=True, slots=True)
class FeatureControlState:
    field: str
    label: str
    enabled: bool
    checked: bool = False
    availability: Availability = Availability.UNKNOWN
    lifecycle: CapabilityLifecycle | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisFormState:
    phase: AnalyzePhase = AnalyzePhase.EMPTY
    source_path: Path | None = None
    reference_path: Path | None = None
    intent: str = ""
    delivery_target: str = ""
    output_path: Path | None = None
    features: tuple[FeatureControlState, ...] = ()
    validation_message: str | None = None

    @classmethod
    def initial(cls, capabilities: tuple[CapabilitySnapshot, ...] = ()) -> AnalysisFormState:
        return cls(features=feature_controls(capabilities))

    @property
    def selected_features(self) -> tuple[FeatureControlState, ...]:
        return tuple(item for item in self.features if item.checked)

    def select_source(self, path: Path | None) -> AnalysisFormState:
        state = replace(self, source_path=path, validation_message=None)
        return state.validate()

    def select_reference(self, path: Path | None) -> AnalysisFormState:
        return replace(self, reference_path=path)

    def configure(
        self,
        *,
        intent: str,
        delivery_target: str,
        output_path: Path | None,
        selected_features: frozenset[str],
    ) -> AnalysisFormState:
        features = tuple(
            replace(item, checked=item.enabled and item.field in selected_features)
            for item in self.features
        )
        return replace(
            self,
            intent=intent.strip(),
            delivery_target=delivery_target.strip(),
            output_path=output_path,
            features=features,
        ).validate()

    def with_capabilities(self, capabilities: tuple[CapabilitySnapshot, ...]) -> AnalysisFormState:
        controls = feature_controls(capabilities)
        checked = {item.field for item in self.features if item.checked}
        return replace(
            self,
            features=tuple(
                replace(item, checked=item.enabled and item.field in checked) for item in controls
            ),
        )

    def validate(self) -> AnalysisFormState:
        if self.source_path is None:
            return replace(
                self,
                phase=AnalyzePhase.EMPTY,
                validation_message="Choose an audio file to continue.",
            )
        if not self.source_path.exists():
            return replace(
                self,
                phase=AnalyzePhase.INVALID,
                validation_message="The selected audio file no longer exists.",
            )
        if not self.source_path.is_file():
            return replace(
                self,
                phase=AnalyzePhase.INVALID,
                validation_message="The selected audio path is not a file.",
            )
        if self.reference_path is not None:
            if not self.reference_path.exists():
                return replace(
                    self,
                    phase=AnalyzePhase.INVALID,
                    validation_message="The selected reference file no longer exists.",
                )
            if not self.reference_path.is_file():
                return replace(
                    self,
                    phase=AnalyzePhase.INVALID,
                    validation_message="The selected reference path is not a file.",
                )
        return replace(self, phase=AnalyzePhase.READY, validation_message=None)

    def review(self) -> AnalysisFormState:
        validated = self.validate()
        if validated.phase is not AnalyzePhase.READY:
            return validated
        return replace(validated, phase=AnalyzePhase.REVIEW)

    def build_command(self) -> AnalysisCommand:
        if self.phase is not AnalyzePhase.REVIEW or self.source_path is None:
            raise ValueError("Analysis must be valid and confirmed before dispatch.")
        selected = {item.field for item in self.selected_features}
        return AnalysisCommand(
            source_path=self.source_path,
            reference_paths=(self.reference_path,) if self.reference_path else (),
            intent=self.intent,
            delivery_target=self.delivery_target,
            include_semantic_analysis="include_semantic_analysis" in selected,
            include_reasoning="include_reasoning" in selected,
            include_rag="include_rag" in selected,
            include_mix_intelligence="include_mix_intelligence" in selected,
            include_plugin_intelligence="include_plugin_intelligence" in selected,
            output_path=self.output_path,
        )


def feature_controls(
    capabilities: tuple[CapabilitySnapshot, ...],
) -> tuple[FeatureControlState, ...]:
    by_id = {item.id: item for item in capabilities}
    controls = []
    for definition in FEATURE_DEFINITIONS:
        capability = next(
            (by_id[item_id] for item_id in definition.capability_ids if item_id in by_id),
            None,
        )
        if capability is None:
            controls.append(
                FeatureControlState(
                    definition.field,
                    definition.label,
                    enabled=False,
                    reason="Capability status has not been reported.",
                )
            )
            continue
        enabled = (
            capability.lifecycle is not CapabilityLifecycle.PLANNED
            and capability.availability in {Availability.AVAILABLE, Availability.DEGRADED}
        )
        controls.append(
            FeatureControlState(
                field=definition.field,
                label=definition.label,
                enabled=enabled,
                availability=capability.availability,
                lifecycle=capability.lifecycle,
                reason=capability.reason,
            )
        )
    return tuple(controls)

