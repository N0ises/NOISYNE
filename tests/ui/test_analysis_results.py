from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget, QToolBox, QWidget

from brain.ui.analyze_page import AnalyzePage
from brain.ui.contracts import (
    AnalysisIssue,
    AnalysisViewResult,
    MetricValue,
    RecoveryAction,
    ReportDescriptor,
    UiError,
    UiErrorCategory,
)
from brain.ui.design_system.components import ErrorState
from brain.ui.pages import PageHost
from brain.ui.presentation_state import (
    PageId,
    PresentationState,
    ResultPhase,
    ResultPresentationState,
    SessionState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.result_presentation import build_result_view_state, raw_value_text
from brain.ui.result_view import AnalysisResultView


def _result(
    source: Path,
    *,
    warnings: tuple[str, ...] = (),
    issues: tuple[AnalysisIssue, ...] = (),
    metrics: tuple[MetricValue, ...] = (),
    summary: str = "",
    similarity: float | None = None,
    reports: tuple[ReportDescriptor, ...] = (),
) -> AnalysisViewResult:
    return AnalysisViewResult(
        source_path=source,
        status="degraded" if warnings else "complete",
        audio_type="full_mix",
        score=87.125,
        summary=summary,
        issues=issues,
        metrics=metrics,
        warnings=warnings,
        reference_similarity=similarity,
        reports=reports,
    )


def _label(view: AnalysisResultView, name: str) -> QLabel:
    label = view.findChild(QLabel, name)
    assert label is not None
    return label


def test_success_result_renders_all_real_dto_areas(qtbot, tmp_path) -> None:
    source = tmp_path / "mix.wav"
    report_path = tmp_path / "analysis.json"
    result = _result(
        source,
        metrics=(MetricValue("raw_loudness", -13.987654321), MetricValue("limited", False)),
        issues=(
            AnalysisIssue(
                "Dynamic range",
                "medium",
                "Dynamics are constrained.",
                "Review limiter settings.",
            ),
        ),
        summary="Interpretive summary from the analysis result.",
        similarity=0.8125,
        reports=(ReportDescriptor("analysis", "json", report_path, "Analysis JSON"),),
    )
    view = AnalysisResultView()
    qtbot.addWidget(view)

    view.render(ResultPresentationState(ResultPhase.SUCCESS, result=result))

    assert _label(view, "resultSource").text() == "mix.wav"
    assert _label(view, "resultStatus").text() == "complete"
    assert _label(view, "resultScore").text() == "87.125"
    assert _label(view, "resultAudioType").text() == "full_mix"
    metrics = view.findChild(QTableWidget, "resultMetrics")
    assert metrics is not None
    assert metrics.item(0, 0).text() == "raw_loudness"
    assert metrics.item(0, 1).text() == "-13.987654321"
    assert metrics.item(1, 1).text() == "False"
    assert "dB" not in metrics.item(0, 1).text()
    assert _label(view, "resultIssueSeverity").text() == "Severity: medium"
    assert _label(view, "resultIssueDescription").text() == "Dynamics are constrained."
    assert _label(view, "resultIssueRecommendation").text() == (
        "Recommendation: Review limiter settings."
    )
    assert _label(view, "resultInterpretation").text() == result.summary
    assert _label(view, "resultReferenceSimilarity").text() == "Reference similarity: 0.8125"
    report = _label(view, "resultReportDetails").text()
    assert report == f"Kind: analysis\nFormat: json\nPath: {report_path}"


def test_warning_result_remains_usable_and_warnings_are_distinct(qtbot, tmp_path) -> None:
    result = _result(
        tmp_path / "mix.wav",
        warnings=("Reasoning provider was unavailable.",),
        issues=(AnalysisIssue("Clipping", "high", "Peak clipped.", "Reduce gain."),),
        metrics=(MetricValue("peak", 1.0),),
    )
    view = AnalysisResultView()
    qtbot.addWidget(view)

    view.render(ResultPresentationState(ResultPhase.WARNING, result=result))

    assert view.findChild(QTableWidget, "resultMetrics") is not None
    assert view.findChild(QLabel, "resultIssueDescription") is not None
    warnings = view.findChild(QWidget, "resultWarnings")
    findings = view.findChild(QWidget, "resultIssues")
    assert warnings is not None
    assert findings is not None
    assert warnings is not findings
    warning_container = view.findChild(QToolBox, "resultTechnicalDetails")
    assert warning_container is not None
    assert "Warnings" in [warning_container.itemText(i) for i in range(warning_container.count())]
    assert any(
        label.text() == "Reasoning provider was unavailable."
        for label in warning_container.findChildren(QLabel)
    )


def test_missing_optional_sections_and_no_issues_render_concisely(qtbot, tmp_path) -> None:
    view = AnalysisResultView()
    qtbot.addWidget(view)
    result = _result(tmp_path / "mix.wav")

    view.render(ResultPresentationState(ResultPhase.SUCCESS, result=result))

    assert _label(view, "resultNoIssues").text() == "No engineering findings were returned."
    assert view.findChild(QTableWidget, "resultMetrics") is None
    assert view.findChild(QLabel, "resultInterpretation") is None
    assert view.findChild(QLabel, "resultReferenceSimilarity") is None
    assert view.findChild(QLabel, "resultReportDetails") is None


@pytest.mark.parametrize(
    ("phase", "message"),
    [
        (ResultPhase.EMPTY, "No analysis result is available."),
        (ResultPhase.LOADING, "Result data is not available yet."),
        (ResultPhase.CANCELLED, "cancelled"),
        (ResultPhase.UNAVAILABLE, "unavailable"),
    ],
)
def test_non_result_states_render_without_stale_data(qtbot, phase, message) -> None:
    view = AnalysisResultView()
    qtbot.addWidget(view)

    view.render(ResultPresentationState(phase=phase))

    assert message.casefold() in _label(view, "resultStateMessage").text().casefold()
    assert view.findChild(QLabel, "resultSource") is None


def test_failure_renders_structured_ui_error(qtbot) -> None:
    error = UiError(
        "analysis_failed",
        UiErrorCategory.VALIDATION,
        "Choose a readable audio file.",
    )
    view = AnalysisResultView()
    qtbot.addWidget(view)

    view.render(ResultPresentationState(ResultPhase.FAILURE, error=error))

    error_state = view.findChild(ErrorState, "resultErrorState")
    assert error_state is not None
    assert any(label.text() == error.user_message for label in view.findChildren(QLabel))
    assert view.findChild(QLabel, "resultSource") is None


def test_result_error_recovery_action_emits_stable_intent(qtbot) -> None:
    error = UiError(
        "analysis_failed",
        UiErrorCategory.VALIDATION,
        "Choose a readable audio file.",
        recovery_actions=(RecoveryAction("select_audio", "Select another file"),),
    )
    view = AnalysisResultView()
    qtbot.addWidget(view)
    view.render(ResultPresentationState(ResultPhase.FAILURE, error=error))

    with qtbot.waitSignal(view.recovery_requested, timeout=1000) as recovery:
        view.findChild(ErrorState, "resultErrorState").findChild(QPushButton).click()

    assert recovery.args == ["select_audio"]


def test_failed_refresh_keeps_prior_result_visible_with_error_context(qtbot, tmp_path) -> None:
    prior = _result(tmp_path / "prior.wav")
    error = UiError(
        "analysis_failed",
        UiErrorCategory.VALIDATION,
        "The latest analysis failed.",
    )
    view = AnalysisResultView()
    qtbot.addWidget(view)

    view.render(ResultPresentationState(ResultPhase.FAILURE, result=prior, error=error))

    assert view.findChild(ErrorState, "resultErrorState") is not None
    assert _label(view, "resultSource").text() == prior.source_path.name


def test_result_presentation_preserves_values_without_unit_inference(tmp_path) -> None:
    metric = MetricValue("integrated_loudness", -14.0000001)
    result = _result(tmp_path / "mix.wav", metrics=(metric,), similarity=88.0)

    state = build_result_view_state(ResultPresentationState(ResultPhase.SUCCESS, result=result))

    assert state.metrics == (metric,)
    assert raw_value_text(state.metrics[0].value) == "-14.0000001"
    assert raw_value_text(state.reference_similarity) == "88.0"


def test_analyze_subview_reaches_and_retains_result_across_configuration_and_navigation(
    qtbot, tmp_path
) -> None:
    analyzed = tmp_path / "analyzed.wav"
    next_source = tmp_path / "next.wav"
    analyzed.write_bytes(b"analyzed")
    next_source.write_bytes(b"next")
    result = _result(analyzed, metrics=(MetricValue("tempo", 123.456),))
    result_state = ResultPresentationState(ResultPhase.SUCCESS, result=result)
    state = replace(
        PresentationState(),
        result=result_state,
        session=SessionState(last_analysis_result=result),
    )
    store = PresentationStore(state)
    host = PageHost()
    qtbot.addWidget(host)
    analyze = host.page(PageId.ANALYZE)
    assert isinstance(analyze, AnalyzePage)

    host.render(store.state)
    analyze.view_result_button.click()
    assert analyze.result_view.isVisible() or not analyze.isVisible()
    assert _label(analyze.result_view, "resultSource").text() == analyzed.name

    analyze.select_source(next_source)
    store.navigate(PageId.OVERVIEW)
    store.navigate(PageId.ANALYZE)
    host.render(store.state)

    assert store.state.result.result is result
    assert store.state.session.last_analysis_result is result
    assert _label(analyze.result_view, "resultSource").text() == analyzed.name
