"""Qt-free result presentation derived only from stable desktop DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contracts import AnalysisIssue, MetricValue, ReportDescriptor, UiError
from .presentation_state import ResultPhase, ResultPresentationState


@dataclass(frozen=True, slots=True)
class ResultHeaderView:
    source_path: Path
    status: str
    score: float
    audio_type: str


@dataclass(frozen=True, slots=True)
class AnalysisResultViewState:
    phase: ResultPhase
    message: str
    header: ResultHeaderView | None = None
    metrics: tuple[MetricValue, ...] = ()
    issues: tuple[AnalysisIssue, ...] = ()
    warnings: tuple[str, ...] = ()
    summary: str = ""
    reference_similarity: float | None = None
    reports: tuple[ReportDescriptor, ...] = ()
    error: UiError | None = None


def build_result_view_state(state: ResultPresentationState) -> AnalysisResultViewState:
    """Map result state one-to-one without inferring values, units, or sections."""
    result = state.result
    if (
        state.phase
        in {
            ResultPhase.SUCCESS,
            ResultPhase.WARNING,
            ResultPhase.FAILURE,
            ResultPhase.CANCELLED,
        }
        and result is not None
    ):
        return AnalysisResultViewState(
            phase=state.phase,
            message=(
                "Analysis completed with warnings. Available result data remains usable."
                if state.phase is ResultPhase.WARNING
                else (
                    "The latest analysis failed. The previous result remains available."
                    if state.phase is ResultPhase.FAILURE
                    else (
                        "The latest analysis was cancelled. The previous result remains available."
                        if state.phase is ResultPhase.CANCELLED
                        else "Analysis completed."
                    )
                )
            ),
            header=ResultHeaderView(
                source_path=result.source_path,
                status=result.status,
                score=result.score,
                audio_type=result.audio_type,
            ),
            metrics=result.metrics,
            issues=result.issues,
            warnings=result.warnings,
            summary=result.summary,
            reference_similarity=result.reference_similarity,
            reports=result.reports,
            error=state.error,
        )

    messages = {
        ResultPhase.EMPTY: "No analysis result is available.",
        ResultPhase.LOADING: "Analysis is running. Result data is not available yet.",
        ResultPhase.SUCCESS: "The completed operation did not return an analysis result.",
        ResultPhase.WARNING: "The partial operation did not return an analysis result.",
        ResultPhase.FAILURE: (
            state.error.user_message if state.error else "Analysis failed without error details."
        ),
        ResultPhase.CANCELLED: "Analysis was cancelled before a result became available.",
        ResultPhase.UNAVAILABLE: "Analysis results are unavailable.",
    }
    return AnalysisResultViewState(
        phase=state.phase,
        message=messages[state.phase],
        error=state.error,
    )


def raw_value_text(value: str | float | bool | None) -> str:
    """Render the DTO value directly; unit inference and normalization are forbidden."""
    return str(value)

