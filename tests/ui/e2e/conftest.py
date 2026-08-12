from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from PySide6.QtCore import QThreadPool

from brain.ui.app import build_main_window, create_application
from brain.ui.branding import default_product_metadata
from brain.ui.contracts import (
    AnalysisCommand,
    AnalysisViewResult,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    KnowledgeQuery,
    KnowledgeResultItem,
    KnowledgeSearchResult,
    MetricValue,
    ProviderStatus,
    ReferenceComparisonCommand,
    ReferenceViewResult,
    ReportDescriptor,
    ReportExportCommand,
    ReportExportResult,
    ReportPreview,
    RuntimeState,
    RuntimeStatus,
    SettingsSnapshot,
    SettingValue,
)
from brain.ui.presentation_state import PresentationState, RuntimePresentationState
from brain.ui.presentation_store import PresentationStore
from brain.ui.state import ApplicationStateStore
from brain.ui.workers import WorkerExecutor


def capability(
    capability_id: str,
    availability: Availability = Availability.AVAILABLE,
    *,
    reason: str = "Available through deterministic desktop test adapter.",
) -> CapabilitySnapshot:
    return CapabilitySnapshot(
        capability_id,
        capability_id.replace("_", " ").title(),
        CapabilityLifecycle.IMPLEMENTED,
        availability,
        reason=reason,
        checked_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def runtime_status(
    state: RuntimeState = RuntimeState.READY,
    *,
    capabilities: tuple[CapabilitySnapshot, ...] | None = None,
) -> RuntimeStatus:
    selected = capabilities or (
        capability("audio_analysis"),
        capability("reference_comparison"),
        capability("rag_retrieval"),
        capability("ai_reasoning", Availability.UNAVAILABLE, reason="No model configured."),
    )
    return RuntimeStatus(
        state,
        "cpu",
        "cpu" if state is not RuntimeState.UNAVAILABLE else None,
        "Deterministic test runtime status.",
        (),
        ProviderStatus(
            "test-provider",
            Availability.AVAILABLE if state is RuntimeState.READY else Availability.UNAVAILABLE,
            "No network provider is called.",
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
        (),
        "desktop-e2e-fixture",
        selected,
        datetime(2026, 1, 1, tzinfo=UTC),
    )


@dataclass
class DeterministicDesktopAdapter:
    """Complete fake mirroring DesktopApplicationAdapter without backend dependencies."""

    runtime: RuntimeStatus = field(default_factory=runtime_status)
    analysis_result: AnalysisViewResult | None = None
    analysis_error: Exception | None = None
    reference_result: ReferenceViewResult | None = None
    reference_error: Exception | None = None
    knowledge_result: KnowledgeSearchResult | None = None
    knowledge_error: Exception | None = None
    preview_result: ReportPreview | None = None
    preview_error: Exception | None = None
    export_result: ReportExportResult | None = None
    export_error: Exception | None = None
    settings_error: Exception | None = None
    calls: list[tuple[str, object]] = field(default_factory=list)

    def product_metadata(self):
        return default_product_metadata()

    def capability_snapshots(self):
        return self.runtime.capabilities

    def runtime_status(self):
        self.calls.append(("runtime_status", None))
        return self.runtime

    def settings_snapshot(self):
        self.calls.append(("settings_snapshot", None))
        if self.settings_error:
            raise self.settings_error
        return SettingsSnapshot(
            "e2e-revision",
            "deterministic fixture",
            (
                SettingValue(
                    "device",
                    "cpu",
                    category="runtime",
                    display_name="Requested device",
                    read_only_reason="V1 settings are read-only.",
                ),
            ),
            False,
        )

    def analyze(self, command: AnalysisCommand):
        self.calls.append(("analyze", command))
        if self.analysis_error:
            raise self.analysis_error
        return self.analysis_result or AnalysisViewResult(
            command.source_path,
            "ok",
            "mix",
            92.5,
            "Deterministic analysis result.",
            metrics=(MetricValue("integrated_loudness", -14.0),),
        )

    def compare_references(self, command: ReferenceComparisonCommand):
        self.calls.append(("compare_references", command))
        if self.reference_error:
            raise self.reference_error
        return self.reference_result or ReferenceViewResult(
            command.current_path,
            command.reference_paths,
            "ok",
            88.75,
            0.9,
        )

    def search_knowledge(self, query: KnowledgeQuery):
        self.calls.append(("search_knowledge", query))
        if self.knowledge_error:
            raise self.knowledge_error
        return self.knowledge_result or KnowledgeSearchResult(
            query.text,
            (
                KnowledgeResultItem(
                    "Keep headroom before limiting.",
                    "fixture-guide.md",
                    2,
                    0.8,
                    0.75,
                ),
            ),
        )

    def load_report(self, descriptor: ReportDescriptor):
        self.calls.append(("load_report", descriptor))
        if self.preview_error:
            raise self.preview_error
        return self.preview_result or ReportPreview(
            descriptor,
            '{"score": 92.5}',
            15,
            datetime(2026, 1, 1, tzinfo=UTC),
        )

    def export_report(self, command: ReportExportCommand):
        self.calls.append(("export_report", command))
        if self.export_error:
            raise self.export_error
        return self.export_result or ReportExportResult(
            command.source,
            ReportDescriptor(
                command.source.kind,
                command.source.format,
                command.destination_path,
                command.destination_path.name,
                command.source.source_path,
            ),
        )


@dataclass
class DesktopHarness:
    window: object
    store: PresentationStore
    adapter: DeterministicDesktopAdapter
    executor: WorkerExecutor

    def wait_for_operation(self, qtbot) -> None:
        qtbot.waitUntil(lambda: self.store.state.operation.is_terminal, timeout=3000)
        assert self.executor.wait_for_done(3000)


@pytest.fixture
def desktop_harness(qtbot):
    create_application(default_product_metadata())
    adapter = DeterministicDesktopAdapter()
    store = PresentationStore(
        PresentationState(runtime=RuntimePresentationState.from_status(adapter.runtime))
    )
    executor = WorkerExecutor(QThreadPool())
    window = build_main_window(
        adapter,
        ApplicationStateStore(),
        store,
        executor,
    )
    qtbot.addWidget(window)
    window.show()
    return DesktopHarness(window, store, adapter, executor)
