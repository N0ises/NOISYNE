from __future__ import annotations

import pytest

from brain.ui.contracts import Availability, CapabilityLifecycle, CapabilitySnapshot
from brain.ui.knowledge_state import KnowledgeQueryState


def _capability(availability: Availability, lifecycle=CapabilityLifecycle.IMPLEMENTED):
    return CapabilitySnapshot(
        "rag_retrieval",
        "RAG retrieval",
        lifecycle,
        availability,
        reason="Configured status reason.",
    )


@pytest.mark.parametrize(
    ("availability", "expected"),
    [
        (Availability.AVAILABLE, True),
        (Availability.DEGRADED, True),
        (Availability.UNAVAILABLE, False),
        (Availability.UNKNOWN, False),
    ],
)
def test_knowledge_capability_truth_controls_search(availability, expected) -> None:
    state = KnowledgeQueryState().with_capabilities((_capability(availability),)).set_text("mix")

    assert state.can_search is expected
    assert state.capability.reason == "Configured status reason."


def test_planned_knowledge_capability_is_not_executable() -> None:
    state = (
        KnowledgeQueryState()
        .with_capabilities((_capability(Availability.AVAILABLE, CapabilityLifecycle.PLANNED),))
        .set_text("mix")
    )

    assert not state.can_search


def test_query_is_trimmed_and_empty_query_is_rejected() -> None:
    state = KnowledgeQueryState().with_capabilities((_capability(Availability.AVAILABLE),))

    with pytest.raises(ValueError):
        state.set_text("   ").build_query()

    assert state.set_text("  gain staging  ").build_query().text == "gain staging"
