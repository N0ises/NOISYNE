"""Minimal Qt Widgets shell for Sprint 1."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from .contracts import UiError
from .presentation import ShellViewState
from .state import ApplicationLifecycle, ApplicationState, ApplicationStateStore


class MainWindow(QMainWindow):
    def __init__(self, view_state: ShellViewState, state_store: ApplicationStateStore) -> None:
        super().__init__()
        self._state_store = state_store
        self.setObjectName("desktopMainWindow")
        self.setWindowTitle(view_state.window_title)
        self.resize(960, 640)

        navigation = QListWidget()
        navigation.setObjectName("primaryNavigation")
        navigation.addItems(view_state.navigation_items)
        navigation.setFixedWidth(180)
        navigation.setCurrentRow(0)

        heading = QLabel(view_state.heading)
        heading.setObjectName("workspaceHeading")
        heading.setAlignment(Qt.AlignmentFlag.AlignLeft)
        heading.setStyleSheet("font-size: 24px; font-weight: 600;")

        body = QLabel(view_state.body)
        body.setObjectName("workspaceBody")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        workspace_layout = QVBoxLayout()
        workspace_layout.addWidget(heading)
        workspace_layout.addWidget(body, 1)
        workspace = QWidget()
        workspace.setObjectName("centralWorkspace")
        workspace.setLayout(workspace_layout)

        shell_layout = QHBoxLayout()
        shell_layout.addWidget(navigation)
        shell_layout.addWidget(workspace, 1)
        shell = QWidget()
        shell.setLayout(shell_layout)
        self.setCentralWidget(shell)

        self.statusBar().setObjectName("applicationStatus")
        self.statusBar().showMessage(view_state.status_message)
        self._state_store.subscribe(self._render_application_state)

    def show_error(self, error: UiError) -> None:
        self.statusBar().showMessage(error.user_message)

    def _render_application_state(self, state: ApplicationState) -> None:
        self.statusBar().showMessage(state.status_message)

    def closeEvent(self, event) -> None:
        self._state_store.set_lifecycle(ApplicationLifecycle.STOPPED, "Stopped")
        super().closeEvent(event)
