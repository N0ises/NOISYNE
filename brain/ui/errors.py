"""Desktop exception translation and process-level exception boundary."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from types import TracebackType

from .contracts import UiError, UiErrorCategory

logger = logging.getLogger(__name__)


def unexpected_error(exc: BaseException, *, operation_id: str | None = None) -> UiError:
    return UiError(
        code="unexpected_internal_error",
        category=UiErrorCategory.INTERNAL,
        user_message="An unexpected error occurred.",
        technical_detail=type(exc).__name__,
        retryable=False,
        operation_id=operation_id,
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
