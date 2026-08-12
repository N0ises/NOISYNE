from __future__ import annotations

from PySide6.QtWidgets import QApplication, QListWidget

from brain.ui.app import build_main_window, create_application, run
from brain.ui.presentation_state import NAVIGATION_ORDER, PageId, SessionState
from brain.ui.presentation_store import PresentationStore
from brain.ui.session_persistence import SessionRepository
from brain.ui.state import ApplicationStateStore


def test_create_application_uses_stable_metadata(product_metadata) -> None:
    application = create_application(product_metadata)

    assert application.applicationName() == product_metadata.application_id
    assert application.applicationDisplayName() == product_metadata.display_name
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
    assert navigation.count() == len(NAVIGATION_ORDER)


def test_navigation_selection_updates_presentation_and_session(qtbot, fake_adapter) -> None:
    presentation_store = PresentationStore()
    window = build_main_window(
        fake_adapter,
        ApplicationStateStore(),
        presentation_store,
    )
    qtbot.addWidget(window)
    navigation = window.findChild(QListWidget, "primaryNavigation")

    navigation.setCurrentRow(NAVIGATION_ORDER.index(PageId.REPORTS))

    assert presentation_store.state.navigation.current_page is PageId.REPORTS
    assert presentation_store.state.session.navigation.current_page is PageId.REPORTS


def test_page_selections_update_shared_session_immediately(qtbot, fake_adapter, tmp_path) -> None:
    presentation_store = PresentationStore()
    window = build_main_window(fake_adapter, ApplicationStateStore(), presentation_store)
    qtbot.addWidget(window)
    source = tmp_path / "source.wav"
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    analyze = window._page_host.page(PageId.ANALYZE)
    references = window._page_host.page(PageId.REFERENCES)

    analyze.select_source(source)
    references.add_references((first, second, first))

    assert presentation_store.state.session.selected_audio == source
    assert presentation_store.state.session.selected_references == (first, second)


def test_application_startup_and_shutdown_smoke(fake_adapter, tmp_path) -> None:
    repository = SessionRepository(tmp_path / "desktop-session.json")

    assert run(["--smoke-test"], adapter=fake_adapter, session_repository=repository) == 0
    assert QApplication.instance() is not None
    assert repository.path.exists()


def test_application_restart_restores_safe_session_context(fake_adapter, tmp_path) -> None:
    repository = SessionRepository(tmp_path / "desktop-session.json")
    missing = tmp_path / "missing.wav"
    repository.save(SessionState().navigate(PageId.REPORTS).select_audio(missing))

    assert run(["--smoke-test"], adapter=fake_adapter, session_repository=repository) == 0
    assert run(["--smoke-test"], adapter=fake_adapter, session_repository=repository) == 0

    restored = repository.load().session
    assert restored.navigation.current_page is PageId.REPORTS
    assert restored.selected_audio == missing
