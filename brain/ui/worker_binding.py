"""Translate existing Qt worker signals into ordered UI operation events."""

from __future__ import annotations

from .contracts import (
    AnalysisViewResult,
    KnowledgeSearchResult,
    OperationEvent,
    OperationHandle,
    OperationState,
    ReferenceViewResult,
    ReportExportResult,
    ReportPreview,
    UiError,
)
from .presentation_store import PresentationStore
from .workers import WorkerTask


class WorkerStateBinding:
    def __init__(self, store: PresentationStore) -> None:
        self._store = store

    def bind(
        self,
        task: WorkerTask,
        *,
        capture_analysis_result: bool = False,
        capture_reference_result: bool = False,
        capture_knowledge_result: bool = False,
        capture_report_preview: bool = False,
        capture_report_export: bool = False,
    ) -> None:
        operation_id = task.handle.operation_id
        sequence = 0
        self._store.begin_operation(
            task.handle,
            cancellable=False,
            tracks_result=capture_analysis_result,
            tracks_reference_result=capture_reference_result,
            tracks_knowledge_result=capture_knowledge_result,
            tracks_report_preview=capture_report_preview,
            tracks_report_export=capture_report_export,
        )

        def next_sequence() -> int:
            nonlocal sequence
            sequence += 1
            return sequence

        def started(handle: object) -> None:
            if not isinstance(handle, OperationHandle) or handle.operation_id != operation_id:
                return
            self._store.apply_operation_event(
                OperationEvent(
                    operation_id=operation_id,
                    sequence=next_sequence(),
                    state=OperationState.RUNNING,
                    stage="running",
                    cancellable=False,
                )
            )

        def succeeded(result: object) -> None:
            captured = (
                result
                if capture_analysis_result and isinstance(result, AnalysisViewResult)
                else None
            )
            if capture_reference_result and isinstance(result, ReferenceViewResult):
                captured = result
            if capture_knowledge_result and isinstance(result, KnowledgeSearchResult):
                captured = result
            if capture_report_preview and isinstance(result, ReportPreview):
                captured = result
            if capture_report_export and isinstance(result, ReportExportResult):
                captured = result
            self._store.apply_operation_event(
                OperationEvent(
                    operation_id=operation_id,
                    sequence=next_sequence(),
                    state=OperationState.COMPLETED,
                    stage="completed",
                    result=captured,
                )
            )

        def failed(error: UiError) -> None:
            self._store.apply_operation_event(
                OperationEvent(
                    operation_id=operation_id,
                    sequence=next_sequence(),
                    state=OperationState.FAILED,
                    stage="failed",
                    error=error,
                )
            )

        task.signals.started.connect(started)
        task.signals.succeeded.connect(succeeded)
        task.signals.failed.connect(failed)
