from __future__ import annotations

import pytest

from phasenox.ui.contracts import Availability, OperationState
from phasenox.ui.design_system.semantics import (
    VisualState,
    availability_visual_state,
    operation_visual_state,
    result_visual_state,
    runtime_visual_state,
)
from phasenox.ui.presentation_state import ResultPhase, RuntimePresentationPhase


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (None, VisualState.IDLE),
        (OperationState.RUNNING, VisualState.RUNNING),
        (OperationState.COMPLETED, VisualState.SUCCESS),
        (OperationState.FAILED, VisualState.ERROR),
        (OperationState.CANCELLED, VisualState.CANCELLED),
    ],
)
def test_operation_semantic_mapping(state, expected) -> None:
    assert operation_visual_state(state) is expected


def test_runtime_result_and_availability_mappings_remain_explicit() -> None:
    assert runtime_visual_state(RuntimePresentationPhase.DEGRADED) is VisualState.DEGRADED
    assert result_visual_state(ResultPhase.UNAVAILABLE) is VisualState.UNAVAILABLE
    assert availability_visual_state(Availability.UNKNOWN) is VisualState.UNKNOWN

