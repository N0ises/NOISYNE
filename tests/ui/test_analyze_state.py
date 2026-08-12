from __future__ import annotations

import pytest

from brain.ui.analyze_state import AnalysisFormState, AnalyzePhase, feature_controls
from brain.ui.contracts import Availability, CapabilityLifecycle, CapabilitySnapshot


def _capability(
    capability_id: str,
    lifecycle: CapabilityLifecycle,
    availability: Availability,
    reason: str = "reason",
) -> CapabilitySnapshot:
    return CapabilitySnapshot(
        capability_id,
        capability_id,
        lifecycle,
        availability,
        reason=reason,
    )


def test_source_selection_clear_and_missing_file_validation(tmp_path) -> None:
    existing = tmp_path / "audio.wav"
    existing.write_bytes(b"audio")

    state = AnalysisFormState.initial().select_source(existing)
    assert state.phase is AnalyzePhase.READY
    assert state.source_path == existing

    missing = state.select_source(tmp_path / "missing.wav")
    assert missing.phase is AnalyzePhase.INVALID
    assert "no longer exists" in missing.validation_message

    cleared = state.select_source(None)
    assert cleared.phase is AnalyzePhase.EMPTY
    assert cleared.source_path is None


def test_optional_reference_is_single_v1_safe_path_and_validated(tmp_path) -> None:
    source = tmp_path / "source.wav"
    reference = tmp_path / "reference.wav"
    source.write_bytes(b"source")
    reference.write_bytes(b"reference")

    state = AnalysisFormState.initial().select_source(source).select_reference(reference).review()
    command = state.build_command()

    assert command.reference_paths == (reference,)

    invalid = state.select_reference(tmp_path / "missing-reference.wav").validate()
    assert invalid.phase is AnalyzePhase.INVALID
    assert "reference file" in invalid.validation_message


@pytest.mark.parametrize(
    ("lifecycle", "availability", "enabled"),
    [
        (CapabilityLifecycle.PLANNED, Availability.AVAILABLE, False),
        (CapabilityLifecycle.IMPLEMENTED, Availability.UNAVAILABLE, False),
        (CapabilityLifecycle.IMPLEMENTED, Availability.UNKNOWN, False),
        (CapabilityLifecycle.IMPLEMENTED, Availability.DEGRADED, True),
        (CapabilityLifecycle.PRODUCTION, Availability.AVAILABLE, True),
    ],
)
def test_capability_driven_controls(lifecycle, availability, enabled) -> None:
    controls = feature_controls((_capability("llm_reasoning", lifecycle, availability),))
    reasoning = next(item for item in controls if item.field == "include_reasoning")

    assert reasoning.enabled is enabled
    assert reasoning.lifecycle is lifecycle
    assert reasoning.availability is availability
    assert reasoning.reason == "reason"


def test_analysis_command_is_constructed_only_after_review(tmp_path) -> None:
    source = tmp_path / "source.wav"
    reference = tmp_path / "reference.wav"
    output = tmp_path / "analysis.json"
    source.write_bytes(b"source")
    reference.write_bytes(b"reference")
    capabilities = (
        _capability(
            "llm_reasoning",
            CapabilityLifecycle.IMPLEMENTED,
            Availability.AVAILABLE,
        ),
        _capability(
            "rag_retrieval",
            CapabilityLifecycle.IMPLEMENTED,
            Availability.DEGRADED,
        ),
    )
    state = (
        AnalysisFormState.initial(capabilities).select_source(source).select_reference(reference)
    )
    state = state.configure(
        intent="  mastering review  ",
        delivery_target=" streaming ",
        output_path=output,
        selected_features=frozenset({"include_reasoning", "include_rag"}),
    )

    with pytest.raises(ValueError):
        state.build_command()

    command = state.review().build_command()

    assert command.source_path == source
    assert command.reference_paths == (reference,)
    assert command.intent == "mastering review"
    assert command.delivery_target == "streaming"
    assert command.include_reasoning
    assert command.include_rag
    assert not command.include_semantic_analysis
    assert command.output_path == output


def test_disabled_feature_cannot_be_selected(tmp_path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    state = (
        AnalysisFormState.initial()
        .select_source(source)
        .configure(
            intent="",
            delivery_target="",
            output_path=None,
            selected_features=frozenset({"include_rag"}),
        )
    )

    assert state.selected_features == ()
