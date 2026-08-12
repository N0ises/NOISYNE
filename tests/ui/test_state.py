from __future__ import annotations

from brain.ui.state import ApplicationLifecycle, ApplicationStateStore


def test_state_store_notifies_lifecycle_changes() -> None:
    store = ApplicationStateStore()
    observed = []
    store.subscribe(observed.append)

    store.set_lifecycle(ApplicationLifecycle.READY, "Ready")

    assert store.state.lifecycle is ApplicationLifecycle.READY
    assert observed == [store.state]
