from __future__ import annotations

from pathlib import Path

import pytest

from phasenox.ui.contracts import (
    AnalysisViewResult,
    OperationEvent,
    OperationHandle,
    OperationState,
    ReferenceViewResult,
    ResultUsability,
    UiErrorCategory,
)
from phasenox.ui.errors import (
    ExceptionBoundary,
    analysis_error,
    knowledge_error,
    missing_model_error,
    provider_unavailable_error,
    reference_error,
    report_error,
    session_persistence_error,
    settings_error,
    unexpected_error,
)
from phasenox.ui.presentation_state import (
    PresentationState,
    ReferenceResultPresentationState,
    ResultPhase,
    ResultPresentationState,
)
from phasenox.ui.presentation_store import PresentationStore


@pytest.mark.parametrize(
    ("error", "usability", "action"),
    [
        (
            missing_model_error(
                operation_id="model-required",
                capability_id="semantic_analysis",
                optional=False,
            ),
            ResultUsability.NOT_USABLE,
            "open_runtime_status",
        ),
        (
            missing_model_error(
                operation_id="model-optional",
                capability_id="reasoning",
                optional=True,
            ),
            ResultUsability.PARTIALLY_USABLE,
            "open_settings",
        ),
        (
            provider_unavailable_error(
                operation_id="provider",
                capability_id="llm_reasoning",
                optional=True,
            ),
            ResultUsability.PARTIALLY_USABLE,
            "refresh_runtime",
        ),
        (
            knowledge_error(ImportError("rag secret"), operation_id="knowledge"),
            ResultUsability.NOT_USABLE,
            "open_runtime_status",
        ),
        (
            report_error(
                PermissionError("token=do-not-show"),
                operation_id="export",
                action="export",
            ),
            ResultUsability.USABLE,
            "choose_export_destination",
        ),
        (
            settings_error(RuntimeError("api_key=do-not-show")),
            ResultUsability.USABLE,
            "retry_settings",
        ),
        (
            session_persistence_error(OSError("credential=do-not-show")),
            ResultUsability.USABLE,
            None,
        ),
    ],
)
def test_known_failures_answer_usability_and_offer_only_real_recovery(
    error, usability, action
) -> None:
    assert error.result_usability is usability
    assert error.usability_message
    assert "do-not-show" not in repr(error)
    assert (action is None) is (not error.recovery_actions)
    if action is not None:
        assert action in {item.id for item in error.recovery_actions}


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("decoder traceback token=secret"),
        FileNotFoundError("missing token=secret"),
        IsADirectoryError("directory token=secret"),
    ],
)
def test_malformed_or_unsupported_audio_is_safe_generic_input_rejection(exc) -> None:
    error = analysis_error(exc, operation_id="analysis")

    assert error.category is UiErrorCategory.VALIDATION
    assert error.result_usability is ResultUsability.NOT_USABLE
    assert error.recovery_actions[0].id == "select_audio"
    assert "secret" not in repr(error)
    assert "traceback" not in error.user_message.casefold()


def test_reference_rejection_and_authoritative_timeout_are_distinct() -> None:
    rejected = reference_error(ValueError("secret"), operation_id="reference")
    timed_out = analysis_error(TimeoutError("secret"), operation_id="analysis")

    assert rejected.category is UiErrorCategory.VALIDATION
    assert rejected.recovery_actions[0].id == "select_references"
    assert timed_out.category is UiErrorCategory.TIMEOUT
    assert timed_out.technical_detail == "TimeoutError"
    assert "secret" not in repr(timed_out)


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (FileNotFoundError("secret"), "report_path_missing"),
        (UnicodeDecodeError("utf-8", b"x", 0, 1, "secret"), "report_encoding_unsupported"),
        (ValueError("secret"), "report_format_unsupported"),
        (PermissionError("secret"), "report_destination_not_writable"),
    ],
)
def test_report_failures_preserve_underlying_results_and_hide_exception_text(exc, code) -> None:
    error = report_error(exc, operation_id="report", action="preview")

    assert error.code == code
    assert error.result_usability is ResultUsability.USABLE
    assert "secret" not in repr(error)


def test_unexpected_exception_is_generic_safe_and_has_no_fake_recovery() -> None:
    error = unexpected_error(RuntimeError("Bearer abc123\ntraceback"), operation_id="operation")

    assert error.category is UiErrorCategory.INTERNAL
    assert error.technical_detail == "RuntimeError"
    assert error.result_usability is ResultUsability.NOT_USABLE
    assert error.recovery_actions == ()
    assert "abc123" not in repr(error)
    assert "traceback" not in repr(error).casefold()


