"""Reusable backend-free Qt Widget primitives for desktop pages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..contracts import CapabilitySnapshot, RecoveryAction, UiError
from ..presentation_state import Notification, NotificationLevel
from .semantics import VisualState, availability_visual_state
from .tokens import DEFAULT_TOKENS, DesignTokens


def _refresh_style(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class ButtonVariant(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DANGER = "danger"


class DesignButton(QPushButton):
    def __init__(
        self,
        text: str,
        *,
        variant: str = ButtonVariant.SECONDARY,
        accessible_name: str | None = None,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        role = variant.value if isinstance(variant, ButtonVariant) else variant
        self.setProperty("variant", role)
        self.setMinimumHeight(tokens.controls.standard_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(accessible_name or text)


class IconButton(DesignButton):
    def __init__(
        self,
        accessible_name: str,
        *,
        icon: QIcon | None = None,
        fallback_text: str = "...",
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            fallback_text,
            variant="icon",
            accessible_name=accessible_name,
            tokens=tokens,
            parent=parent,
        )
        if icon is not None:
            self.setIcon(icon)
        self.setIconSize(QSize(tokens.icons.medium, tokens.icons.medium))
        self.setToolTip(accessible_name)


class PageHeader(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHeader")
        self._title = QLabel(title)
        self._title.setObjectName("pageHeaderTitle")
        self._title.setProperty("textRole", "pageTitle")
        self._title.setAccessibleName("Page title")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("pageHeaderSubtitle")
        self._subtitle.setProperty("textRole", "secondary")
        self._subtitle.setWordWrap(True)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(tokens.spacing.xs)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._subtitle)

        self.actions = QHBoxLayout()
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(tokens.spacing.sm)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens.spacing.lg)
        layout.addLayout(text_layout, 1)
        layout.addLayout(self.actions)

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        self._subtitle.setText(subtitle)
        self._subtitle.setVisible(bool(subtitle))

    def add_action(self, button: QPushButton) -> None:
        self.actions.addWidget(button)


class Card(QFrame):
    def __init__(
        self,
        title: str | None = None,
        *,
        component: str = "card",
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("component", component)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(
            tokens.spacing.md,
            tokens.spacing.md,
            tokens.spacing.md,
            tokens.spacing.md,
        )
        self.content_layout.setSpacing(tokens.spacing.md)
        if title:
            label = QLabel(title)
            label.setProperty("textRole", "title")
            self.content_layout.addWidget(label)


class Panel(Card):
    def __init__(self, title: str | None = None, **kwargs) -> None:
        super().__init__(title, component="panel", **kwargs)


class TextInput(QLineEdit):
    def __init__(
        self,
        placeholder: str = "",
        *,
        accessible_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setAccessibleName(accessible_name or placeholder or "Text input")
        self.setClearButtonEnabled(True)


class ComboBox(QComboBox):
    def __init__(
        self,
        items: tuple[str, ...] = (),
        *,
        accessible_name: str = "Selection",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.addItems(items)
        self.setAccessibleName(accessible_name)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class CheckBox(QCheckBox):
    def __init__(self, text: str, *, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setAccessibleName(text)


class ToggleSwitch(CheckBox):
    def __init__(self, text: str, *, parent: QWidget | None = None) -> None:
        super().__init__(text, parent=parent)
        self.setProperty("controlRole", "toggle")
        self.setAccessibleDescription("Toggle control")


class TabView(QTabWidget):
    def __init__(self, *, accessible_name: str = "Tabs", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName(accessible_name)
        self.setDocumentMode(True)


class TableView(QTableWidget):
    def __init__(
        self,
        headers: tuple[str, ...] = (),
        *,
        accessible_name: str = "Data table",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.setAccessibleName(accessible_name)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


class MetricCard(Card):
    def __init__(
        self,
        label: str,
        value: str,
        supporting_text: str = "",
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tokens=tokens, parent=parent)
        self._label = label
        label_widget = QLabel(label)
        label_widget.setProperty("textRole", "secondary")
        self.value_label = QLabel(value)
        self.value_label.setProperty("textRole", "metric")
        self.value_label.setAccessibleName(f"{label}: {value}")
        support_widget = QLabel(supporting_text)
        support_widget.setProperty("textRole", "caption")
        support_widget.setWordWrap(True)
        self.content_layout.addWidget(label_widget)
        self.content_layout.addWidget(self.value_label)
        self.content_layout.addWidget(support_widget)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
        self.value_label.setAccessibleName(f"{self._label}: {value}")


class StatusBadge(QLabel):
    def __init__(
        self,
        text: str,
        state: VisualState = VisualState.IDLE,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setProperty("component", "statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.set_state(state)

    @property
    def visual_state(self) -> VisualState:
        return VisualState(self.property("status"))

    def set_state(self, state: VisualState) -> None:
        self.setProperty("status", state.value)
        self.setAccessibleDescription(f"Status: {state.value}")
        _refresh_style(self)


class CapabilityStatusIndicator(Card):
    """Display lifecycle and current availability as separate concepts."""

    def __init__(
        self,
        capability: CapabilitySnapshot,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(capability.display_name, tokens=tokens, parent=parent)
        lifecycle = QLabel(f"Lifecycle: {capability.lifecycle.value}")
        lifecycle.setProperty("textRole", "caption")
        availability = StatusBadge(
            capability.availability.value,
            availability_visual_state(capability.availability),
        )
        self.content_layout.addWidget(lifecycle)
        self.content_layout.addWidget(availability)
        if capability.reason:
            reason = QLabel(capability.reason)
            reason.setProperty("textRole", "secondary")
            reason.setWordWrap(True)
            self.content_layout.addWidget(reason)


class ProgressIndicator(QProgressBar):
    def __init__(
        self,
        progress: float | None = None,
        *,
        accessible_name: str = "Operation progress",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setTextVisible(False)
        self.setAccessibleName(accessible_name)
        self.set_progress(progress)

    def set_progress(self, progress: float | None) -> None:
        if progress is None:
            self.setRange(0, 0)
            self.setAccessibleDescription("Progress is indeterminate")
            return
        bounded = max(0.0, min(1.0, progress))
        self.setRange(0, 1000)
        self.setValue(round(bounded * 1000))
        self.setAccessibleDescription(f"Progress: {bounded:.0%}")


class EmptyState(Card):
    action_requested = Signal()

    def __init__(
        self,
        title: str,
        message: str,
        action_label: str | None = None,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tokens=tokens, parent=parent)
        title_widget = QLabel(title)
        title_widget.setProperty("textRole", "title")
        message_widget = QLabel(message)
        message_widget.setProperty("textRole", "secondary")
        message_widget.setWordWrap(True)
        self.content_layout.addWidget(title_widget)
        self.content_layout.addWidget(message_widget)
        if action_label:
            button = DesignButton(action_label, variant=ButtonVariant.PRIMARY, tokens=tokens)
            button.clicked.connect(self.action_requested)
            self.content_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)


class ErrorState(Card):
    recovery_requested = Signal(str)

    def __init__(
        self,
        error: UiError,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(component="panel", tokens=tokens, parent=parent)
        self.setProperty("semantic", "error")
        title = QLabel("Something needs attention")
        title.setProperty("textRole", "title")
        message = QLabel(error.user_message)
        message.setWordWrap(True)
        usability = QLabel(error.usability_message)
        usability.setObjectName("errorUsability")
        usability.setProperty("textRole", "secondary")
        usability.setWordWrap(True)
        self.content_layout.addWidget(title)
        self.content_layout.addWidget(message)
        self.content_layout.addWidget(usability)
        self._add_recovery_actions(error.recovery_actions, tokens)
        self.setAccessibleName(f"Error: {error.user_message}")

    def _add_recovery_actions(
        self, actions: tuple[RecoveryAction, ...], tokens: DesignTokens
    ) -> None:
        if not actions:
            return
        row = QHBoxLayout()
        row.setSpacing(tokens.spacing.sm)
        for action in actions:
            button = DesignButton(action.label, tokens=tokens)
            button.clicked.connect(
                lambda _checked=False, action_id=action.id: self.recovery_requested.emit(action_id)
            )
            row.addWidget(button)
        row.addStretch(1)
        self.content_layout.addLayout(row)


class ModalDialog(QDialog):
    def __init__(
        self,
        title: str,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(tokens.controls.dialog_minimum_width)
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
        )
        self.content_layout.setSpacing(tokens.spacing.lg)


class ConfirmationDialog(ModalDialog):
    def __init__(
        self,
        title: str,
        message: str,
        *,
        confirm_label: str = "Confirm",
        destructive: bool = False,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, tokens=tokens, parent=parent)
        message_widget = QLabel(message)
        message_widget.setWordWrap(True)
        self.content_layout.addWidget(message_widget)
        buttons = QDialogButtonBox()
        self.confirm_button = DesignButton(
            confirm_label,
            variant=ButtonVariant.DANGER if destructive else ButtonVariant.PRIMARY,
            tokens=tokens,
        )
        self.cancel_button = DesignButton("Cancel", tokens=tokens)
        buttons.addButton(self.confirm_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.content_layout.addWidget(buttons)


class NotificationToast(QFrame):
    dismissed = Signal(str)
    recovery_requested = Signal(str, str)

    def __init__(
        self,
        notification: Notification,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.notification_id = notification.notification_id
        self.setProperty("component", "panel")
        self.setProperty("semantic", _notification_semantic(notification.level))
        self.setAccessibleName(f"{notification.level.value} notification")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing.md,
            tokens.spacing.md,
            tokens.spacing.md,
            tokens.spacing.md,
        )
        layout.setSpacing(tokens.spacing.sm)
        text = QVBoxLayout()
        message = QLabel(notification.message)
        message.setWordWrap(True)
        text.addWidget(message)
        if notification.error is not None:
            usability = QLabel(notification.error.usability_message)
            usability.setObjectName("notificationUsability")
            usability.setProperty("textRole", "secondary")
            usability.setWordWrap(True)
            text.addWidget(usability)
        layout.addLayout(text, 1)
        for action in notification.recovery_actions:
            button = DesignButton(action.label, tokens=tokens)
            button.clicked.connect(
                lambda _checked=False, action_id=action.id: self.recovery_requested.emit(
                    notification.notification_id, action_id
                )
            )
            layout.addWidget(button)
        dismiss = IconButton("Dismiss notification", fallback_text="X", tokens=tokens)
        dismiss.clicked.connect(
            lambda _checked=False: self.dismissed.emit(notification.notification_id)
        )
        layout.addWidget(dismiss)


@dataclass(frozen=True, slots=True)
class AudioFileCardData:
    path: Path
    detail: str = ""
    available: bool = True


class AudioFileCard(Card):
    activated = Signal(object)
    remove_requested = Signal(object)

    def __init__(
        self,
        data: AudioFileCardData,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tokens=tokens, parent=parent)
        self.data = data
        row = QHBoxLayout()
        text = QVBoxLayout()
        name = QLabel(data.path.name)
        name.setProperty("textRole", "title")
        detail = QLabel(data.detail or str(data.path.parent))
        detail.setProperty("textRole", "secondary")
        detail.setWordWrap(True)
        text.addWidget(name)
        text.addWidget(detail)
        row.addLayout(text, 1)
        status = StatusBadge(
            "Available" if data.available else "Missing",
            VisualState.READY if data.available else VisualState.UNAVAILABLE,
        )
        row.addWidget(status)
        open_button = DesignButton("Open", tokens=tokens)
        open_button.setEnabled(data.available)
        open_button.clicked.connect(lambda _checked=False: self.activated.emit(data))
        row.addWidget(open_button)
        remove_button = IconButton("Remove audio file", fallback_text="X", tokens=tokens)
        remove_button.clicked.connect(lambda _checked=False: self.remove_requested.emit(data))
        row.addWidget(remove_button)
        self.content_layout.addLayout(row)
        self.setAccessibleName(f"Audio file: {data.path.name}")


class ResultSection(Card):
    def __init__(
        self,
        title: str,
        *,
        state: VisualState = VisualState.IDLE,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, component="resultSection", tokens=tokens, parent=parent)
        self.status_badge = StatusBadge(state.value.title(), state)
        self.content_layout.insertWidget(1, self.status_badge, 0, Qt.AlignmentFlag.AlignLeft)


class Sidebar(QListWidget):
    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedWidth(tokens.controls.sidebar_width)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setAccessibleName("Primary navigation")


class TopBar(QFrame):
    def __init__(
        self,
        title: str = "",
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("component", "panel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing.lg,
            tokens.spacing.sm,
            tokens.spacing.lg,
            tokens.spacing.sm,
        )
        label = QLabel(title)
        label.setProperty("textRole", "title")
        layout.addWidget(label)
        layout.addStretch(1)


class AppShell(QWidget):
    def __init__(
        self,
        sidebar: QWidget,
        workspace: QWidget,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(workspace, 1)


def _notification_semantic(level: NotificationLevel) -> str:
    return {
        NotificationLevel.INFO: VisualState.INFO.value,
        NotificationLevel.WARNING: VisualState.WARNING.value,
        NotificationLevel.ERROR: VisualState.ERROR.value,
    }[level]
