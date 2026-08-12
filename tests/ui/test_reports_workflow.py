from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from brain.ui.contracts import (
    AnalysisViewResult,
    IntelligenceSnapshot,
    KnowledgeSearchResult,
    ReferenceViewResult,
    ReportDescriptor,
    ReportExportCommand,
    ReportExportResult,
    ReportPreview,
    UiErrorCategory,
)
from brain.ui.pages import PageHost, PlaceholderPage
from brain.ui.presentation_state import (
    KnowledgeResultPresentationState,
    NavigationState,
    PageId,
    PresentationState,
    RecentReport,
    ReferenceResultPresentationState,
    ResultPhase,
    ResultPresentationState,
    SessionState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.report_controller import ReportController
from brain.ui.reports_page import ReportsPage
from brain.ui.workers import WorkerExecutor


class FakeReportAdapter:
    def __init__(self, *, preview=None, export_result=None, error=None, delay=0.0) -> None:
        self.preview_result = preview
        self.export_result = export_result
        self.error = error
        self.delay = delay
        self.preview_descriptor = None
        self.export_command = None
        self.thread_id = None

    def load_report(self, descriptor):
        self.preview_descriptor = descriptor
        self.thread_id = threading.get_ident()
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.preview_result

    def export_report(self, command):
        self.export_command = command
        self.thread_id = threading.get_ident()
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.export_result


def _recent(path: Path, *, kind="analysis", format="json", source=True) -> RecentReport:
    descriptor = ReportDescriptor(
        kind,
        format,
        path,
        path.name,
        Path("mix.wav") if source else None,
    )
    return RecentReport(descriptor, datetime(2026, 1, 2, 3, 4, tzinfo=UTC), path.exists())


def _preview(report: RecentReport, content="report content") -> ReportPreview:
    return ReportPreview(
        report.descriptor,
        content,
        len(content.encode()),
        datetime(2026, 1, 2, 5, 6, tzinfo=UTC),
    )


def test_reports_placeholder_replaced_and_selection_survives_navigation(qtbot, tmp_path) -> None:
    first = tmp_path / "analysis.json"
    second = tmp_path / "reference_report.md"
    first.write_text("{}", encoding="utf-8")
    second.write_text("# Reference", encoding="utf-8")
    host = PageHost()
    qtbot.addWidget(host)
    page = host.page(PageId.REPORTS)
    assert isinstance(page, ReportsPage)
    assert not isinstance(page, PlaceholderPage)
    page.render(
        PresentationState(
            session=SessionState(
                recent_reports=(
                    _recent(first),
                    _recent(second, kind="reference_comparison", format="markdown"),
                )
            )
        )
    )
    page.report_list.setCurrentRow(1)

    host.show_page(PageId.ANALYZE)
    host.show_page(PageId.REPORTS)

    assert host.page(PageId.REPORTS) is page
    assert page.selected_report.descriptor.path == second


def test_report_content_is_loaded_only_when_reports_workspace_is_open(qtbot, tmp_path) -> None:
    path = tmp_path / "analysis.json"
    path.write_text("{}", encoding="utf-8")
    page = ReportsPage()
    qtbot.addWidget(page)
    requested = []
    page.preview_requested.connect(requested.append)
    session = SessionState(recent_reports=(_recent(path),))

    page.render(PresentationState(session=session))
    assert requested == []
    assert page.selected_report is None

    page.render(
        PresentationState(
            navigation=NavigationState(current_page=PageId.REPORTS),
            session=session,
        )
    )
    assert requested == [session.recent_reports[0].descriptor]


def test_restored_report_selection_does_not_preload_until_workspace_is_open(
    qtbot, tmp_path
) -> None:
    path = tmp_path / "analysis.json"
    path.write_text("{}", encoding="utf-8")
    report = _recent(path)
    page = ReportsPage()
    qtbot.addWidget(page)
    requested = []
    page.preview_requested.connect(requested.append)
    session = SessionState(recent_reports=(report,), selected_report_path=path)

    page.render(PresentationState(session=session))
    page.render(PresentationState(session=session))
    assert page.selected_report == report
    assert requested == []

    page.render(
        PresentationState(
            navigation=NavigationState(current_page=PageId.REPORTS),
            session=session,
        )
    )
    page.render(
        PresentationState(
            navigation=NavigationState(current_page=PageId.REPORTS),
            session=session,
        )
    )
    assert requested == [report.descriptor]


def test_actual_descriptors_metadata_missing_state_and_unsupported_format(qtbot, tmp_path) -> None:
    analysis = tmp_path / "analysis.json"
    reference_json = tmp_path / "reference_report.json"
    reference_md = tmp_path / "reference_report.md"
    for path in (analysis, reference_json, reference_md):
        path.write_text("{}", encoding="utf-8")
    missing = tmp_path / "missing.json"
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"pdf")
    reports = (
        _recent(analysis),
        _recent(reference_json, kind="reference_comparison"),
        _recent(reference_md, kind="reference_comparison", format="markdown"),
        _recent(missing, source=False),
        _recent(fake_pdf, format="pdf"),
    )
    page = ReportsPage()
    qtbot.addWidget(page)
    requested = []
    page.preview_requested.connect(requested.append)
    page.render(PresentationState(session=SessionState(recent_reports=reports)))

    assert page.report_list.count() == 5
    assert "Missing" in page.report_list.item(3).text()
    page.report_list.setCurrentRow(0)
    assert requested[-1].path == analysis
    page.report_list.setCurrentRow(3)
    assert requested[-1].path != missing
    assert "Status: Missing" in page.metadata_label.text()
    assert "Source audio:" not in page.metadata_label.text()
    assert not page.export_button.isEnabled()

    page.report_list.setCurrentRow(4)
    assert page.status_badge.text() == "Unsupported"
    assert "PDF" not in page.report_list.item(4).text()
    assert not page.export_button.isEnabled()
    assert all(item.format != "pdf" for item in requested)


