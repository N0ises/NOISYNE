from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from phasenox.ui.contracts import (
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    RecoveryAction,
    ResultUsability,
    UiError,
    UiErrorCategory,
)
from phasenox.ui.design_system.components import (
    AppShell,
    AudioFileCard,
    AudioFileCardData,
    ButtonVariant,
    CapabilityStatusIndicator,
    Card,
    CheckBox,
    ComboBox,
    ConfirmationDialog,
    DesignButton,
    EmptyState,
    ErrorState,
    IconButton,
    MetricCard,
    ModalDialog,
    NotificationToast,
    PageHeader,
    Panel,
    ProgressIndicator,
    ResultSection,
    Sidebar,
    StatusBadge,
    TableView,
    TabView,
    TextInput,
    ToggleSwitch,
    TopBar,
)
from phasenox.ui.design_system.semantics import VisualState
from phasenox.ui.presentation_state import Notification, NotificationLevel


def test_button_variants_and_disabled_state(qtbot) -> None:
    primary = DesignButton("Run", variant=ButtonVariant.PRIMARY)
    danger = DesignButton("Delete", variant=ButtonVariant.DANGER)
    qtbot.addWidget(primary)
    qtbot.addWidget(danger)

    assert primary.property("variant") == "primary"
    assert danger.property("variant") == "danger"
    assert primary.accessibleName() == "Run"

    primary.setDisabled(True)
    assert not primary.isEnabled()


def test_status_badge_preserves_semantic_states(qtbot) -> None:
    badge = StatusBadge("Degraded", VisualState.WARNING)
    qtbot.addWidget(badge)

    assert badge.visual_state is VisualState.WARNING
    badge.set_state(VisualState.UNAVAILABLE)
    assert badge.visual_state is VisualState.UNAVAILABLE
    assert badge.accessibleDescription() == "Status: unavailable"


def test_capability_indicator_keeps_lifecycle_and_availability_separate(qtbot) -> None:
    capability = CapabilitySnapshot(
        id="optional_ml",
        display_name="Optional local ML",
        lifecycle=CapabilityLifecycle.PRODUCTION,
        availability=Availability.UNAVAILABLE,
        reason="Optional runtime missing",
        checked_at=datetime.now(UTC),
    )
    indicator = CapabilityStatusIndicator(capability)
    qtbot.addWidget(indicator)

    texts = [label.text() for label in indicator.findChildren(QLabel)]
    badge = indicator.findChild(StatusBadge)
    assert "Lifecycle: production" in texts
    assert badge is not None
    assert badge.visual_state is VisualState.UNAVAILABLE


def test_input_focus_and_disabled_behavior(qtbot) -> None:
    field = TextInput("Search", accessible_name="Search files")
    qtbot.addWidget(field)
    field.show()

    field.setFocus(Qt.FocusReason.TabFocusReason)
    qtbot.waitUntil(field.hasFocus, timeout=1000)
    assert field.hasFocus()
    assert field.accessibleName() == "Search files"

    field.setDisabled(True)
    assert not field.isEnabled()


def test_empty_and_error_states_emit_intent(qtbot) -> None:
    empty = EmptyState("No files", "Choose a file to continue.", "Choose file")
    error = ErrorState(
        UiError(
            code="missing_file",
            category=UiErrorCategory.VALIDATION,
            user_message="The selected file is missing.",
            recovery_actions=(RecoveryAction("choose_file", "Choose another"),),
            result_usability=ResultUsability.NOT_USABLE,
        )
    )
    qtbot.addWidget(empty)
    qtbot.addWidget(error)

    with qtbot.waitSignal(empty.action_requested, timeout=1000):
        empty.findChild(QPushButton).click()
    with qtbot.waitSignal(error.recovery_requested, timeout=1000) as signal:
        error.findChild(QPushButton).click()

    assert signal.args == ["choose_file"]
    assert error.findChild(QLabel, "errorUsability").text() == (
        "No result is available from this operation."
    )


def test_confirmation_dialog_accepts_and_rejects(qtbot) -> None:
    accepted = ConfirmationDialog("Confirm", "Continue?")
    rejected = ConfirmationDialog("Confirm", "Continue?")
    qtbot.addWidget(accepted)
    qtbot.addWidget(rejected)

    accepted.confirm_button.click()
    rejected.cancel_button.click()

    assert accepted.result() == ConfirmationDialog.DialogCode.Accepted
    assert rejected.result() == ConfirmationDialog.DialogCode.Rejected


def test_notification_toast_emits_dismiss_and_recovery(qtbot) -> None:
    error = UiError(
        code="report_failed",
        category=UiErrorCategory.REPORT_EXPORT,
        user_message="Could not open file.",
        recovery_actions=(RecoveryAction("retry", "Retry"),),
        result_usability=ResultUsability.USABLE,
    )
    notification = Notification(
        notification_id="notification-1",
        sequence=1,
        level=NotificationLevel.ERROR,
        message="Could not open file.",
        created_at=datetime.now(UTC),
        error=error,
        recovery_actions=(RecoveryAction("retry", "Retry"),),
    )
    toast = NotificationToast(notification)
    qtbot.addWidget(toast)
    buttons = toast.findChildren(QPushButton)

    with qtbot.waitSignal(toast.recovery_requested, timeout=1000) as recovery:
        next(button for button in buttons if button.text() == "Retry").click()
    with qtbot.waitSignal(toast.dismissed, timeout=1000) as dismissed:
        next(
            button for button in buttons if button.accessibleName() == "Dismiss notification"
        ).click()

    assert recovery.args == ["notification-1", "retry"]
    assert dismissed.args == ["notification-1"]
    assert toast.findChild(QLabel, "notificationUsability").text() == (
        "Existing results and session data remain usable."
    )


def test_progress_is_indeterminate_without_backend_progress(qtbot) -> None:
    progress = ProgressIndicator(None)
    qtbot.addWidget(progress)

    assert progress.minimum() == 0
    assert progress.maximum() == 0
    progress.set_progress(0.25)
    assert progress.maximum() == 1000
    assert progress.value() == 250


def test_all_foundation_components_construct_headlessly(qtbot, tmp_path) -> None:
    widgets = [
        PageHeader("Title", "Subtitle"),
        Card("Card"),
        Panel("Panel"),
        IconButton("More"),
        ComboBox(("One", "Two")),
        CheckBox("Check"),
        ToggleSwitch("Toggle"),
        TabView(),
        TableView(("Name", "Value")),
        MetricCard("Score", "90"),
        ModalDialog("Dialog"),
        AudioFileCard(AudioFileCardData(tmp_path / "audio.wav", available=False)),
        ResultSection("Result", state=VisualState.CANCELLED),
        TopBar("Foundation"),
    ]
    sidebar = Sidebar()
    shell = AppShell(sidebar, QWidget())
    widgets.append(shell)
    for widget in widgets:
        qtbot.addWidget(widget)

    assert all(widget is not None for widget in widgets)
    audio_card = next(widget for widget in widgets if isinstance(widget, AudioFileCard))
    assert audio_card.accessibleName() == "Audio file: audio.wav"

