from __future__ import annotations

from PySide6.QtWidgets import QApplication, QListWidget

from brain.ui.app import build_main_window, create_application, run
from brain.ui.presentation_state import PageId
from brain.ui.presentation_store import PresentationStore
from brain.ui.session_persistence import SessionRepository
from brain.ui.state import ApplicationStateStore


def test_create_application_uses_stable_metadata(product_metadata) -> None:
    application = create_application(product_metadata)

    assert application.applicationName() == product_metadata.application_id
    assert application.applicationVersion() == product_metadata.version
    assert application.organizationName() == product_metadata.organization_name


def test_main_window_construction_uses_central_title(qtbot, fake_adapter) -> None:
    window = build_main_window(fake_adapter, ApplicationStateStore())
    qtbot.addWidget(window)

    assert window.windowTitle() == fake_adapter.product_metadata().application_title
    assert window.findChild(object, "primaryNavigation") is not None
    assert window.findChild(object, "centralWorkspace") is not None
    assert window.findChild(object, "applicationStatus") is not None
    navigation = window.findChild(QListWidget, "primaryNavigation")
    assert navigation is not None
    assert navigation.count() == 8


def test_navigation_selection_updates_presentation_and_session(qtbot, fake_adapter) -> None:
    presentation_store = PresentationStore()
    window = build_main_window(
        fake_adapter,
        ApplicationStateStore(),
        presentation_store,
    )
    qtbot.addWidget(window)
    navigation = window.findChild(QListWidget, "primaryNavigation")

    navigation.setCurrentRow(5)

    assert presentation_store.state.navigation.current_page is PageId.REPORTS
    assert presentation_store.state.session.navigation.current_page is PageId.REPORTS


def test_application_startup_and_shutdown_smoke(fake_adapter, tmp_path) -> None:
    repository = SessionRepository(tmp_path / "desktop-session.json")

    assert run(["--smoke-test"], adapter=fake_adapter, session_repository=repository) == 0
    assert QApplication.instance() is not None
    assert repository.path.exists()