def test_preview_worker_is_bound_before_start_off_gui_and_indeterminate(qtbot, tmp_path) -> None:
    path = tmp_path / "analysis.json"
    path.write_text("{}", encoding="utf-8")
    report = _recent(path)
    adapter = FakeReportAdapter(preview=_preview(report), delay=0.15)
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    controller = ReportController(adapter, store, executor)
    creation_states = []
    controller.task_created.connect(
        lambda _task: creation_states.append(store.state.operation.state)
    )
    gui_thread = threading.get_ident()
    timer_fired = []
    QTimer.singleShot(20, lambda: timer_fired.append(True))

    controller.preview(report.descriptor)
    qtbot.waitUntil(lambda: store.state.operation.state.value == "running", timeout=1000)

    assert creation_states[0].value == "queued"
    assert store.state.operation.progress is None
    assert not store.state.operation.cancellable
    assert not store.request_cancellation()
    qtbot.waitUntil(lambda: bool(timer_fired), timeout=1000)
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()
    assert adapter.thread_id != gui_thread
    assert store.state.report_preview.preview.content == "report content"


def test_viewer_copy_content_path_and_open_folder_are_safe(qtbot, tmp_path) -> None:
    path = tmp_path / "analysis.json"
    path.write_text("{}", encoding="utf-8")
    report = _recent(path)
    page = ReportsPage()
    qtbot.addWidget(page)
    state = PresentationState(
        navigation=NavigationState(current_page=PageId.REPORTS),
        session=SessionState(recent_reports=(report,)),
        report_preview=PresentationState().report_preview.__class__(
            phase=ResultPhase.SUCCESS,
            preview=_preview(report, '{\n  "score": 91\n}'),
        ),
    )
    opened = []
    page.open_directory_requested.connect(opened.append)
    page.render(state)

    page.copy_content_button.click()
    assert QApplication.clipboard().text() == '{\n  "score": 91\n}'
    page.copy_path_button.click()
    assert QApplication.clipboard().text() == str(path)
    page.open_folder_button.click()
    assert opened == [tmp_path]
    assert "Session recorded time: 2026-01-02T03:04:00+00:00" in page.metadata_label.text()
    assert "Filesystem modified time: 2026-01-02T05:06:00+00:00" in page.metadata_label.text()
    assert "Source audio: mix.wav" in page.metadata_label.text()


def test_directory_open_failure_is_structured_without_os_shell(qtbot, tmp_path) -> None:
    store = PresentationStore()
    controller = ReportController(
        FakeReportAdapter(),
        store,
        WorkerExecutor(QThreadPool()),
        directory_opener=lambda path: False,
    )

    assert not controller.open_directory(tmp_path)
    assert store.state.notifications.active[-1].error.category is UiErrorCategory.REPORT_EXPORT


