"""Global shell surfaces bound only to Sprint 2 presentation DTOs."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .contracts import ProductMetadata
from .design_system.components import (
    ButtonVariant,
    DesignButton,
    NotificationToast,
    ProgressIndicator,
    StatusBadge,
)
from .design_system.semantics import (
    VisualState,
    operation_visual_state,
    runtime_visual_state,
)
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import (
    NotificationState,
    OperationPresentationState,
    RuntimePresentationPhase,
    RuntimePresentationState,
)


class ProductIdentity(QFrame):
    def __init__(
        self,
        metadata: ProductMetadata,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("productIdentity")
        self.setAccessibleName(f"{metadata.display_name}, version {metadata.version}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens.spacing.xxs)
        self.name_label = QLabel(metadata.display_name)
        self.name_label.setObjectName("productDisplayName")
        self.name_label.setProperty("textRole", "title")
        version = QLabel(f"Version {metadata.version}")
        version.setProperty("textRole", "caption")
        layout.addWidget(self.name_label)
        layout.addWidget(version)


class RuntimeStatusSurface(QWidget):
    activated = Signal()

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("runtimeStatusSurface")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens.spacing.sm)
        label = QLabel("Runtime")
        label.setProperty("textRole", "caption")
        self.badge = StatusBadge("Unknown", VisualState.IDLE)
        self.details_button = DesignButton("Details", tokens=tokens)
        self.details_button.setAccessibleName("Open runtime status")
        self.details_button.clicked.connect(self.activated)
        layout.addWidget(label)
        layout.addWidget(self.badge)
        layout.addWidget(self.details_button)

    def render(self, runtime: RuntimePresentationState) -> None:
        labels = {
            RuntimePresentationPhase.LOADING: "Checking",
            RuntimePresentationPhase.UNKNOWN: "Unknown",
            RuntimePresentationPhase.READY: "Ready",
            RuntimePresentationPhase.DEGRADED: "Degraded",
            RuntimePresentationPhase.UNAVAILABLE: "Unavailable",
        }
        self.badge.setText(labels[runtime.phase])
        self.badge.set_state(runtime_visual_state(runtime.phase))


class OperationStatusSurface(QFrame):
    cancel_requested = Signal()

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("operationStatusSurface")
        self.setProperty("component", "panel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing.md,
            tokens.spacing.sm,
            tokens.spacing.md,
            tokens.spacing.sm,
        )
        layout.setSpacing(tokens.spacing.sm)
        self.label = QLabel("No current operation")
        self.label.setObjectName("operationStatusLabel")
        self.badge = StatusBadge("Idle", VisualState.IDLE)
        self.progress = ProgressIndicator(None)
        self.progress.setObjectName("operationProgress")
        self.progress.setMinimumWidth(120)
        self.cancel_button = DesignButton(
            "Cancel",
            variant=ButtonVariant.SECONDARY,
            tokens=tokens,
        )
        self.cancel_button.setObjectName("cancelOperation")
        self.cancel_button.clicked.connect(self.cancel_requested)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.badge)
        layout.addWidget(self.progress)
        layout.addWidget(self.cancel_button)
        self.render(OperationPresentationState())

    def render(self, operation: OperationPresentationState) -> None:
        state = operation_visual_state(operation.state)
        state_text = operation.state.value if operation.state is not None else "idle"
        self.label.setText(operation.message or operation.kind or "No current operation")
        self.badge.setText(state_text.replace("_", " ").title())
        self.badge.set_state(state)
        active = not operation.is_idle and not operation.is_terminal
        self.progress.setVisible(active)
        if active:
            self.progress.set_progress(operation.progress)
        self.cancel_button.setVisible(active and operation.cancellable)
        self.cancel_button.setEnabled(active and operation.cancellable)


class NotificationSurface(QWidget):
    dismissed = Signal(str)
    recovery_requested = Signal(str, str)

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("notificationSurface")
        self.setAccessibleName("Notifications")
        self._tokens = tokens
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(tokens.spacing.sm)
        self._toasts: dict[str, NotificationToast] = {}
        self.setVisible(False)

    def render(self, notifications: NotificationState) -> None:
        active_ids = {item.notification_id for item in notifications.active}
        for notification_id in tuple(self._toasts):
            if notification_id not in active_ids:
                toast = self._toasts.pop(notification_id)
                self._layout.removeWidget(toast)
                toast.setParent(None)
                toast.deleteLater()
        for notification in notifications.active:
            if notification.notification_id not in self._toasts:
                toast = NotificationToast(notification, tokens=self._tokens)
                toast.dismissed.connect(self.dismissed)
                toast.recovery_requested.connect(self.recovery_requested)
                self._toasts[notification.notification_id] = toast
                self._layout.addWidget(toast)
        self.setVisible(bool(notifications.active))
