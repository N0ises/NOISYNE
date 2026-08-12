"""Minimal Qt Widgets shell bound to the Sprint 2 presentation state."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from .contracts import UiError
from .design_system.components import AppShell, PageHeader, Sidebar
from .design_system.gallery import ComponentGallery
from .design_system.tokens import DEFAULT_TOKENS
from .presentation import ShellViewState
from .presentation_state import PageId, PresentationState
from .presentation_store import PresentationStore
from .state import ApplicationLifecycle, ApplicationState, ApplicationStateStore


class MainWindow(QMainWindow):
    def __init__(
        self,
        view_state: ShellViewState,
        state_store: ApplicationStateStore,
        presentation_store: PresentationStore,
    ) -> None:
        super().__init__()
        self._state_store = state_store
        self._presentation_store = presentation_store
        self._navigation_items = view_state.navigation_items
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
        for navigation_item in view_state.navigation_items:
            item = QListWidgetItem(navigation_item.label)
            item.setData(Qt.ItemDataRole.UserRole, navigation_item.page_id.value)
            self._navigation.addItem(item)
        self._page_header = PageHeader(view_state.heading, view_state.body, tokens=tokens)
        self._page_header.setObjectName("workspaceHeading")

        self._body = QLabel(view_state.body)
        self._body.setObjectName("workspaceBody")
        self._body.setWordWrap(True)
        self._body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        workspace_layout = QVBoxLayout()
        workspace_layout.setContentsMargins(
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
        )
        workspace_layout.setSpacing(tokens.spacing.lg)
        workspace_layout.addWidget(self._page_header)
        workspace_layout.addWidget(self._body)
        workspace_layout.addWidget(ComponentGallery(tokens=tokens), 1)
        workspace = QWidget()
        workspace.setObjectName("centralWorkspace")
        workspace.setLayout(workspace_layout)

        self.setCentralWidget(AppShell(self._navigation, workspace, tokens=tokens))

        self.statusBar().setObjectName("applicationStatus")
        self.statusBar().showMessage(view_state.status_message)
        self._navigation.currentItemChanged.connect(self._navigate)
        self._state_store.subscribe(self._render_application_state)
        self._presentation_store.subscribe(self._render_presentation_state)

    def show_error(self, error: UiError) -> None:
        self.statusBar().showMessage(error.user_message)

    def _render_application_state(self, state: ApplicationState) -> None:
        self.statusBar().showMessage(state.status_message)

    def _navigate(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is not None:
            self._presentation_store.navigate(PageId(current.data(Qt.ItemDataRole.UserRole)))

    def _render_presentation_state(self, state: PresentationState) -> None:
        page = state.navigation.current_page
        label = next(item.label for item in self._navigation_items if item.page_id is page)
        self._page_header.set_title(label)
        self._page_header.set_subtitle(f"{label} foundation is ready.")
        self._body.setText(f"{label} foundation is ready.")
        for row in range(self._navigation.count()):
            item = self._navigation.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == page.value:
                if self._navigation.currentRow() != row:
                    self._navigation.setCurrentRow(row)
                break

    def closeEvent(self, event) -> None:
        self._state_store.set_lifecycle(ApplicationLifecycle.STOPPED, "Stopped")
        super().closeEvent(event)
