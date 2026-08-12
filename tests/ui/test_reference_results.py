from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidget, QToolBox, QWidget

from brain.ui.contracts import (
    MetricValue,
    ReferenceBandDifference,
    ReferenceFinding,
    ReferenceMetric,
    ReferenceSegmentDeviation,
    ReferenceSimilarity,
    ReferenceViewResult,
    ReportDescriptor,
    UiError,
    UiErrorCategory,
)
from brain.ui.design_system.components import ErrorState
from brain.ui.presentation_state import ReferenceResultPresentationState, ResultPhase
from brain.ui.reference_result_view import ReferenceResultView


def _result(tmp_path, *, warnings=(), optional=True) -> ReferenceViewResult:
    current = tmp_path / "current.wav"
    reference = tmp_path / "reference.wav"
    report = tmp_path / "reference_report.json"
    return ReferenceViewResult(
        current_path=current,
        reference_paths=(reference,),
        status="degraded" if warnings else "ok",
        similarity=88.75,
        confidence=0.91,
        scores=(MetricValue("frequency_score", 80.125),) if optional else (),
        metric_variances=(MetricValue("loudness", 0.125),) if optional else (),
        metrics=(
            (ReferenceMetric("loudness", -13.25, -14.0, 0.75, "LUFS", 1.0, True, "low", 94.5),)
            if optional
            else ()
        ),
        band_differences=(
            (ReferenceBandDifference("low", 20.0, 200.0, 1.0, 1.2, 0.2, "info"),)
            if optional
            else ()
        ),
        findings=(
            (
                ReferenceFinding(
                    "Low band",
                    "Energy differs.",
                    "frequency",
                    "medium",
                    0.8,
                    "Review low-band balance.",
                    "technical_issue",
                ),
            )
            if optional
            else ()
        ),
        reference_similarities=(ReferenceSimilarity(reference, 88.75),) if optional else (),
        segment_deviations=(
            (ReferenceSegmentDeviation(1.0, 2.0, "loudness", -14.0, -13.0, "low"),)
            if optional
            else ()
        ),
        warnings=warnings,
        reports=(
            (ReportDescriptor("reference_comparison", "json", report, "Reference JSON"),)
            if optional
            else ()
        ),
    )


def test_reference_result_renders_exact_comparison_data(qtbot, tmp_path) -> None:
    view = ReferenceResultView()
    qtbot.addWidget(view)
    result = _result(tmp_path)

    view.render(ReferenceResultPresentationState(ResultPhase.SUCCESS, result=result))

    assert view.findChild(QLabel, "referenceResultSimilarity").text() == "Similarity (raw): 88.75"
    assert "%" not in view.findChild(QLabel, "referenceResultSimilarity").text()
    metrics = view.findChild(QTableWidget, "referenceMetrics")
    assert metrics.item(0, 1).text() == "-13.25"
    assert metrics.item(0, 2).text() == "-14.0"
    assert metrics.item(0, 3).text() == "0.75"
    assert metrics.item(0, 4).text() == "LUFS"
    bands = view.findChild(QTableWidget, "referenceBandDifferences")
    assert bands.item(0, 5).text() == "0.2"
    assert view.findChild(QLabel, "referenceRecommendation").text() == (
        "Recommendation: Review low-band balance."
    )
    segments = view.findChild(QTableWidget, "referenceSegments")
    assert segments.item(0, 0).text() == "1.0"
    assert segments.item(0, 1).text() == "2.0"
    assert view.findChild(QWidget, "referenceReports") is not None


def test_warning_result_remains_usable_and_distinct(qtbot, tmp_path) -> None:
    view = ReferenceResultView()
    qtbot.addWidget(view)
    result = _result(tmp_path, warnings=("Optional reasoner unavailable.",))

    view.render(ReferenceResultPresentationState(ResultPhase.WARNING, result=result))

    assert view.findChild(QTableWidget, "referenceMetrics") is not None
    assert view.findChild(QWidget, "referenceWarnings") is not None
    toolbox = view.findChild(QToolBox, "referenceResultDetails")
    assert "Warnings" in [toolbox.itemText(index) for index in range(toolbox.count())]


def test_absent_optional_result_sections_are_omitted(qtbot, tmp_path) -> None:
    view = ReferenceResultView()
    qtbot.addWidget(view)

    view.render(
        ReferenceResultPresentationState(
            ResultPhase.SUCCESS,
            result=_result(tmp_path, optional=False),
        )
    )

    assert view.findChild(QTableWidget, "referenceMetrics") is None
    assert view.findChild(QTableWidget, "referenceSegments") is None
    assert view.findChild(QWidget, "referenceFindings") is None
    assert view.findChild(QWidget, "referenceReports") is None


def test_failure_cancelled_and_unavailable_states_do_not_show_stale_result(qtbot) -> None:
    view = ReferenceResultView()
    qtbot.addWidget(view)
    error = UiError("reference_failed", UiErrorCategory.VALIDATION, "Choose valid tracks.")

    view.render(ReferenceResultPresentationState(ResultPhase.FAILURE, error=error))
    assert any(label.text() == "Choose valid tracks." for label in view.findChildren(QLabel))
    assert view.findChild(QLabel, "referenceResultSimilarity") is None

    for phase in (ResultPhase.CANCELLED, ResultPhase.UNAVAILABLE):
        view.render(ReferenceResultPresentationState(phase))
        assert phase.value in view.findChild(QLabel, "referenceResultStateMessage").text()
        assert view.findChild(QLabel, "referenceResultSimilarity") is None


def test_failed_refresh_keeps_prior_reference_result_visible(qtbot, tmp_path) -> None:
    prior = _result(tmp_path)
    error = UiError(
        "reference_failed",
        UiErrorCategory.VALIDATION,
        "The latest comparison failed.",
    )
    view = ReferenceResultView()
    qtbot.addWidget(view)

    view.render(
        ReferenceResultPresentationState(
            ResultPhase.FAILURE,
            result=prior,
            error=error,
        )
    )

    assert view.findChild(ErrorState, "referenceResultError") is not None
    assert view.findChild(QLabel, "referenceResultSimilarity") is not None
