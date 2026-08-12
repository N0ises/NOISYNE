"""Qt-free presentation and session state for the desktop application."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from .contracts import (
    AnalysisViewResult,
    CapabilitySnapshot,
    KnowledgeSearchResult,
    OperationEvent,
    OperationHandle,
    OperationState,
    RecoveryAction,
    ReferenceViewResult,
    ReportDescriptor,
    ReportExportResult,
    ReportPreview,
    RuntimeState,
    RuntimeStatus,
    SettingsSnapshot,
    UiError,
)


class PageId(str, Enum):
    OVERVIEW = "overview"
    ANALYZE = "analyze"
    REFERENCES = "references"
    INTELLIGENCE = "intelligence"
    KNOWLEDGE = "knowledge"
    REPORTS = "reports"
    SETTINGS = "settings"
    RUNTIME_STATUS = "runtime_status"


NAVIGATION_ORDER = tuple(PageId)


@dataclass(frozen=True, slots=True)
class NavigationState:
    current_page: PageId = PageId.OVERVIEW
    available_pages: tuple[PageId, ...] = NAVIGATION_ORDER

    def navigate(self, page: PageId) -> NavigationState:
        if page not in self.available_pages:
            raise ValueError(f"Page is not available: {page.value}")
        return replace(self, current_page=page)


TERMINAL_OPERATION_STATES = frozenset(
    {OperationState.COMPLETED, OperationState.FAILED, OperationState.CANCELLED}
)

_ALLOWED_OPERATION_TRANSITIONS = {
    OperationState.QUEUED: frozenset(
        {
            OperationState.VALIDATING,
            OperationState.RUNNING,
            OperationState.CANCELLING,
            OperationState.CANCELLED,
            OperationState.FAILED,
        }
    ),
    OperationState.VALIDATING: frozenset(
        {
            OperationState.QUEUED,
            OperationState.RUNNING,
            OperationState.CANCELLING,
            OperationState.CANCELLED,
            OperationState.FAILED,
        }
    ),
    OperationState.RUNNING: frozenset(
        {
            OperationState.CANCELLING,
            OperationState.COMPLETED,
            OperationState.FAILED,
            OperationState.CANCELLED,
        }
    ),
    OperationState.CANCELLING: frozenset(
        {
            OperationState.COMPLETED,
            OperationState.FAILED,
            OperationState.CANCELLED,
        }
    ),
    OperationState.COMPLETED: frozenset(),
    OperationState.FAILED: frozenset(),
    OperationState.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class OperationPresentationState:
    operation_id: str | None = None
    kind: str | None = None
    state: OperationState | None = None
    last_sequence: int = -1
    stage: str = "idle"
    progress: float | None = None
    message: str | None = None
    cancellable: bool = False
    cancel_requested: bool = False
    error: UiError | None = None

    @property
    def is_idle(self) -> bool:
        return self.operation_id is None

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_OPERATION_STATES

    @classmethod
    def begin(
        cls, handle: OperationHandle, *, cancellable: bool = False
    ) -> OperationPresentationState:
        return cls(
            operation_id=handle.operation_id,
            kind=handle.kind,
            state=handle.state,
            last_sequence=0,
            stage=handle.state.value,
            cancellable=cancellable,
            cancel_requested=handle.cancel_requested,
        )

    def request_cancel(self) -> OperationPresentationState:
        if self.is_idle or self.is_terminal or not self.cancellable:
            return self
        return replace(
            self,
            state=OperationState.CANCELLING,
            stage=OperationState.CANCELLING.value,
            cancellable=False,
            cancel_requested=True,
        )

    def apply(self, event: OperationEvent) -> tuple[OperationPresentationState, bool]:
        if event.operation_id != self.operation_id:
            return self, False
        if self.is_terminal or event.sequence <= self.last_sequence:
            return self, False
        if self.state is None or event.state not in _ALLOWED_OPERATION_TRANSITIONS[self.state]:
            return self, False
        if event.progress is not None and not 0.0 <= event.progress <= 1.0:
            return self, False
        updated = replace(
            self,
            state=event.state,
            last_sequence=event.sequence,
            stage=event.stage,
            progress=event.progress,
            message=event.message,
            cancellable=event.cancellable and event.state not in TERMINAL_OPERATION_STATES,
            cancel_requested=self.cancel_requested or event.state is OperationState.CANCELLING,
            error=event.error,
        )
        return updated, True


class NotificationLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Notification:
    notification_id: str
    sequence: int
    level: NotificationLevel
    message: str
    created_at: datetime
    operation_id: str | None = None
    error: UiError | None = None
    recovery_actions: tuple[RecoveryAction, ...] = ()


@dataclass(frozen=True, slots=True)
class NotificationState:
    active: tuple[Notification, ...] = ()
    history: tuple[Notification, ...] = ()
    next_sequence: int = 1
    history_limit: int = 50

    def add(
        self,
        *,
        level: NotificationLevel,
        message: str,
        operation_id: str | None = None,
        error: UiError | None = None,
        recovery_actions: tuple[RecoveryAction, ...] = (),
        created_at: datetime | None = None,
    ) -> NotificationState:
        if error is not None:
            duplicate = next(
                (
                    item
                    for item in self.active
                    if item.error is not None
                    and item.error.code == error.code
                    and item.operation_id == operation_id
                ),
                None,
            )
            if duplicate is not None:
                return self
        sequence = self.next_sequence
        notification = Notification(
            notification_id=f"notification-{sequence}",
            sequence=sequence,
            level=level,
            message=message,
            created_at=created_at or datetime.now(UTC),
            operation_id=operation_id,
            error=error,
            recovery_actions=recovery_actions,
        )
        return replace(
            self,
            active=(*self.active, notification),
            history=(*self.history, notification)[-self.history_limit :],
            next_sequence=sequence + 1,
        )

    def dismiss(self, notification_id: str) -> NotificationState:
        return replace(
            self,
            active=tuple(item for item in self.active if item.notification_id != notification_id),
        )

    def active_error_id(self, error: UiError) -> str | None:
        match = next(
            (
                item
                for item in self.active
                if item.error is not None
                and item.error.code == error.code
                and item.operation_id == error.operation_id
            ),
            None,
        )
        return match.notification_id if match is not None else None


class RuntimePresentationPhase(str, Enum):
    LOADING = "loading"
    UNKNOWN = "unknown"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class RuntimePresentationState:
    phase: RuntimePresentationPhase = RuntimePresentationPhase.UNKNOWN
    status: RuntimeStatus | None = None
    capabilities: tuple[CapabilitySnapshot, ...] = ()

    @classmethod
    def loading(cls) -> RuntimePresentationState:
        return cls(phase=RuntimePresentationPhase.LOADING)

    @classmethod
    def from_status(cls, status: RuntimeStatus) -> RuntimePresentationState:
        phase = {
            RuntimeState.READY: RuntimePresentationPhase.READY,
            RuntimeState.DEGRADED: RuntimePresentationPhase.DEGRADED,
            RuntimeState.UNAVAILABLE: RuntimePresentationPhase.UNAVAILABLE,
            RuntimeState.UNKNOWN: RuntimePresentationPhase.UNKNOWN,
        }[status.state]
        return cls(phase=phase, status=status, capabilities=status.capabilities)

    def capability(self, capability_id: str) -> CapabilitySnapshot | None:
        return next((item for item in self.capabilities if item.id == capability_id), None)


class SettingsPresentationPhase(str, Enum):
    LOADING = "loading"
    READY = "ready"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class SettingsPresentationState:
    phase: SettingsPresentationPhase = SettingsPresentationPhase.LOADING
    snapshot: SettingsSnapshot | None = None
    error: UiError | None = None


class ResultPhase(str, Enum):
    EMPTY = "empty"
    LOADING = "loading"
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ResultPresentationState:
    phase: ResultPhase = ResultPhase.EMPTY
    operation_id: str | None = None
    result: AnalysisViewResult | None = None
    error: UiError | None = None

    @classmethod
    def loading(
        cls,
        operation_id: str,
        retained_result: AnalysisViewResult | None = None,
    ) -> ResultPresentationState:
        return cls(
            phase=ResultPhase.LOADING,
            operation_id=operation_id,
            result=retained_result,
        )


@dataclass(frozen=True, slots=True)
class ReferenceResultPresentationState:
    phase: ResultPhase = ResultPhase.EMPTY
    operation_id: str | None = None
    result: ReferenceViewResult | None = None
    error: UiError | None = None

    @classmethod
    def loading(
        cls,
        operation_id: str,
        retained_result: ReferenceViewResult | None = None,
    ) -> ReferenceResultPresentationState:
        return cls(
            phase=ResultPhase.LOADING,
            operation_id=operation_id,
            result=retained_result,
        )


@dataclass(frozen=True, slots=True)
class KnowledgeResultPresentationState:
    phase: ResultPhase = ResultPhase.EMPTY
    operation_id: str | None = None
    result: KnowledgeSearchResult | None = None
    error: UiError | None = None

    @classmethod
    def loading(
        cls,
        operation_id: str,
        retained_result: KnowledgeSearchResult | None = None,
    ) -> KnowledgeResultPresentationState:
        return cls(
            phase=ResultPhase.LOADING,
            operation_id=operation_id,
            result=retained_result,
        )


@dataclass(frozen=True, slots=True)
class ReportPreviewPresentationState:
    phase: ResultPhase = ResultPhase.EMPTY
    operation_id: str | None = None
    preview: ReportPreview | None = None
    error: UiError | None = None

    @classmethod
    def loading(cls, operation_id: str) -> ReportPreviewPresentationState:
        return cls(phase=ResultPhase.LOADING, operation_id=operation_id)


@dataclass(frozen=True, slots=True)
class ReportExportPresentationState:
    phase: ResultPhase = ResultPhase.EMPTY
    operation_id: str | None = None
    result: ReportExportResult | None = None
    error: UiError | None = None

    @classmethod
    def loading(cls, operation_id: str) -> ReportExportPresentationState:
        return cls(phase=ResultPhase.LOADING, operation_id=operation_id)


@dataclass(frozen=True, slots=True)
class RecentPath:
    path: Path
    last_used_at: datetime
    exists: bool


@dataclass(frozen=True, slots=True)
class RecentAnalysis:
    source_path: Path
    analyzed_at: datetime
    status: str
    audio_type: str
    score: float
    source_exists: bool


@dataclass(frozen=True, slots=True)
class RecentReport:
    descriptor: ReportDescriptor
    created_at: datetime
    exists: bool


def _path_key(path: Path) -> str:
    return str(path.expanduser().resolve(strict=False)).casefold()


def _prepend_unique(items: tuple, item, key, limit: int) -> tuple:
    item_key = key(item)
    remaining = tuple(existing for existing in items if key(existing) != item_key)
    return (item, *remaining)[:limit]


@dataclass(frozen=True, slots=True)
class SessionState:
    navigation: NavigationState = NavigationState()
    selected_audio: Path | None = None
    selected_references: tuple[Path, ...] = ()
    last_analysis_result: AnalysisViewResult | None = None
    last_reference_result: ReferenceViewResult | None = None
    last_knowledge_query: str = ""
    recent_knowledge_queries: tuple[str, ...] = ()
    current_operation: OperationHandle | None = None
    recent_analyses: tuple[RecentAnalysis, ...] = ()
    recent_reports: tuple[RecentReport, ...] = ()
    recent_references: tuple[RecentPath, ...] = ()
    recent_files: tuple[RecentPath, ...] = ()
    selected_report_path: Path | None = None
    recent_limit: int = 20

    def navigate(self, page: PageId) -> SessionState:
        return replace(self, navigation=self.navigation.navigate(page))

    def select_audio(self, path: Path | None, *, used_at: datetime | None = None) -> SessionState:
        if path is None:
            return replace(self, selected_audio=None)
        timestamp = used_at or datetime.now(UTC)
        recent = RecentPath(path=path, last_used_at=timestamp, exists=path.exists())
        return replace(
            self,
            selected_audio=path,
            recent_files=_prepend_unique(
                self.recent_files, recent, lambda item: _path_key(item.path), self.recent_limit
            ),
        )

    def select_references(
        self, paths: tuple[Path, ...], *, used_at: datetime | None = None
    ) -> SessionState:
        timestamp = used_at or datetime.now(UTC)
        unique_paths: list[Path] = []
        seen: set[str] = set()
        recent = self.recent_references
        files = self.recent_files
        for path in paths:
            key = _path_key(path)
            if key in seen:
                continue
            seen.add(key)
            unique_paths.append(path)
            item = RecentPath(path=path, last_used_at=timestamp, exists=path.exists())
            recent = _prepend_unique(
                recent, item, lambda entry: _path_key(entry.path), self.recent_limit
            )
            files = _prepend_unique(
                files, item, lambda entry: _path_key(entry.path), self.recent_limit
            )
        return replace(
            self,
            selected_references=tuple(unique_paths),
            recent_references=recent,
            recent_files=files,
        )

    def with_operation(self, handle: OperationHandle | None) -> SessionState:
        return replace(self, current_operation=handle)

    def select_report(self, path: Path | None) -> SessionState:
        return replace(self, selected_report_path=path)

    def record_analysis(
        self, result: AnalysisViewResult, *, analyzed_at: datetime | None = None
    ) -> SessionState:
        timestamp = analyzed_at or datetime.now(UTC)
        analysis = RecentAnalysis(
            source_path=result.source_path,
            analyzed_at=timestamp,
            status=result.status,
            audio_type=result.audio_type,
            score=result.score,
            source_exists=result.source_path.exists(),
        )
        recent_analyses = _prepend_unique(
            self.recent_analyses,
            analysis,
            lambda item: _path_key(item.source_path),
            self.recent_limit,
        )
        recent_reports = self.recent_reports
        for descriptor in result.reports:
            report = RecentReport(
                descriptor=descriptor,
                created_at=timestamp,
                exists=descriptor.path.exists(),
            )
            recent_reports = _prepend_unique(
                recent_reports,
                report,
                lambda item: _path_key(item.descriptor.path),
                self.recent_limit,
            )
        selected = self.select_audio(result.source_path, used_at=timestamp)
        return replace(
            selected,
            last_analysis_result=result,
            recent_analyses=recent_analyses,
            recent_reports=recent_reports,
        )

    def record_reference_result(
        self,
        result: ReferenceViewResult,
        *,
        compared_at: datetime | None = None,
    ) -> SessionState:
        timestamp = compared_at or datetime.now(UTC)
        selected = self.select_audio(result.current_path, used_at=timestamp)
        selected = selected.select_references(result.reference_paths, used_at=timestamp)
        recent_reports = selected.recent_reports
        for descriptor in result.reports:
            report = RecentReport(
                descriptor=descriptor,
                created_at=timestamp,
                exists=descriptor.path.exists(),
            )
            recent_reports = _prepend_unique(
                recent_reports,
                report,
                lambda item: _path_key(item.descriptor.path),
                self.recent_limit,
            )
        return replace(
            selected,
            last_reference_result=result,
            recent_reports=recent_reports,
        )

    def record_knowledge_result(self, result: KnowledgeSearchResult) -> SessionState:
        query = result.query.strip()
        recent = (query, *(item for item in self.recent_knowledge_queries if item != query))
        return replace(
            self,
            last_knowledge_query=query,
            recent_knowledge_queries=recent[: self.recent_limit],
        )

    def record_report(
        self,
        descriptor: ReportDescriptor,
        *,
        created_at: datetime | None = None,
    ) -> SessionState:
        report = RecentReport(
            descriptor=descriptor,
            created_at=created_at or datetime.now(UTC),
            exists=descriptor.path.exists(),
        )
        return replace(
            self,
            recent_reports=_prepend_unique(
                self.recent_reports,
                report,
                lambda item: _path_key(item.descriptor.path),
                self.recent_limit,
            ),
        )


@dataclass(frozen=True, slots=True)
class PresentationState:
    navigation: NavigationState = NavigationState()
    operation: OperationPresentationState = OperationPresentationState()
    notifications: NotificationState = NotificationState()
    runtime: RuntimePresentationState = RuntimePresentationState()
    settings: SettingsPresentationState = SettingsPresentationState()
    result: ResultPresentationState = ResultPresentationState()
    reference_result: ReferenceResultPresentationState = ReferenceResultPresentationState()
    knowledge_result: KnowledgeResultPresentationState = KnowledgeResultPresentationState()
    report_preview: ReportPreviewPresentationState = ReportPreviewPresentationState()
    report_export: ReportExportPresentationState = ReportExportPresentationState()
    session: SessionState = SessionState()

    @classmethod
    def from_session(cls, session: SessionState) -> PresentationState:
        return cls(navigation=session.navigation, session=session)