def test_native_export_choice_normalizes_extension_and_cancel_is_not_failure(
    qtbot, tmp_path, monkeypatch
) -> None:
    source = tmp_path / "analysis.json"
    source.write_text("{}", encoding="utf-8")
    page = ReportsPage()
    qtbot.addWidget(page)
    page.render(PresentationState(session=SessionState(recent_reports=(_recent(source),))))
    page.report_list.setCurrentRow(0)
    emitted = []
    page.export_requested.connect(emitted.append)

    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    page.export_button.click()
    assert emitted == []

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args: (str(tmp_path / "chosen-copy"), "JSON report (*.json)"),
    )
    page.export_button.click()
    assert emitted[-1].destination_path == tmp_path / "chosen-copy.json"
    assert not emitted[-1].overwrite


def test_overwrite_requires_confirmation(qtbot, tmp_path, monkeypatch) -> None:
    source = tmp_path / "analysis.json"
    destination = tmp_path / "existing.json"
    source.write_text("{}", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")
    page = ReportsPage()
    qtbot.addWidget(page)
    page.render(PresentationState(session=SessionState(recent_reports=(_recent(source),))))
    page.report_list.setCurrentRow(0)
    emitted = []
    page.export_requested.connect(emitted.append)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.No,
    )
    page.export_button.click()
    assert emitted == []

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    page.export_button.click()
    assert emitted[-1].overwrite


def test_successful_export_updates_session_with_real_descriptor(qtbot, tmp_path) -> None:
    source = tmp_path / "analysis.json"
    destination = tmp_path / "copy.json"
    source.write_text("{}", encoding="utf-8")
    report = _recent(source)
    exported = ReportDescriptor("analysis", "json", destination, destination.name, Path("mix.wav"))
    adapter = FakeReportAdapter(export_result=ReportExportResult(report.descriptor, exported))
    store = PresentationStore(PresentationState(session=SessionState(recent_reports=(report,))))
    executor = WorkerExecutor(QThreadPool())
    controller = ReportController(adapter, store, executor)
    gui_thread = threading.get_ident()

    controller.export(ReportExportCommand(report.descriptor, destination))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.report_export.phase is ResultPhase.SUCCESS
    assert adapter.thread_id != gui_thread
    assert store.state.session.recent_reports[0].descriptor == exported
    assert store.state.session.recent_reports[1].descriptor == report.descriptor


def test_export_failure_is_recoverable_and_preserves_every_other_result(qtbot, tmp_path) -> None:
    source = tmp_path / "analysis.json"
    source.write_text("{}", encoding="utf-8")
    report = _recent(source)
    analysis = AnalysisViewResult(
        Path("mix.wav"),
        "ok",
        "mix",
        90.0,
        "summary",
        intelligence=IntelligenceSnapshot(reasoning="retained"),
    )
    reference = ReferenceViewResult(Path("mix.wav"), (Path("ref.wav"),), "ok", 90.0, 0.9)
    knowledge = KnowledgeSearchResult("query")
    state = PresentationState(
        result=ResultPresentationState(phase=ResultPhase.SUCCESS, result=analysis),
        reference_result=ReferenceResultPresentationState(
            phase=ResultPhase.SUCCESS, result=reference
        ),
        knowledge_result=KnowledgeResultPresentationState(
            phase=ResultPhase.SUCCESS, result=knowledge
        ),
        session=SessionState(recent_reports=(report,)),
    )
    store = PresentationStore(state)
    executor = WorkerExecutor(QThreadPool())
    controller = ReportController(
        FakeReportAdapter(error=PermissionError("denied")), store, executor
    )

    controller.export(ReportExportCommand(report.descriptor, tmp_path / "copy.json"))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.report_export.phase is ResultPhase.FAILURE
    assert store.state.report_export.error.category is UiErrorCategory.REPORT_EXPORT
    assert store.state.report_export.error.retryable
    assert store.state.result.result is analysis
    assert store.state.reference_result.result is reference
    assert store.state.knowledge_result.result is knowledge
    assert store.state.session.recent_reports == (report,)
