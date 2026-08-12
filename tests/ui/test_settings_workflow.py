from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QLabel, QPushButton

from brain.ui.contracts import (
    AnalysisViewResult,
    Availability,
    IntelligenceSnapshot,
    KnowledgeSearchResult,
    PathStatus,
    ProviderStatus,
    ReferenceViewResult,
    RuntimeState,
    RuntimeStatus,
    SettingsSnapshot,
    SettingValue,
    UiErrorCategory,
)
from brain.ui.pages import PageHost, PlaceholderPage
from brain.ui.presentation_state import (
    KnowledgeResultPresentationState,
    PageId,
    PresentationState,
    ReferenceResultPresentationState,
    ReportExportPresentationState,
    ResultPhase,
    ResultPresentationState,
    RuntimePresentationPhase,
    RuntimePresentationState,
    SettingsPresentationPhase,
    SettingsPresentationState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.settings_controller import SettingsController
from brain.ui.settings_page import SettingsPage
from brain.ui.workers import WorkerExecutor


def _snapshot() -> SettingsSnapshot:
    reason = "V1 has no validated user-settings persistence contract."
    return SettingsSnapshot(
        "packaged-v1",
        "packaged_default",
        (
            SettingValue(
                "llm.provider",
                "configured-provider",
                category="provider",
                display_name="Provider",
                read_only_reason=reason,
            ),
            SettingValue(
                "llm.model",
                "configured-model",
                category="provider",
                display_name="Configured model",
                read_only_reason=reason,
            ),
            SettingValue(
                "runtime.device",
                "cuda",
                category="runtime",
                display_name="Requested device",
                read_only_reason=reason,
            ),
            SettingValue(
                "models.clap.name",
                "clap-model",
                category="models",
                display_name="CLAP model",
                read_only_reason=reason,
            ),
            SettingValue(
                "chroma.path",
                "C:/data/chroma",
                category="knowledge",
                display_name="Knowledge index path",
                read_only_reason=reason,
            ),
            SettingValue(
                "runtime.report_dir",
                "C:/reports",
                category="reports",
                display_name="Report directory",
                read_only_reason=reason,
            ),
            SettingValue(
                "runtime.cache_dir",
                "C:/cache",
                category="storage",
                display_name="Cache directory",
                read_only_reason=reason,
            ),
            SettingValue(
                "logging.level",
                "INFO",
                category="logging",
                display_name="Backend log level",
                read_only_reason=reason,
            ),
        ),
        True,
    )


def _runtime(state=RuntimeState.UNKNOWN, provider=Availability.UNAVAILABLE) -> RuntimeStatus:
    return RuntimeStatus(
        state=state,
        requested_device="cuda",
        effective_device="cpu" if state is RuntimeState.DEGRADED else None,
        device_reason="CUDA was not probed." if state is RuntimeState.UNKNOWN else "CPU fallback.",
        loaded_models=(),
        provider=ProviderStatus(
            "configured-provider",
            provider,
            reason="Endpoint was not reachable.",
        ),
        paths=(PathStatus("cache", Path("C:/cache"), False, False, False),),
        configuration_source="packaged_default",
        capabilities=(),
        checked_at=datetime.now(UTC),
    )


class FakeSettingsAdapter:
    def __init__(
        self, *, snapshot=None, runtime=None, settings_error=None, runtime_error=None, delay=0.0
    ):
        self.snapshot = snapshot or _snapshot()
        self.runtime = runtime or _runtime()
        self.settings_error = settings_error
        self.runtime_error = runtime_error
        self.delay = delay
        self.runtime_thread = None
        self.runtime_calls = 0

    def settings_snapshot(self):
        if self.settings_error:
            raise self.settings_error
        return self.snapshot

    def runtime_status(self):
        self.runtime_calls += 1
        self.runtime_thread = threading.get_ident()
        if self.delay:
            time.sleep(self.delay)
        if self.runtime_error:
            raise self.runtime_error
        return self.runtime


def test_settings_placeholder_is_replaced_and_tab_survives_navigation(qtbot) -> None:
    host = PageHost()
    qtbot.addWidget(host)
    page = host.page(PageId.SETTINGS)

    assert isinstance(page, SettingsPage)
    assert not isinstance(page, PlaceholderPage)
    state = PresentationState(
        settings=SettingsPresentationState(
            phase=SettingsPresentationPhase.READY,
            snapshot=_snapshot(),
        )
    )
    page.render(state)
    page.tabs.setCurrentIndex(3)
    host.show_page(PageId.ANALYZE)
    host.show_page(PageId.SETTINGS)
    page.render(state)
    assert host.page(PageId.SETTINGS) is page
    assert page.tabs.currentIndex() == 3


def test_snapshot_renders_provider_models_paths_and_every_field_read_only(qtbot) -> None:
    page = SettingsPage()
    qtbot.addWidget(page)
    page.render(
        PresentationState(
            settings=SettingsPresentationState(
                phase=SettingsPresentationPhase.READY,
                snapshot=_snapshot(),
            )
        )
    )

    assert page.findChild(QLabel, "setting-llm.provider").text() == "configured-provider"
    assert page.findChild(QLabel, "setting-llm.model").text() == "configured-model"
    assert page.findChild(QLabel, "setting-runtime.device").text() == "cuda"
    assert page.findChild(QLabel, "setting-chroma.path").text() == "C:/data/chroma"
    assert page.findChild(QLabel, "setting-runtime.report_dir").text() == "C:/reports"
    assert page.findChild(QLabel, "setting-logging.level").text() == "INFO"
    modes = page.findChildren(QLabel)
    assert all(
        label.text() == "Read-only"
        for label in modes
        if label.objectName().startswith("setting-mode-")
    )
    button_texts = {button.text() for button in page.findChildren(QPushButton)}
    assert button_texts == {"Refresh runtime status", "Reload configuration"}
    assert "Credential configured: Yes" in page.settings_status.text()
    assert "lm-studio" not in " ".join(label.text() for label in page.findChildren(QLabel))


def test_configured_provider_and_device_are_separate_from_runtime_truth(qtbot) -> None:
    page = SettingsPage()
    qtbot.addWidget(page)
    state = PresentationState(
        settings=SettingsPresentationState(
            phase=SettingsPresentationPhase.READY, snapshot=_snapshot()
        ),
        runtime=RuntimePresentationState.from_status(_runtime()),
    )

    page.render(state)

    assert page.findChild(QLabel, "setting-llm.provider").text() == "configured-provider"
    assert "Availability: unavailable" in page.provider_summary.text()
    assert page.findChild(QLabel, "setting-runtime.device").text() == "cuda"
    assert "Effective device: Unknown" in page.runtime_summary.text()
    assert page.runtime_badge.text() == "Unknown"


def test_degraded_runtime_remains_degraded_and_does_not_claim_gpu(qtbot) -> None:
    page = SettingsPage()
    qtbot.addWidget(page)
    page.render(
        PresentationState(
            settings=SettingsPresentationState(
                phase=SettingsPresentationPhase.READY, snapshot=_snapshot()
            ),
            runtime=RuntimePresentationState.from_status(
                _runtime(RuntimeState.DEGRADED, Availability.DEGRADED)
            ),
        )
    )

    assert page.runtime_badge.text() == "Degraded"
    assert "Effective device: cpu" in page.runtime_summary.text()
    assert "Availability: degraded" in page.provider_summary.text()


def test_settings_reload_is_sync_authoritative_and_failure_preserves_snapshot() -> None:
    original = _snapshot()
    store = PresentationStore(
        PresentationState(
            settings=SettingsPresentationState(
                phase=SettingsPresentationPhase.READY, snapshot=original
            )
        )
    )
    adapter = FakeSettingsAdapter(settings_error=RuntimeError("secret=do-not-show"))
    controller = SettingsController(adapter, store, WorkerExecutor(QThreadPool()))

    controller.refresh_settings()

    assert store.state.settings.phase is SettingsPresentationPhase.FAILURE
    assert store.state.settings.snapshot is original
    error = store.state.settings.error
    assert error.category is UiErrorCategory.CONFIGURATION
    assert error.technical_detail == "RuntimeError"
    assert "do-not-show" not in repr(error)


def test_invalid_settings_dto_is_rejected_as_configuration_failure() -> None:
    adapter = FakeSettingsAdapter()
    adapter.snapshot = object()
    store = PresentationStore()
    controller = SettingsController(adapter, store, WorkerExecutor(QThreadPool()))

    controller.refresh_settings()

    assert store.state.settings.phase is SettingsPresentationPhase.FAILURE
    assert store.state.settings.error.category is UiErrorCategory.CONFIGURATION
    assert store.state.settings.error.technical_detail == "TypeError"


def test_runtime_refresh_runs_off_gui_with_listeners_before_start(qtbot) -> None:
    adapter = FakeSettingsAdapter(runtime=_runtime(RuntimeState.DEGRADED), delay=0.15)
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    controller = SettingsController(adapter, store, executor)
    phase_at_creation = []
    controller.task_created.connect(
        lambda _task: phase_at_creation.append(store.state.runtime.phase)
    )
    timer_fired = []
    QTimer.singleShot(20, lambda: timer_fired.append(True))
    gui_thread = threading.get_ident()

    controller.refresh_runtime()
    assert phase_at_creation == [RuntimePresentationPhase.LOADING]
    qtbot.waitUntil(lambda: bool(timer_fired), timeout=1000)
    qtbot.waitUntil(
        lambda: store.state.runtime.phase is RuntimePresentationPhase.DEGRADED,
        timeout=3000,
    )
    executor.wait_for_done()
    assert adapter.runtime_thread != gui_thread
    assert adapter.runtime_calls == 1


def test_runtime_failure_is_structured_and_preserves_all_result_states(qtbot, tmp_path) -> None:
    analysis = AnalysisViewResult(
        Path("mix.wav"),
        "ok",
        "mix",
        90.0,
        "summary",
        intelligence=IntelligenceSnapshot(reasoning="retained"),
    )
    reference = ReferenceViewResult(Path("mix.wav"), (Path("reference.wav"),), "ok", 90.0, 0.9)
    knowledge = KnowledgeSearchResult("query")
    state = PresentationState(
        result=ResultPresentationState(phase=ResultPhase.SUCCESS, result=analysis),
        reference_result=ReferenceResultPresentationState(
            phase=ResultPhase.SUCCESS, result=reference
        ),
        knowledge_result=KnowledgeResultPresentationState(
            phase=ResultPhase.SUCCESS, result=knowledge
        ),
        report_export=ReportExportPresentationState(
            phase=ResultPhase.SUCCESS,
        ),
        settings=SettingsPresentationState(
            phase=SettingsPresentationPhase.READY, snapshot=_snapshot()
        ),
    )
    store = PresentationStore(state)
    executor = WorkerExecutor(QThreadPool())
    controller = SettingsController(
        FakeSettingsAdapter(runtime_error=RuntimeError("provider secret")),
        store,
        executor,
    )

    controller.refresh_runtime()
    qtbot.waitUntil(
        lambda: bool(store.state.notifications.active),
        timeout=3000,
    )
    executor.wait_for_done()

    assert store.state.runtime.phase is RuntimePresentationPhase.UNKNOWN
    assert store.state.notifications.active[-1].error.category is UiErrorCategory.CONFIGURATION
    assert "provider secret" not in repr(store.state.notifications.active[-1].error)
    assert store.state.result.result is analysis
    assert store.state.reference_result.result is reference
    assert store.state.knowledge_result.result is knowledge
    assert store.state.settings.snapshot == _snapshot()
