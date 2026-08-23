"""Desktop exception translation and process-level exception boundary."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from types import TracebackType

from .contracts import RecoveryAction, ResultUsability, UiError, UiErrorCategory

logger = logging.getLogger(__name__)


def unexpected_error(exc: BaseException, *, operation_id: str | None = None) -> UiError:
    return UiError(
        code="unexpected_internal_error",
        category=UiErrorCategory.INTERNAL,
        user_message="An unexpected error occurred.",
        technical_detail=type(exc).__name__,
        retryable=False,
        result_usability=(
            ResultUsability.NOT_USABLE
            if operation_id is not None
            else ResultUsability.NOT_APPLICABLE
        ),
        operation_id=operation_id,
    )


def timeout_error(
    exc: BaseException,
    *,
    operation_id: str,
    capability_id: str | None = None,
    recovery_actions: tuple[RecoveryAction, ...] = (),
    result_usability: ResultUsability = ResultUsability.NOT_USABLE,
) -> UiError:
    """Map only an authoritative timeout type; never parse exception text."""
    return UiError(
        code="operation_timed_out",
        category=UiErrorCategory.TIMEOUT,
        user_message="The operation timed out before it completed.",
        technical_detail=type(exc).__name__,
        retryable=True,
        recovery_actions=recovery_actions,
        result_usability=result_usability,
        capability_id=capability_id,
        operation_id=operation_id,
    )


def missing_model_error(*, operation_id: str, capability_id: str, optional: bool) -> UiError:
    return UiError(
        code="optional_model_unavailable" if optional else "required_model_unavailable",
        category=UiErrorCategory.PROVIDER_MODEL,
        user_message=(
            "An optional local model is unavailable. Available deterministic results are retained."
            if optional
            else "A required local model is unavailable for this operation."
        ),
        retryable=False,
        recovery_actions=(
            RecoveryAction("open_runtime_status", "View runtime status"),
            RecoveryAction("open_settings", "Open settings"),
        ),
        result_usability=(
            ResultUsability.PARTIALLY_USABLE if optional else ResultUsability.NOT_USABLE
        ),
        capability_id=capability_id,
        operation_id=operation_id,
    )


def provider_unavailable_error(*, operation_id: str, capability_id: str, optional: bool) -> UiError:
    return UiError(
        code="optional_provider_unavailable" if optional else "required_provider_unavailable",
        category=UiErrorCategory.PROVIDER_MODEL,
        user_message=(
            "The optional provider is unavailable. Available deterministic results are retained."
            if optional
            else "The configured provider is unavailable for this operation."
        ),
        retryable=True,
        recovery_actions=(
            RecoveryAction("open_settings", "Open settings"),
            RecoveryAction("refresh_runtime", "Refresh runtime status"),
        ),
        result_usability=(
            ResultUsability.PARTIALLY_USABLE if optional else ResultUsability.NOT_USABLE
        ),
        capability_id=capability_id,
        operation_id=operation_id,
    )


def capability_runtime_unavailable_error(*, operation_id: str, capability_id: str) -> UiError:
    return UiError(
        code="capability_runtime_unavailable",
        category=UiErrorCategory.CAPABILITY_UNAVAILABLE,
        user_message="A required optional-runtime component is not installed for this operation.",
        retryable=False,
        recovery_actions=(RecoveryAction("open_runtime_status", "View runtime status"),),
        result_usability=ResultUsability.NOT_USABLE,
        capability_id=capability_id,
        operation_id=operation_id,
    )


def analysis_error(exc: BaseException, *, operation_id: str) -> UiError:
    """Translate presentation-safe input rejection without exposing backend types."""
    if isinstance(exc, TimeoutError):
        return timeout_error(
            exc,
            operation_id=operation_id,
            recovery_actions=(RecoveryAction("select_audio", "Return to Analyze"),),
        )
    if isinstance(exc, ImportError):
        return capability_runtime_unavailable_error(
            operation_id=operation_id,
            capability_id="local_ml_runtime",
        )
    if isinstance(exc, (ValueError, FileNotFoundError, IsADirectoryError)):
        return UiError(
            code="analysis_input_rejected",
            category=UiErrorCategory.VALIDATION,
            user_message="The selected audio could not be analyzed. Check the input and try again.",
            technical_detail=type(exc).__name__,
            recovery_actions=(RecoveryAction("select_audio", "Select another file"),),
            result_usability=ResultUsability.NOT_USABLE,
            operation_id=operation_id,
        )
    return unexpected_error(exc, operation_id=operation_id)


def reference_error(exc: BaseException, *, operation_id: str) -> UiError:
    """Translate reference input rejection without exposing backend exceptions."""
    if isinstance(exc, TimeoutError):
        return timeout_error(
            exc,
            operation_id=operation_id,
            recovery_actions=(RecoveryAction("select_references", "Return to References"),),
        )
    if isinstance(exc, (ValueError, FileNotFoundError, IsADirectoryError)):
        return UiError(
            code="reference_input_rejected",
            category=UiErrorCategory.VALIDATION,
            user_message="The selected tracks could not be compared. Check the inputs and try again.",
            technical_detail=type(exc).__name__,
            recovery_actions=(RecoveryAction("select_references", "Select other tracks"),),
            result_usability=ResultUsability.NOT_USABLE,
            operation_id=operation_id,
        )
    return unexpected_error(exc, operation_id=operation_id)


def knowledge_error(exc: BaseException, *, operation_id: str) -> UiError:
    """Translate knowledge search failures without leaking backend details."""
    if isinstance(exc, TimeoutError):
        return timeout_error(
            exc,
            operation_id=operation_id,
            capability_id="rag_retrieval",
            recovery_actions=(RecoveryAction("open_knowledge", "Return to Knowledge"),),
        )
    if isinstance(exc, ValueError):
        return UiError(
            code="knowledge_query_invalid",
            category=UiErrorCategory.VALIDATION,
            user_message="Enter a knowledge query and try again.",
            technical_detail=type(exc).__name__,
            recovery_actions=(RecoveryAction("open_knowledge", "Return to Knowledge"),),
            result_usability=ResultUsability.NOT_USABLE,
            operation_id=operation_id,
        )
    if isinstance(exc, (ImportError, FileNotFoundError)):
        return UiError(
            code="knowledge_runtime_unavailable",
            category=UiErrorCategory.CAPABILITY_UNAVAILABLE,
            user_message="Knowledge search is unavailable on this installation.",
            technical_detail=type(exc).__name__,
            retryable=False,
            recovery_actions=(
                RecoveryAction("open_runtime_status", "View runtime status"),
                RecoveryAction("open_settings", "Open settings"),
            ),
            result_usability=ResultUsability.NOT_USABLE,
            operation_id=operation_id,
            capability_id="rag_retrieval",
        )
    return UiError(
        code="knowledge_retrieval_failed",
        category=UiErrorCategory.INTERNAL,
        user_message="Knowledge search could not be completed.",
        technical_detail=type(exc).__name__,
        retryable=True,
        recovery_actions=(RecoveryAction("open_knowledge", "Return to Knowledge"),),
        result_usability=ResultUsability.NOT_USABLE,
        operation_id=operation_id,
        capability_id="rag_retrieval",
    )


def report_error(exc: BaseException, *, operation_id: str, action: str) -> UiError:
    if isinstance(exc, TimeoutError):
        return timeout_error(
            exc,
            operation_id=operation_id,
            recovery_actions=(RecoveryAction("open_reports", "Return to Reports"),),
            result_usability=ResultUsability.USABLE,
        )
    if isinstance(exc, FileNotFoundError):
        message = "The report file or destination folder is missing."
        code = "report_path_missing"
        recovery = (RecoveryAction("open_reports", "Return to Reports"),)
    elif isinstance(exc, FileExistsError):
        message = "The destination already exists and overwrite was not confirmed."
        code = "report_destination_exists"
        recovery = (RecoveryAction("choose_export_destination", "Choose another destination"),)
    elif isinstance(exc, UnicodeDecodeError):
        message = "The report preview is not valid UTF-8 text."
        code = "report_encoding_unsupported"
        recovery = (RecoveryAction("open_reports", "Return to Reports"),)
    elif isinstance(exc, ValueError):
        message = "This report type, format, or destination is not supported."
        code = "report_format_unsupported"
        recovery = (RecoveryAction("open_reports", "Return to Reports"),)
    elif isinstance(exc, PermissionError):
        message = "The report destination is not writable. Choose another destination."
        code = "report_destination_not_writable"
        recovery = (RecoveryAction("choose_export_destination", "Choose another destination"),)
    else:
        message = f"The report {action} could not be completed."
        code = f"report_{action}_failed"
        recovery = (RecoveryAction("open_reports", "Return to Reports"),)
    return UiError(
        code=code,
        category=UiErrorCategory.REPORT_EXPORT,
        user_message=message,
        technical_detail=type(exc).__name__,
        retryable=not isinstance(exc, (UnicodeDecodeError, ValueError)),
        recovery_actions=recovery,
        result_usability=ResultUsability.USABLE,
        operation_id=operation_id,
    )


def report_open_error() -> UiError:
    return UiError(
        code="report_folder_open_failed",
        category=UiErrorCategory.REPORT_EXPORT,
        user_message="The report folder could not be opened.",
        retryable=False,
        recovery_actions=(RecoveryAction("open_reports", "Return to Reports"),),
        result_usability=ResultUsability.USABLE,
    )


def settings_error(exc: BaseException, *, operation_id: str | None = None) -> UiError:
    return UiError(
        code="settings_snapshot_failed",
        category=UiErrorCategory.CONFIGURATION,
        user_message="The effective application settings could not be loaded.",
        technical_detail=type(exc).__name__,
        retryable=True,
        recovery_actions=(RecoveryAction("retry_settings", "Reload settings"),),
        result_usability=ResultUsability.USABLE,
        operation_id=operation_id,
    )


def runtime_refresh_error(exc: BaseException, *, operation_id: str) -> UiError:
    if isinstance(exc, TimeoutError):
        return timeout_error(
            exc,
            operation_id=operation_id,
            recovery_actions=(RecoveryAction("refresh_runtime", "Refresh runtime status"),),
            result_usability=ResultUsability.USABLE,
        )
    return UiError(
        code="runtime_status_refresh_failed",
        category=UiErrorCategory.CONFIGURATION,
        user_message="Runtime status could not be refreshed.",
        technical_detail=type(exc).__name__,
        retryable=True,
        recovery_actions=(RecoveryAction("refresh_runtime", "Refresh runtime status"),),
        result_usability=ResultUsability.USABLE,
        operation_id=operation_id,
    )


def session_persistence_error(exc: BaseException) -> UiError:
    return UiError(
        code="session_persistence_failed",
        category=UiErrorCategory.PERSISTENCE,
        user_message="The current desktop session could not be saved.",
        technical_detail=type(exc).__name__,
        retryable=True,
        result_usability=ResultUsability.USABLE,
    )


ExceptionHook = Callable[[type[BaseException], BaseException, TracebackType | None], None]


class ExceptionBoundary:
    """Install a logging exception hook and forward a safe UI error."""

    def __init__(self, on_error: Callable[[UiError], None]) -> None:
        self._on_error = on_error
        self._previous_hook: ExceptionHook | None = None

    def install(self) -> None:
        if self._previous_hook is None:
            self._previous_hook = sys.excepthook
            sys.excepthook = self._handle

    def uninstall(self) -> None:
        if self._previous_hook is not None:
            sys.excepthook = self._previous_hook
            self._previous_hook = None

    def _handle(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        logger.critical("Unhandled desktop exception", exc_info=(exc_type, exc, traceback))
        self._on_error(unexpected_error(exc))

