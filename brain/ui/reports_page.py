"""Persistent descriptor-backed Reports workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .contracts import ReportDescriptor, ReportExportCommand
from .design_system.components import ButtonVariant, Card, DesignButton, PageHeader, StatusBadge
from .design_system.semantics import VisualState
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import PageId, PresentationState, RecentReport, ResultPhase

_SUPPORTED_FORMATS = {
    "analysis": frozenset({"json"}),
    "reference_comparison": frozenset({"json", "markdown"}),
}
_EXTENSIONS = {"json": ".json", "markdown": ".md"}


class ReportsPage(QScrollArea):
    preview_requested = Signal(object)
    export_requested = Signal(object)
    open_directory_requested = Signal(object)
    page_id = PageId.REPORTS

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-reports")
        self.setAccessibleName("Reports workspace")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._tokens = tokens
        self._reports_signature: tuple = ()
        self._selected: RecentReport | None = None

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl
        )
        layout.setSpacing(tokens.spacing.lg)
        layout.addWidget(
            PageHeader(
                "Reports",
                "Preview and copy real report artifacts retained by this session.",
                tokens=tokens,
            )
        )

        list_card = Card("Available reports", tokens=tokens)
        self.report_list = QListWidget()
        self.report_list.setObjectName("reportList")
        self.report_list.setAccessibleName("Available reports")
        self.empty_label = QLabel("No generated reports are known to this session.")
        self.empty_label.setObjectName("reportsEmptyState")
        self.empty_label.setWordWrap(True)
        list_card.content_layout.addWidget(self.empty_label)
        list_card.content_layout.addWidget(self.report_list)
        layout.addWidget(list_card)

        metadata_card = Card("Report metadata", tokens=tokens)
        self.metadata_label = QLabel("Select a report to inspect its metadata.")
        self.metadata_label.setObjectName("reportMetadata")
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        metadata_card.content_layout.addWidget(self.metadata_label)
        layout.addWidget(metadata_card)

        actions_card = Card("Safe actions", tokens=tokens)
        actions = QHBoxLayout()
        self.copy_content_button = DesignButton("Copy content", tokens=tokens)
        self.copy_path_button = DesignButton("Copy path", tokens=tokens)
        self.open_folder_button = DesignButton("Open containing folder", tokens=tokens)
        self.export_button = DesignButton(
            "Export copy", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        for button in (
            self.copy_content_button,
            self.copy_path_button,
            self.open_folder_button,
            self.export_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        actions_card.content_layout.addLayout(actions)
        layout.addWidget(actions_card)

        status_card = Card("Report operation", tokens=tokens)
        self.status_badge = StatusBadge("Idle", VisualState.IDLE)
        self.status_message = QLabel("Select a report to load its preview.")
        self.status_message.setObjectName("reportStatusMessage")
        self.status_message.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setObjectName("reportProgress")
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        status_card.content_layout.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignLeft)
        status_card.content_layout.addWidget(self.status_message)
        status_card.content_layout.addWidget(self.progress)
        layout.addWidget(status_card)

        viewer_card = Card("Report viewer", tokens=tokens)
        self.viewer = QTextEdit()
        self.viewer.setObjectName("reportViewer")
        self.viewer.setReadOnly(True)
        self.viewer.setAcceptRichText(False)
        self.viewer.setPlaceholderText("Select an existing supported report to preview it.")
        viewer_card.content_layout.addWidget(self.viewer)
        layout.addWidget(viewer_card)
        layout.addStretch(1)
        self.setWidget(content)

        self.report_list.currentItemChanged.connect(self._select_report)
        self.copy_content_button.clicked.connect(self._copy_content)
        self.copy_path_button.clicked.connect(self._copy_path)
        self.open_folder_button.clicked.connect(self._open_folder)
        self.export_button.clicked.connect(self._choose_export)
        self._update_actions()

    @property
    def selected_report(self) -> RecentReport | None:
        return self._selected

    def render(self, state: PresentationState) -> None:
        self._sync_reports(state.session.recent_reports)
        if (
            state.navigation.current_page is PageId.REPORTS
            and self._selected is None
            and self.report_list.count()
        ):
            self.report_list.setCurrentRow(0)
        preview_state = state.report_preview
        preview = preview_state.preview
        if (
            preview is not None
            and self._selected is not None
            and preview.descriptor.path == self._selected.descriptor.path
        ):
            if preview.content is not None:
                self.viewer.setPlainText(preview.content)
            else:
                self.viewer.clear()
            self._render_metadata(self._selected, preview)

        if preview_state.phase is ResultPhase.LOADING:
            self._set_status(
                "Loading", VisualState.RUNNING, "Loading report preview. Progress is indeterminate."
            )
        elif preview_state.phase in {ResultPhase.SUCCESS, ResultPhase.WARNING} and preview:
            message = preview.unavailable_reason or (
                preview.warnings[0] if preview.warnings else "Report preview loaded."
            )
            visual = (
                VisualState.WARNING
                if preview_state.phase is ResultPhase.WARNING
                else VisualState.SUCCESS
            )
            self._set_status("Preview ready", visual, message)
        elif preview_state.phase is ResultPhase.FAILURE:
            message = (
                preview_state.error.user_message
                if preview_state.error
                else "Report preview failed."
            )
            self._set_status("Preview failed", VisualState.ERROR, message)

        export_state = state.report_export
        if export_state.phase is ResultPhase.LOADING:
            self._set_status(
                "Exporting", VisualState.RUNNING, "Copying report bytes. Progress is indeterminate."
            )
        elif export_state.phase in {ResultPhase.SUCCESS, ResultPhase.WARNING}:
            self._set_status("Export complete", VisualState.SUCCESS, "Report copy completed.")
        elif export_state.phase is ResultPhase.FAILURE:
            message = (
                export_state.error.user_message if export_state.error else "Report export failed."
            )
            self._set_status("Export failed", VisualState.ERROR, message)

        busy = (
            preview_state.phase is ResultPhase.LOADING or export_state.phase is ResultPhase.LOADING
        )
        self.progress.setVisible(busy)
        self.report_list.setEnabled(not busy)
        self._update_actions(busy=busy)

    def _sync_reports(self, reports: tuple[RecentReport, ...]) -> None:
        signature = tuple(
            (
                item.descriptor.kind,
                item.descriptor.format,
                str(item.descriptor.path),
                item.descriptor.display_label,
                str(item.descriptor.source_path) if item.descriptor.source_path else None,
                item.created_at,
                item.descriptor.path.exists(),
            )
            for item in reports
        )
        if signature == self._reports_signature:
            return
        selected_path = self._selected.descriptor.path if self._selected else None
        self._reports_signature = signature
        self.report_list.clear()
        self._selected = None
        selected_row: int | None = None
        for row, report in enumerate(reports):
            exists = report.descriptor.path.exists() and report.descriptor.path.is_file()
            suffix = "" if exists else " — Missing"
            format_label = (
                report.descriptor.format.upper()
                if self._is_supported(report.descriptor)
                else "Unsupported format"
            )
            item = QListWidgetItem(f"{report.descriptor.display_label} [{format_label}]{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, report)
            self.report_list.addItem(item)
            if selected_path is not None and report.descriptor.path == selected_path:
                selected_row = row
        self.empty_label.setVisible(not reports)
        self.report_list.setVisible(bool(reports))
        if reports and selected_row is not None:
            self.report_list.setCurrentRow(selected_row)
        else:
            self.metadata_label.setText("Select a report to inspect its metadata.")
            self.viewer.clear()
            self._update_actions()

    def _select_report(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        report = current.data(Qt.ItemDataRole.UserRole) if current else None
        self._selected = report if isinstance(report, RecentReport) else None
        self.viewer.clear()
        if self._selected is None:
            self.metadata_label.setText("Select a report to inspect its metadata.")
            self._update_actions()
            return
        self._render_metadata(self._selected)
        self._update_actions()
        descriptor = self._selected.descriptor
        if (
            self._is_supported(descriptor)
            and descriptor.path.exists()
            and descriptor.path.is_file()
        ):
            self.preview_requested.emit(descriptor)
        elif not self._is_supported(descriptor):
            self._set_status(
                "Unsupported",
                VisualState.UNAVAILABLE,
                "This retained artifact is not a supported V1 Desktop report format.",
            )
        else:
            self._set_status(
                "Missing",
                VisualState.WARNING,
                "The report file is missing. Re-run its originating workflow if needed.",
            )

    def _render_metadata(self, report: RecentReport, preview=None) -> None:
        descriptor = report.descriptor
        exists = descriptor.path.exists() and descriptor.path.is_file()
        lines = [
            f"Label: {descriptor.display_label}",
            f"Kind: {descriptor.kind}",
            f"Format: {descriptor.format}",
            f"Path: {descriptor.path}",
            f"Status: {'Exists' if exists else 'Missing'}",
            f"Session recorded time: {report.created_at.isoformat()}",
        ]
        if descriptor.source_path is not None:
            lines.append(f"Source audio: {descriptor.source_path}")
        if preview is not None:
            lines.extend(
                (
                    f"File size: {preview.size_bytes} bytes",
                    f"Filesystem modified time: {preview.filesystem_modified_at.isoformat()}",
                )
            )
        self.metadata_label.setText("\n".join(lines))

    def _copy_content(self) -> None:
        QApplication.clipboard().setText(self.viewer.toPlainText())

    def _copy_path(self) -> None:
        if self._selected is not None:
            QApplication.clipboard().setText(str(self._selected.descriptor.path))

    def _open_folder(self) -> None:
        if self._selected is not None:
            self.open_directory_requested.emit(self._selected.descriptor.path.parent)

    def _choose_export(self) -> None:
        if self._selected is None:
            return
        descriptor = self._selected.descriptor
        extension = _EXTENSIONS.get(descriptor.format)
        if extension is None:
            return
        selected, _filter = QFileDialog.getSaveFileName(
            self,
            "Export report copy",
            str(descriptor.path.with_name(descriptor.path.stem + "-copy" + extension)),
            f"{descriptor.format.upper()} report (*{extension})",
        )
        if not selected:
            return
        destination = Path(selected)
        if not destination.suffix:
            destination = destination.with_suffix(extension)
        if destination.suffix.casefold() != extension:
            self._set_status(
                "Invalid destination",
                VisualState.ERROR,
                f"The destination must use the {extension} extension.",
            )
            return
        overwrite = False
        if destination.exists():
            response = QMessageBox.question(
                self,
                "Replace existing report?",
                f"Replace the existing file?\n{destination}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return
            overwrite = True
        self.export_requested.emit(
            ReportExportCommand(
                source=descriptor,
                destination_path=destination,
                overwrite=overwrite,
            )
        )

    def _update_actions(self, *, busy: bool = False) -> None:
        descriptor = self._selected.descriptor if self._selected else None
        exists = bool(descriptor and descriptor.path.exists() and descriptor.path.is_file())
        supported = bool(descriptor and self._is_supported(descriptor))
        has_content = bool(self.viewer.toPlainText())
        self.copy_content_button.setEnabled(not busy and has_content)
        self.copy_path_button.setEnabled(not busy and descriptor is not None)
        self.open_folder_button.setEnabled(
            not busy and bool(descriptor and descriptor.path.parent.is_dir())
        )
        self.export_button.setEnabled(not busy and exists and supported)

    def _set_status(self, label: str, visual: VisualState, message: str) -> None:
        self.status_badge.setText(label)
        self.status_badge.set_state(visual)
        self.status_message.setText(message)

    @staticmethod
    def _is_supported(descriptor: ReportDescriptor) -> bool:
        return descriptor.format in _SUPPORTED_FORMATS.get(descriptor.kind, frozenset())
