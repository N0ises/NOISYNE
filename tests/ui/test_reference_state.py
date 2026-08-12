from __future__ import annotations

import pytest

from brain.ui.contracts import Availability, CapabilityLifecycle, CapabilitySnapshot
from brain.ui.reference_state import ReferenceFormState, ReferencePhase


def _capability(availability: Availability = Availability.UNKNOWN) -> CapabilitySnapshot:
    return CapabilitySnapshot(
        "reference_comparison",
        "Reference comparison",
        CapabilityLifecycle.PRODUCTION,
        availability,
        reason="Runtime probe status",
    )


def test_multiple_references_are_supported_ordered_and_removable(tmp_path) -> None:
    current = tmp_path / "current.wav"
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    for path in (current, first, second):
        path.write_bytes(b"audio")

    state = ReferenceFormState.initial((_capability(),)).select_current(current)
    state = state.add_references((first, second, first))

    assert state.phase is ReferencePhase.READY
    assert state.reference_paths == (first, second)
    assert state.remove_reference(first).reference_paths == (second,)


def test_missing_current_and_reference_prevent_execution(tmp_path) -> None:
    current = tmp_path / "current.wav"
    reference = tmp_path / "reference.wav"
    current.write_bytes(b"audio")
    state = ReferenceFormState.initial((_capability(),)).select_current(current)

    assert state.phase is ReferencePhase.EMPTY
    assert "reference" in state.validation_message

    state = state.add_references((reference,))
    assert state.phase is ReferencePhase.INVALID
    assert "missing" in state.validation_message


def test_command_contains_only_supported_metadata_after_review(tmp_path) -> None:
    current = tmp_path / "current.wav"
    references = (tmp_path / "one.wav", tmp_path / "two.wav")
    output = tmp_path / "reports"
    current.write_bytes(b"audio")
    for path in references:
        path.write_bytes(b"audio")
    state = ReferenceFormState.initial((_capability(Availability.AVAILABLE),))
    state = (
        state.select_current(current)
        .add_references(references)
        .configure(
            genre=" electronic ",
            mood=" focused ",
            target=" streaming ",
            focus_areas=(" dynamics ", " stereo ", ""),
            output_directory=output,
        )
    )

    with pytest.raises(ValueError):
        state.build_command()
    command = state.review().build_command()

    assert command.current_path == current
    assert command.reference_paths == references
    assert command.genre == "electronic"
    assert command.mood == "focused"
    assert command.target == "streaming"
    assert command.focus_areas == ("dynamics", "stereo")
    assert command.output_directory == output


@pytest.mark.parametrize(
    ("lifecycle", "availability", "executable"),
    [
        (CapabilityLifecycle.PLANNED, Availability.AVAILABLE, False),
        (CapabilityLifecycle.PRODUCTION, Availability.UNAVAILABLE, False),
        (CapabilityLifecycle.PRODUCTION, Availability.UNKNOWN, True),
        (CapabilityLifecycle.PRODUCTION, Availability.DEGRADED, True),
    ],
)
def test_capability_controls_execution(lifecycle, availability, executable) -> None:
    capability = CapabilitySnapshot(
        "reference_comparison",
        "Reference comparison",
        lifecycle,
        availability,
        reason="reason",
    )

    state = ReferenceFormState.initial((capability,))

    assert state.capability.executable is executable
