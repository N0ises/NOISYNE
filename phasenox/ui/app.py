"""Desktop application bootstrap and QApplication lifecycle."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication

from .adapters import V2ApplicationAdapter
from .brand_resources import application_icon
from .contracts import DesktopApplicationAdapter, ProductMetadata, RuntimeStatus, UiError
from .design_system.theme import apply_theme
from .errors import ExceptionBoundary, unexpected_error
from .first_launch import recover_data_root_interactively
from .job_gateway import DesktopJobGateway
from .logging_setup import configure_logging
from .main_window import MainWindow
from .packaging_probe import run_packaging_probe
from .paths import initialize_desktop_state
from .presentation import build_shell_view_state
from .presentation_state import NotificationLevel, PresentationState
from .presentation_store import PresentationStore
from .session_persistence import SessionPersistenceBinding, SessionRepository
from .startup import (
    DesktopStartupMode,
    SessionChoice,
    activate_backend_root,
    prepare_desktop_startup,
)
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
    parser.add_argument(
        "--packaged-analysis",
        type=Path,
        help="Analyze a supplied audio fixture during the packaging probe.",
    )
    parser.add_argument(
        "--packaged-analysis-report",
        type=Path,
        help="Write the packaging probe analysis report to this path.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        help="Explicitly select an existing PHASENOX Data Root for this user.",
    )
    parser.add_argument(
        "--temporary-session",
        action="store_true",
        help="Start without persistent backend services or a fallback Data Root.",
    )
    parser.add_argument(
        "--session-choice",
        choices=tuple(item.value for item in SessionChoice),
        help="Explicitly recover from the legacy or canonical Desktop session.",
    )
    return parser


def create_qt_runtime() -> QApplication:
    application = QApplication.instance()
    if application is None:
        application = QApplication([sys.argv[0]])
    if not isinstance(application, QApplication):
        raise TypeError("A non-GUI QCoreApplication already exists.")
    return application


def apply_application_identity(
    application: QApplication, metadata: ProductMetadata
) -> QApplication:
    """Make canonical identity authoritative after startup resolution."""

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


def create_application(metadata: ProductMetadata) -> QApplication:
    """Create an already-resolved application for embedding and focused tests."""
    return apply_application_identity(create_qt_runtime(), metadata)


def build_main_window(
    adapter: DesktopApplicationAdapter,
    state_store: ApplicationStateStore | None = None,
    presentation_store: PresentationStore | None = None,
    executor: WorkerExecutor | None = None,
    job_gateway: DesktopJobGateway | None = None,
) -> MainWindow:
    store = state_store or ApplicationStateStore()
    ui_store = presentation_store or PresentationStore()
    view_state = build_shell_view_state(adapter.product_metadata(), ui_store.state.navigation)
    worker_executor = executor or WorkerExecutor()
    window = MainWindow(
        view_state,
        store,
        ui_store,
        adapter,
        worker_executor,
        job_gateway,
    )
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
    application_adapter = adapter or V2ApplicationAdapter()
    metadata = application_adapter.product_metadata()
    application = create_qt_runtime()
    startup = prepare_desktop_startup(
        application_version=metadata.version,
        requested_data_root=options.data_root,
        temporary=options.temporary_session,
        session_choice=(SessionChoice(options.session_choice) if options.session_choice else None),
    )
    if startup.mode is DesktopStartupMode.RECOVERY_REQUIRED:
        startup = recover_data_root_interactively(
            startup,
            application_version=metadata.version,
        )
    if startup.mode is DesktopStartupMode.RECOVERY_REQUIRED:
        intents = ", ".join(item.value for item in startup.recovery_intents)
        print(
            f"PHASENØX startup blocked: {startup.reason or 'recovery is required'}"
            f" Available actions: {intents}",
            file=sys.stderr,
        )
        return 2
    application = apply_application_identity(application, metadata)
    if startup.mode is DesktopStartupMode.TEMPORARY:
        print(
            "PHASENØX temporary session mode: persistent backend services are disabled.",
            file=sys.stderr,
        )
        return 0

    activate_backend_root(startup)
    state_layout = initialize_desktop_state(startup.locations.canonical_root)
    configure_logging(state_layout.root)

    if startup.active_session_path is None:  # pragma: no cover - guarded by startup mode
        raise RuntimeError("Persistent startup did not select a Desktop session.")
    repository = session_repository or SessionRepository(startup.active_session_path)
    loaded = repository.load()
    presentation_store = PresentationStore(PresentationState.from_session(loaded.session))
    if loaded.warning:
        presentation_store.add_notification(NotificationLevel.WARNING, loaded.warning)
    session_binding = SessionPersistenceBinding(repository, presentation_store)

    executor = WorkerExecutor()
    job_gateway = DesktopJobGateway()
    job_gateway.start()
    state_store = ApplicationStateStore()
    window = build_main_window(
        application_adapter,
        state_store,
        presentation_store,
        executor,
        job_gateway,
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
            lambda: run_packaging_probe(
                options.packaging_probe,
                metadata,
                adapter=application_adapter,
                state_root=state_layout.root,
                audio_path=options.packaged_analysis,
                report_path=options.packaged_analysis_report,
            ),
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
        # Desktop Core work is deterministic and bounded. Waiting prevents
        # executor threads from surviving the Qt/application teardown.
        job_gateway.shutdown(wait=True)
        executor.wait_for_done()
        boundary.uninstall()
        session_binding.save_current()
        session_binding.close()
    return exit_code or qt_exit_code


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
