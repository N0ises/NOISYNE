from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from brain.ui.contracts import (
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    ProviderStatus,
    RecoveryAction,
    RuntimeState,
    RuntimeStatus,
    UiError,
    UiErrorCategory,
)
from brain.ui.presentation_state import (
    NavigationState,
    NotificationLevel,
    NotificationState,
    PageId,
    RuntimePresentationPhase,
    RuntimePresentationState,
)
from brain.ui.presentation_store import PresentationStore


def test_navigation_uses_stable_page_ids_and_rejects_unavailable_pages() -> None:
    navigation = NavigationState(available_pages=(PageId.OVERVIEW, PageId.REPORTS))

    assert navigation.navigate(PageId.REPORTS).current_page is PageId.REPORTS
    with pytest.raises(ValueError):
        navigation.navigate(PageId.SETTINGS)


def test_runtime_phase_does_not_infer_capability_lifecycle() -> None:
    capability = CapabilitySnapshot(
        id="local_ml",
        display_name="Local ML",
        lifecycle=CapabilityLifecycle.PRODUCTION,
        availability=Availability.UNAVAILABLE,
        reason="Optional runtime is not installed.",
    )
    status = RuntimeStatus(
        state=RuntimeState.DEGRADED,
        requested_device="cpu",
        effective_device=None,
        device_reason="Optional runtime missing",
        loaded_models=(),
        provider=ProviderStatus("none", Availability.UNAVAILABLE),
        paths=(),
        configuration_source="test",
        capabilities=(capability,),
        checked_at=datetime.now(UTC),
    )

    state = RuntimePresentationState.from_status(status)

    assert state.phase is RuntimePresentationPhase.DEGRADED
    assert state.capability("local_ml") == capability
    assert state.capability("local_ml").lifecycle is CapabilityLifecycle.PRODUCTION
    assert state.capability("local_ml").availability is Availability.UNAVAILABLE


def test_notifications_are_dismissible_ordered_and_bounded() -> None:
    state = NotificationState(history_limit=2)
    for message in ("one", "two", "three"):
        state = state.add(level=NotificationLevel.INFO, message=message)

    assert [item.message for item in state.active] == ["one", "two", "three"]
    assert [item.message for item in state.history] == ["two", "three"]
    assert [item.sequence for item in state.history] == [2, 3]

    state = state.dismiss("notification-2")
    assert [item.message for item in state.active] == ["one", "three"]
    assert [item.message for item in state.history] == ["two", "three"]


def test_loading_runtime_is_explicit() -> None:
    state = replace(RuntimePresentationState(), phase=RuntimePresentationPhase.UNKNOWN)
    assert state.loading().phase is RuntimePresentationPhase.LOADING


def test_structured_global_error_preserves_recovery_actions() -> None:
    store = PresentationStore()
    error = UiError(
        code="configuration_missing",
        category=UiErrorCategory.CONFIGURATION,
        user_message="Choose a valid configuration.",
        recovery_actions=(RecoveryAction("open_settings", "Open settings"),),
    )

    notification_id = store.add_error(error)

    notification = store.state.notifications.active[-1]
    assert notification.notification_id == notification_id
    assert notification.error is error
    assert notification.operation_id is None
    assert notification.recovery_actions == error.recovery_actions
