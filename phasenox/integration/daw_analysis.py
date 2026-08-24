"""Asynchronous application-service gateway for accepted DAW audio exports."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from pathlib import Path

from .daw_bridge import (
    DawAnalysisResult,
    DawAnalysisState,
    DawBridgeError,
    DawImportRequest,
)

Analyzer = Callable[[DawImportRequest], DawAnalysisResult]


class DawAnalysisGateway:
    """Run canonical deterministic analysis away from HTTP request threads."""

    def __init__(
        self,
        analyzer: Analyzer | None = None,
        *,
        max_pending: int = 16,
        max_results: int = 128,
    ) -> None:
        if max_pending <= 0 or max_results <= 0:
            raise ValueError("Analysis queue and result limits must be positive.")
        self._analyzer = analyzer or self._analyze_with_application_service
        self._pending: queue.Queue[DawImportRequest | None] = queue.Queue(maxsize=max_pending)
        self._max_results = max_results
        self._results: dict[str, DawAnalysisResult] = {}
        self._result_order: list[str] = []
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._accepting = False

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._accepting = True
            thread = threading.Thread(
                target=self._run,
                name="phasenox-daw-analysis",
                daemon=True,
            )
            self._thread = thread
            thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        if timeout <= 0:
            raise ValueError("Analysis shutdown timeout must be positive.")
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            self._accepting = False
        self._pending.put(None, timeout=timeout)
        thread.join(timeout=timeout)
        if thread.is_alive():
            raise DawBridgeError(
                "shutdown_timeout",
                "DAW analysis did not stop within the bounded shutdown interval.",
            )
        with self._lock:
            self._thread = None

    def submit(self, request: DawImportRequest) -> DawAnalysisResult:
        request_id = request.audio_export.export_id
        with self._lock:
            if not self._accepting:
                raise DawBridgeError("analysis_unavailable", "DAW analysis is not available.")
            existing = self._results.get(request_id)
            if existing is not None:
                return existing
            result = DawAnalysisResult(
                request_id=request_id,
                state=DawAnalysisState.QUEUED,
                analysis_id=None,
                source=request.audio_export.path.name,
            )
            self._store_result(result)
        try:
            self._pending.put_nowait(request)
        except queue.Full as exc:
            with self._lock:
                self._results.pop(request_id, None)
                if request_id in self._result_order:
                    self._result_order.remove(request_id)
            raise DawBridgeError(
                "analysis_queue_full",
                "PHASENOX analysis capacity is currently full.",
            ) from exc
        return result

    def result(self, request_id: str) -> DawAnalysisResult | None:
        with self._lock:
            return self._results.get(request_id)

    def _run(self) -> None:
        while True:
            request = self._pending.get()
            try:
                if request is None:
                    return
                request_id = request.audio_export.export_id
                with self._lock:
                    self._store_result(
                        DawAnalysisResult(
                            request_id=request_id,
                            state=DawAnalysisState.ANALYZING,
                            analysis_id=None,
                            source=request.audio_export.path.name,
                        )
                    )
                try:
                    result = self._analyzer(request)
                    if result.request_id != request_id:
                        raise ValueError("Analyzer returned a mismatched request identity.")
                except Exception:  # noqa: BLE001 - worker must map analyzer failures safely
                    result = DawAnalysisResult(
                        request_id=request_id,
                        state=DawAnalysisState.FAILED,
                        analysis_id=None,
                        source=request.audio_export.path.name,
                        error_code="analysis_failure",
                        error_message="PHASENOX could not analyze the submitted audio.",
                    )
                with self._lock:
                    self._store_result(result)
            finally:
                self._pending.task_done()

    def _store_result(self, result: DawAnalysisResult) -> None:
        request_id = result.request_id
        if request_id not in self._results:
            self._result_order.append(request_id)
        self._results[request_id] = result
        while len(self._result_order) > self._max_results:
            expired = self._result_order.pop(0)
            self._results.pop(expired, None)

    @staticmethod
    def _analyze_with_application_service(request: DawImportRequest) -> DawAnalysisResult:
        from phasenox.application import (
            ApplicationRequest,
            ApplicationResultStatus,
            OperationType,
            PhasenoxV2Service,
        )

        request_id = request.audio_export.export_id
        application_result = PhasenoxV2Service().execute(
            ApplicationRequest(
                request_id=request_id,
                operation=OperationType.ANALYZE,
                parameters={"audio_path": str(request.audio_export.path)},
            )
        )
        if application_result.status is ApplicationResultStatus.FAILED:
            error_code = (
                application_result.errors[0].code
                if application_result.errors
                else "analysis_failure"
            )
            return DawAnalysisResult(
                request_id=request_id,
                state=DawAnalysisState.FAILED,
                analysis_id=None,
                source=request.audio_export.path.name,
                error_code=error_code,
                error_message="PHASENOX could not analyze the submitted audio.",
            )

        payload = application_result.payload or {}
        metadata = payload.get("audio_metadata")
        safe_metadata: dict[str, object] = {}
        if isinstance(metadata, dict):
            for key in ("format", "sample_rate", "channels", "duration", "bit_depth"):
                value = metadata.get(key)
                if isinstance(value, (str, int, float, bool)) or value is None:
                    safe_metadata[key] = value
        descriptors = payload.get("descriptors")
        descriptor_count = len(descriptors) if isinstance(descriptors, list) else 0
        summary: dict[str, object] = {
            "audio": safe_metadata,
            "descriptor_count": descriptor_count,
        }
        return DawAnalysisResult(
            request_id=request_id,
            state=DawAnalysisState.COMPLETED,
            analysis_id=f"analysis-{request_id[:16]}",
            source=Path(request.audio_export.path).name,
            summary=summary,
            limitations=tuple(application_result.limitations[:8]),
        )


__all__ = ["DawAnalysisGateway"]
