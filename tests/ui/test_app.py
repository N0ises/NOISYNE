from __future__ import annotations

from PySide6.QtWidgets import QApplication

from brain.ui.app import build_main_window, create_application, run
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


def test_application_startup_and_shutdown_smoke(fake_adapter) -> None:
    assert run(["--smoke-test"], adapter=fake_adapter) == 0
    assert QApplication.instance() is not None
