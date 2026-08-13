"""Desktop application bootstrap and QApplication lifecycle."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication

from .adapters import V1ApplicationAdapter
from .brand_resources import application_icon
from .contracts import DesktopApplicationAdapter, ProductMetadata, RuntimeStatus, UiError
from .design_system.theme import apply_theme
from .errors import ExceptionBoundary, unexpected_error
from .logging_setup import configure_logging
from .main_window import MainWindow
from .packaging_probe import run_packaging_probe
from .paths import prepare_packaged_runtime, session_state_path
from .presentation import build_shell_view_state
from .presentation_state import NotificationLevel, PresentationState
from .presentation_store import PresentationStore
from .session_persistence import SessionPersistenceBinding, SessionRepository
from .state import ApplicationLifecycle, ApplicationStateStore
from .worker_binding import WorkerStateBinding
from .workers import WorkerExecutor

logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the desktop application.")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Show the shell, process events, and close cleanly.",
    )
    parser.add_argument(
        "--packaging-probe",
        type=Path,
        help="Run representative packaged-runtime checks and write JSON results.",
    )
    return parser


def create_application(metadata: ProductMetadata) -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication([sys.argv[0]])
    if not isinstance(application, QApplication):
        raise TypeError("A non-GUI QCoreApplication already exists.")

    QCoreApplication.setApplicationName(metadata.application_id)
    application.setApplicationDisplayName(metadata.display_name)
    QCoreApplication.setApplicationVersion(metadata.version)
    QCoreApplication.setOrganizationName(metadata.organization_name)
    if metadata.organization_domain:
        QCoreApplication.setOrganizationDomain(metadata.organization_domain)
    icon = application_icon()
    if not icon.isNull():
        application.setWindowIcon(icon)
    apply_theme(application)
    return application


def build_main_window(
    adapter: DesktopApplicationAdapter,
    state_store: ApplicationStateStore | None = None,
    presentation_store: PresentationStore | None = None,
    executor: WorkerExecutor | None = None,
) -> MainWindow:
    store = state_store or ApplicationStateStore()
    ui_store = presentation_store or PresentationStore()
    view_state = build_shell_view_state(adapter.product_metadata(), ui_store.state.navigation)
    worker_executor = executor or WorkerExecutor()
    window = MainWindow(view_state, store, ui_store, adapter, worker_executor)
    icon = application_icon()
    if not icon.isNull():
        window.setWindowIcon(icon)
    return window


def run(
    argv: Sequence[str] | None = None,
    *,
    adapter: DesktopApplicationAdapter | None = None,
    session_repository: SessionRepository | None = None,
) -> int:
    options = _parser().parse_args(argv)
    application_adapter = adapter or V1ApplicationAdapter()
    metadata = application_adapter.product_metadata()
    application = create_application(metadata)
    try:
        prepare_packaged_runtime()
    except OSError as exc:
        # The shell can still surface session/path errors through its resilience
        # layer; retain a safe stderr diagnostic for pre-window failures.
        print(f"NØISYNE could not initialize its user-data directories: {exc}", file=sys.stderr)
    configure_logging()

    repository = session_repository or SessionRepository(session_state_path())
    loaded = repository.load()
    presentation_store = PresentationStore(PresentationState.from_session(loaded.session))
    if loaded.warning:
        presentation_store.add_notification(NotificationLevel.WARNING, loaded.warning)
    session_binding = SessionPersistenceBinding(repository, presentation_store)

    executor = WorkerExecutor()
    state_store = ApplicationStateStore()
    window = build_main_window(
        application_adapter,
        state_store,
        presentation_store,
        executor,
    )
    boundary = ExceptionBoundary(window.show_error)
    boundary.install()
    state_store.set_lifecycle(ApplicationLifecycle.READY, "Ready")
    window.show()

    exit_code = 0

    def accept_runtime_status(result: object) -> None:
        if isinstance(result, RuntimeStatus):
            presentation_store.set_runtime_status(result)
            return
        presentation_store.set_runtime_unknown()
        presentation_store.add_error(
            unexpected_error(TypeError("Adapter returned an invalid runtime status DTO."))
        )

    def fail_runtime_status(error: UiError) -> None:
        presentation_store.set_runtime_unknown()
        presentation_store.add_error(error)

    presentation_store.set_runtime_loading()
    runtime_task = executor.create("runtime_status", application_adapter.runtime_status)
    runtime_task.signals.succeeded.connect(accept_runtime_status)
    runtime_task.signals.failed.connect(fail_runtime_status)
    executor.start(runtime_task)

    def fail_probe(error: UiError) -> None:
        nonlocal exit_code
        exit_code = 1
        logger.error("Packaging probe failed: %s", error.technical_detail)
        window.show_error(error)

    if options.packaging_probe is not None:
        task = executor.create(
            "packaging_probe",
            lambda: run_packaging_probe(options.packaging_probe, metadata),
        )
        WorkerStateBinding(presentation_store).bind(task)
        task.signals.failed.connect(fail_probe)
        task.signals.finished.connect(lambda _operation_id: window.close())
        executor.start(task)
    elif options.smoke_test:
        QTimer.singleShot(100, window.close)

    try:
        qt_exit_code = application.exec()
    finally:
        executor.wait_for_done()
        boundary.uninstall()
        session_binding.save_current()
        session_binding.close()
    return exit_code or qt_exit_code


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
