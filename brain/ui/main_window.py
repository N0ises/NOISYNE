"""Persistent Qt application shell bound to presentation-owned state."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QListWidgetItem,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from .analysis_controller import AnalysisController
from .contracts import DesktopApplicationAdapter, UiError
from .design_system.components import AppShell, DesignButton, Sidebar
from .design_system.tokens import DEFAULT_TOKENS
from .knowledge_controller import KnowledgeController
from .pages import PageHost
from .presentation import ShellViewState
from .presentation_state import PageId, PresentationState
from .presentation_store import PresentationStore
from .reference_controller import ReferenceController
from .report_controller import ReportController
from .settings_controller import SettingsController
from .shell_surfaces import (
    NotificationSurface,
    OperationStatusSurface,
    ProductIdentity,
    RuntimeStatusSurface,
)
from .state import ApplicationLifecycle, ApplicationState, ApplicationStateStore
from .workers import WorkerExecutor


class MainWindow(QMainWindow):
    recovery_action_requested = Signal(str, str)

    def __init__(
        self,
        view_state: ShellViewState,
        state_store: ApplicationStateStore,
        presentation_store: PresentationStore,
        application_adapter: DesktopApplicationAdapter,
        executor: WorkerExecutor,
    ) -> None:
        super().__init__()
        self._state_store = state_store
        self._presentation_store = presentation_store
        self._analysis_controller = AnalysisController(
            application_adapter,
            presentation_store,
            executor,
        )
        self._reference_controller = ReferenceController(
            application_adapter,
            presentation_store,
            executor,
        )
        self._knowledge_controller = KnowledgeController(
            application_adapter,
            presentation_store,
            executor,
        )
        self._report_controller = ReportController(
            application_adapter,
            presentation_store,
            executor,
        )
        self._settings_controller = SettingsController(
            application_adapter,
            presentation_store,
            executor,
        )
        tokens = DEFAULT_TOKENS
        self.setObjectName("desktopMainWindow")
        self.setWindowTitle(view_state.window_title)
        self.setMinimumSize(
            tokens.controls.window_minimum_width,
            tokens.controls.window_minimum_height,
        )
        self.resize(
            tokens.controls.window_default_width,
            tokens.controls.window_default_height,
        )

        self._navigation = Sidebar(tokens=tokens)
        self._navigation.setObjectName("primaryNavigation")
        self._navigation.setMinimumWidth(0)
        self._navigation.setMaximumWidth(16777215)
        for navigation_item in view_state.navigation_items:
            item = QListWidgetItem(navigation_item.label)
            item.setData(Qt.ItemDataRole.UserRole, navigation_item.page_id.value)
            item.setToolTip(navigation_item.label)
            self._navigation.addItem(item)

        self._settings_button = DesignButton("Settings", tokens=tokens)
        self._settings_button.setObjectName("settingsEntry")
        self._settings_button.clicked.connect(
            lambda _checked=False: self._presentation_store.navigate(PageId.SETTINGS)
        )

        sidebar_container = QWidget()
        sidebar_container.setObjectName("shellSidebar")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(
            tokens.spacing.md,
            tokens.spacing.lg,
            tokens.spacing.md,
            tokens.spacing.md,
        )
        sidebar_layout.setSpacing(tokens.spacing.md)
        sidebar_layout.addWidget(ProductIdentity(view_state.metadata, tokens=tokens))
        sidebar_layout.addWidget(self._navigation, 1)
        sidebar_layout.addWidget(self._settings_button)
        sidebar_container.setFixedWidth(tokens.controls.sidebar_width)

        self._runtime_surface = RuntimeStatusSurface(tokens=tokens)
        self._runtime_surface.activated.connect(
            lambda: self._presentation_store.navigate(PageId.RUNTIME_STATUS)
        )
        top_bar = QFrame()
        top_bar.setObjectName("globalTopBar")
        top_bar.setProperty("component", "panel")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(
            tokens.spacing.lg,
            tokens.spacing.sm,
            tokens.spacing.lg,
            tokens.spacing.sm,
        )
        top_layout.addStretch(1)
        top_layout.addWidget(self._runtime_surface)

        self._notifications = NotificationSurface(tokens=tokens)
        self._notifications.dismissed.connect(self._presentation_store.dismiss_notification)
        self._notifications.recovery_requested.connect(self._handle_recovery_action)
        self._page_host = PageHost(tokens=tokens)
        self._page_host.navigation_requested.connect(self._presentation_store.navigate)
        self._page_host.analysis_requested.connect(self._analysis_controller.execute)
        self._page_host.reference_comparison_requested.connect(self._reference_controller.execute)
        self._page_host.knowledge_search_requested.connect(self._knowledge_controller.execute)
        self._page_host.report_preview_requested.connect(self._report_controller.preview)
        self._page_host.report_export_requested.connect(self._report_controller.export)
        self._page_host.report_open_directory_requested.connect(
            self._report_controller.open_directory
        )
        self._page_host.settings_refresh_requested.connect(
            self._settings_controller.refresh_settings
        )
        self._page_host.runtime_refresh_requested.connect(self._settings_controller.refresh_runtime)
        self._page_host.session_audio_selected.connect(self._presentation_store.select_audio)
        self._page_host.session_references_selected.connect(
            self._presentation_store.select_references
        )
        self._page_host.session_report_selected.connect(self._presentation_store.select_report)
        self._page_host.recovery_requested.connect(self._handle_page_recovery_action)
        self._page_host.voice_interruption_requested.connect(
            self._presentation_store.request_voice_interruption
        )
        self._page_host.voice_plan_confirmation_recorded.connect(
            self._presentation_store.record_agent_confirmation
        )
        self._operation_surface = OperationStatusSurface(tokens=tokens)
        self._operation_surface.cancel_requested.connect(
            self._presentation_store.request_cancellation
        )

        workspace = QWidget()
        workspace.setObjectName("centralWorkspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(
            tokens.spacing.lg,
            tokens.spacing.lg,
            tokens.spacing.lg,
            tokens.spacing.md,
        )
        workspace_layout.setSpacing(tokens.spacing.md)
        workspace_layout.addWidget(top_bar)
        workspace_layout.addWidget(self._notifications)
        workspace_layout.addWidget(self._page_host, 1)
        workspace_layout.addWidget(self._operation_surface)

        self.setCentralWidget(AppShell(sidebar_container, workspace, tokens=tokens))
        self.statusBar().setObjectName("applicationStatus")
        self.statusBar().showMessage(view_state.status_message)
        self._navigation.currentItemChanged.connect(self._navigate)
        self._state_store.subscribe(self._render_application_state)
        self._presentation_store.subscribe(self._render_presentation_state)
        self._settings_controller.refresh_settings()

    def show_error(self, error: UiError) -> None:
        self.statusBar().showMessage(error.user_message)
        self._presentation_store.add_error(error)

    def _handle_recovery_action(self, notification_id: str, action_id: str) -> None:
        handled = self._route_recovery_action(action_id)
        if handled:
            self._presentation_store.dismiss_notification(notification_id)
        self.recovery_action_requested.emit(notification_id, action_id)

    def _handle_page_recovery_action(self, action_id: str) -> None:
        self._route_recovery_action(action_id)
        self.recovery_action_requested.emit("", action_id)

    def _route_recovery_action(self, action_id: str) -> bool:
        navigation = {
            "open_settings": PageId.SETTINGS,
            "select_audio": PageId.ANALYZE,
            "select_references": PageId.REFERENCES,
            "open_knowledge": PageId.KNOWLEDGE,
            "open_reports": PageId.REPORTS,
            "choose_export_destination": PageId.REPORTS,
            "open_runtime_status": PageId.RUNTIME_STATUS,
        }
        handled = action_id in navigation or action_id in {
            "retry_settings",
            "refresh_runtime",
        }
        if action_id in navigation:
            self._presentation_store.navigate(navigation[action_id])
        elif action_id == "retry_settings":
            self._presentation_store.navigate(PageId.SETTINGS)
            self._settings_controller.refresh_settings()
        elif action_id == "refresh_runtime":
            self._presentation_store.navigate(PageId.RUNTIME_STATUS)
            self._settings_controller.refresh_runtime()
        return handled

    def _render_application_state(self, state: ApplicationState) -> None:
        self.statusBar().showMessage(state.status_message)

    def _navigate(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is not None:
            self._presentation_store.navigate(PageId(current.data(Qt.ItemDataRole.UserRole)))

    def _render_presentation_state(self, state: PresentationState) -> None:
        page = state.navigation.current_page
        self._page_host.render(state)
        self._page_host.show_page(page)
        with QSignalBlocker(self._navigation):
            for row in range(self._navigation.count()):
                item = self._navigation.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == page.value:
                    self._navigation.setCurrentRow(row)
                    break
        self._runtime_surface.render(state.runtime)
        self._operation_surface.render(state.operation)
        self._notifications.render(state.notifications)

    def closeEvent(self, event) -> None:
        self._state_store.set_lifecycle(ApplicationLifecycle.STOPPED, "Stopped")
        super().closeEvent(event)