def test_duplicate_active_operation_error_creates_one_notification() -> None:
    store = PresentationStore()
    error = analysis_error(ValueError("invalid"), operation_id="analysis")

    first = store.add_error(error)
    second = store.add_error(error)

    assert second == first
    assert len(store.state.notifications.active) == 1
    assert len(store.state.notifications.history) == 1


def test_operation_and_callback_paths_deduplicate_the_same_error() -> None:
    store = PresentationStore()
    handle = OperationHandle("analysis", "analysis")
    error = analysis_error(ValueError("invalid"), operation_id=handle.operation_id)
    store.begin_operation(handle)

    store.apply_operation_event(
        OperationEvent("analysis", 1, OperationState.FAILED, "failed", error=error)
    )
    store.add_error(error)

    assert len(store.state.notifications.active) == 1


def test_global_exception_boundary_logs_but_emits_only_safe_error(caplog) -> None:
    captured = []
    boundary = ExceptionBoundary(captured.append)
    exception = RuntimeError("Authorization: Bearer secret-token\ntraceback")

    boundary._handle(RuntimeError, exception, None)

    assert len(captured) == 1
    assert "Unhandled desktop exception" in caplog.text
    error = captured[0]
    assert error.user_message == "An unexpected error occurred."
    assert error.technical_detail == "RuntimeError"
    assert "secret-token" not in repr(error)
    assert "traceback" not in repr(error).casefold()


def test_failed_and_cancelled_new_analysis_preserve_prior_result() -> None:
    prior = AnalysisViewResult(Path("prior.wav"), "ok", "mix", 90.0, "retained")
    store = PresentationStore()
    store.begin_operation(OperationHandle("first", "analysis"))
    store.apply_operation_event(OperationEvent("first", 1, OperationState.RUNNING, "running"))
    store.apply_operation_event(
        OperationEvent("first", 2, OperationState.COMPLETED, "complete", result=prior)
    )

    store.begin_operation(OperationHandle("failed", "analysis"))
    error = analysis_error(ValueError("secret"), operation_id="failed")
    store.apply_operation_event(
        OperationEvent("failed", 1, OperationState.FAILED, "failed", error=error)
    )
    assert store.state.result.phase is ResultPhase.FAILURE
    assert store.state.result.result is prior

    store.begin_operation(OperationHandle("cancelled", "analysis"))
    store.apply_operation_event(
        OperationEvent("cancelled", 1, OperationState.CANCELLED, "cancelled")
    )
    assert store.state.result.phase is ResultPhase.CANCELLED
    assert store.state.result.result is prior


def test_rag_and_report_failures_do_not_erase_unrelated_results() -> None:
    analysis = AnalysisViewResult(Path("mix.wav"), "ok", "mix", 90.0, "retained")
    reference = ReferenceViewResult(
        Path("mix.wav"),
        (Path("reference.wav"),),
        "ok",
        90.0,
        0.9,
    )
    store = PresentationStore(
        PresentationState(
            result=ResultPresentationState(ResultPhase.SUCCESS, result=analysis),
            reference_result=ReferenceResultPresentationState(
                ResultPhase.SUCCESS,
                result=reference,
            ),
        )
    )

    store.begin_operation(
        OperationHandle("knowledge", "knowledge_search"),
        tracks_result=False,
        tracks_knowledge_result=True,
    )
    rag_error = knowledge_error(ImportError("secret"), operation_id="knowledge")
    store.apply_operation_event(
        OperationEvent("knowledge", 1, OperationState.FAILED, "failed", error=rag_error)
    )

    store.begin_operation(
        OperationHandle("report", "report_preview"),
        tracks_result=False,
        tracks_report_preview=True,
    )
    preview_error = report_error(
        FileNotFoundError("secret"),
        operation_id="report",
        action="preview",
    )
    store.apply_operation_event(
        OperationEvent("report", 1, OperationState.FAILED, "failed", error=preview_error)
    )

    assert store.state.result.result is analysis
    assert store.state.reference_result.result is reference
    assert store.state.knowledge_result.phase is ResultPhase.FAILURE
    assert store.state.report_preview.phase is ResultPhase.FAILURE

