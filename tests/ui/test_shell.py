from __future__ import annotations

from datetime import UTC, datetime

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QPushButton

from brain.ui.app import build_main_window
from brain.ui.contracts import (
    Availability,
    OperationEvent,
    OperationHandle,
    OperationState,
    ProviderStatus,
    RecoveryAction,
    RuntimeState,
    RuntimeStatus,
    UiError,
    UiErrorCategory,
)
from brain.ui.design_system.components import NotificationToast
from brain.ui.design_system.gallery import ComponentGallery
from brain.ui.design_system.tokens import DEFAULT_TOKENS
from brain.ui.pages import PageHost
from brain.ui.presentation_state import (
    NAVIGATION_ORDER,
    NotificationLevel,
    OperationPresentationState,
    PageId,
    PresentationState,
    SessionState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.shell_surfaces import OperationStatusSurface, ProductIdentity, RuntimeStatusSurface
from brain.ui.state import ApplicationStateStore


def _window(qtbot, fake_adapter, store: PresentationStore | None = None):
    presentation_store = store or PresentationStore()
    window = build_main_window(fake_adapter, ApplicationStateStore(), presentation_store)
    qtbot.addWidget(window)
    window.show()
    return window, presentation_store


def _runtime_status(state: RuntimeState) -> RuntimeStatus:
    return RuntimeStatus(
        state=state,
        requested_device="cpu",
        effective_device="cpu" if state is RuntimeState.READY else None,
        device_reason=None,
        loaded_models=(),
        provider=ProviderStatus("test", Availability.UNKNOWN),
        paths=(),
        configuration_source="test",
        capabilities=(),
        checked_at=datetime.now(UTC),
    )


def test_all_stable_page_ids_appear_in_navigation(qtbot, fake_adapter) -> None:
    window, _store = _window(qtbot, fake_adapter)
    navigation = window.findChild(QListWidget, "primaryNavigation")

    ids = tuple(
        PageId(navigation.item(row).data(Qt.ItemDataRole.UserRole))
        for row in range(navigation.count())
    )

    assert ids == NAVIGATION_ORDER
    assert navigation.accessibleName() == "Primary navigation"


def test_user_and_programmatic_navigation_converge_without_extra_publish(
    qtbot, fake_adapter
) -> None:
    window, store = _window(qtbot, fake_adapter)
    navigation = window.findChild(QListWidget, "primaryNavigation")
    host = window.findChild(PageHost, "pageHost")

    navigation.setCurrentRow(NAVIGATION_ORDER.index(PageId.REPORTS))
    assert store.state.navigation.current_page is PageId.REPORTS
    assert host.current_page_id is PageId.REPORTS

    observed = []
    store.subscribe(observed.append)
    store.navigate(PageId.SETTINGS)

    assert len(observed) == 2
    assert navigation.currentRow() == NAVIGATION_ORDER.index(PageId.SETTINGS)
    assert host.current_page_id is PageId.SETTINGS


def test_every_navigation_destination_selects_its_persistent_page(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    navigation = window.findChild(QListWidget, "primaryNavigation")
    host = window.findChild(PageHost, "pageHost")
    original_pages = {page_id: host.page(page_id) for page_id in NAVIGATION_ORDER}

    for row, page_id in enumerate(NAVIGATION_ORDER):
        navigation.setCurrentRow(row)
        assert store.state.navigation.current_page is page_id
        assert host.current_page_id is page_id
        assert host.currentWidget() is original_pages[page_id]


def test_navigation_preserves_session_and_page_instances(qtbot, fake_adapter, tmp_path) -> None:
    selected_audio = tmp_path / "selected.wav"
    selected_audio.write_bytes(b"audio")
    store = PresentationStore(
        PresentationState.from_session(SessionState().select_audio(selected_audio))
    )
    window, store = _window(qtbot, fake_adapter, store)
    host = window.findChild(PageHost, "pageHost")
    overview = host.page(PageId.OVERVIEW)

    store.navigate(PageId.ANALYZE)
    store.navigate(PageId.OVERVIEW)

    assert store.state.session.selected_audio == selected_audio
    assert host.currentWidget() is overview
    assert host.page(PageId.OVERVIEW) is overview


@pytest.mark.parametrize(
    ("runtime_state", "expected"),
    [
        (RuntimeState.UNKNOWN, "Unknown"),
        (RuntimeState.READY, "Ready"),
        (RuntimeState.DEGRADED, "Degraded"),
        (RuntimeState.UNAVAILABLE, "Unavailable"),
    ],
)
def test_runtime_indicator_maps_runtime_truth(qtbot, fake_adapter, runtime_state, expected) -> None:
    window, store = _window(qtbot, fake_adapter)
    surface = window.findChild(RuntimeStatusSurface, "runtimeStatusSurface")

    store.set_runtime_status(_runtime_status(runtime_state))

    assert surface.badge.text() == expected


def test_runtime_loading_is_checking_not_ready(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    surface = window.findChild(RuntimeStatusSurface, "runtimeStatusSurface")

    store.set_runtime_loading()

    assert surface.badge.text() == "Checking"


def test_runtime_details_open_completed_settings_runtime_workspace(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    surface = window.findChild(RuntimeStatusSurface, "runtimeStatusSurface")

    surface.details_button.click()

    assert store.state.navigation.current_page is PageId.SETTINGS
    assert window._page_host.current_page_id is PageId.SETTINGS
    assert PageId.RUNTIME_STATUS not in NAVIGATION_ORDER


def test_operation_surface_is_truthful_about_progress_and_cancellation(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    surface = window.findChild(OperationStatusSurface, "operationStatusSurface")
    store.begin_operation(OperationHandle("op-1", "analysis"), cancellable=True)

    assert surface.badge.text() == "Queued"
    assert surface.progress.minimum() == 0
    assert surface.progress.maximum() == 0
    assert surface.cancel_button.isVisible()
    assert surface.cancel_button.isEnabled()

    store.apply_operation_event(
        OperationEvent("op-1", 1, OperationState.RUNNING, "running", cancellable=False)
    )

    assert surface.badge.text() == "Running"
    assert not surface.cancel_button.isVisible()
    assert surface.progress.maximum() == 0


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (OperationState.QUEUED, "Queued"),
        (OperationState.VALIDATING, "Validating"),
        (OperationState.RUNNING, "Running"),
        (OperationState.CANCELLING, "Cancelling"),
        (OperationState.COMPLETED, "Completed"),
        (OperationState.FAILED, "Failed"),
        (OperationState.CANCELLED, "Cancelled"),
    ],
)
def test_operation_indicator_maps_all_contract_states(
    qtbot, state: OperationState, expected: str
) -> None:
    surface = OperationStatusSurface()
    qtbot.addWidget(surface)

    surface.render(
        OperationPresentationState(
            operation_id="op-1",
            kind="analysis",
            state=state,
        )
    )

    assert surface.badge.text() == expected


def test_cancel_control_requests_but_does_not_claim_completion(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    surface = window.findChild(OperationStatusSurface, "operationStatusSurface")
    store.begin_operation(OperationHandle("op-1", "analysis"), cancellable=True)

    surface.cancel_button.click()

    assert store.state.operation.state is OperationState.CANCELLING
    assert store.state.operation.cancel_requested
    assert surface.badge.text() == "Cancelling"
    assert not surface.cancel_button.isVisible()


def test_notification_dismissal_and_structured_recovery_intent(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    error = UiError(
        code="configuration_missing",
        category=UiErrorCategory.CONFIGURATION,
        user_message="Choose a configuration.",
        recovery_actions=(RecoveryAction("open_settings", "Open settings"),),
    )
    notification_id = store.add_error(error)
    toast = window.findChild(NotificationToast)
    buttons = toast.findChildren(QPushButton)

    with qtbot.waitSignal(window.recovery_action_requested, timeout=1000) as recovery:
        next(button for button in buttons if button.text() == "Open settings").click()
    assert recovery.args == [notification_id, "open_settings"]
    assert store.state.navigation.current_page is PageId.SETTINGS
    assert store.state.notifications.active == ()

    next(button for button in buttons if button.accessibleName() == "Dismiss notification").click()
    assert store.state.notifications.active == ()


def test_global_surface_renders_info_warning_and_error_notifications(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    for level in NotificationLevel:
        store.add_notification(level, f"{level.value} message")

    toasts = window.findChildren(NotificationToast)

    assert len(toasts) == 3
    assert [toast.property("semantic") for toast in toasts] == ["info", "warning", "error"]


def test_global_exception_error_enters_structured_notification_surface(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    error = UiError(
        "unexpected_internal_error",
        UiErrorCategory.INTERNAL,
        "An unexpected error occurred.",
        technical_detail="RuntimeError",
    )

    window.show_error(error)

    assert store.state.notifications.active[-1].error is error
    assert window.statusBar().currentMessage() == error.user_message
    assert window.findChild(NotificationToast) is not None


def test_product_identity_uses_metadata_and_settings_entry_navigates(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    identity = window.findChild(ProductIdentity, "productIdentity")
    settings = window.findChild(QPushButton, "settingsEntry")

    assert identity.name_label.text() == fake_adapter.product_metadata().display_name
    assert fake_adapter.product_metadata().version in identity.accessibleName()

    settings.click()
    assert store.state.navigation.current_page is PageId.SETTINGS


def test_overview_is_dashboard_not_component_gallery(qtbot, fake_adapter) -> None:
    window, _store = _window(qtbot, fake_adapter)
    host = window.findChild(PageHost, "pageHost")

    assert host.current_page_id is PageId.OVERVIEW
    assert host.findChild(ComponentGallery) is None
    assert host.currentWidget().accessibleName() == "Overview Dashboard"


def test_keyboard_navigation_and_shell_resize(qtbot, fake_adapter) -> None:
    window, store = _window(qtbot, fake_adapter)
    navigation = window.findChild(QListWidget, "primaryNavigation")
    navigation.setFocus()

    qtbot.keyClick(navigation, Qt.Key.Key_Down)
    assert store.state.navigation.current_page is PageId.ANALYZE

    window.resize(
        DEFAULT_TOKENS.controls.window_minimum_width,
        DEFAULT_TOKENS.controls.window_minimum_height,
    )
    qtbot.wait(10)
    assert window.width() >= DEFAULT_TOKENS.controls.window_minimum_width
    assert window.height() >= DEFAULT_TOKENS.controls.window_minimum_height
