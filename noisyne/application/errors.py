"""Sprint 15 bounded application error taxonomy.

Public error contracts never carry stack traces, credentials, endpoint URLs,
prompts, or secrets.  Internal exception detail may be chained on the service
side for logs/debugging but is not serialized into results.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from noisyne.perception._serialization import JsonContract


class ApplicationErrorCode(str, Enum):
    """Stable, bounded application error taxonomy."""

    INVALID_REQUEST = "invalid_request"
    AUDIO_DECODE_FAILURE = "audio_decode_failure"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    RUNTIME_DEPENDENCY_UNAVAILABLE = "runtime_dependency_unavailable"
    ANALYSIS_FAILURE = "analysis_failure"
    REFERENCE_FAILURE = "reference_failure"
    REASONING_FAILURE = "reasoning_failure"
    SERIALIZATION_FAILURE = "serialization_failure"
    INTERNAL_FAILURE = "internal_failure"


@dataclass(frozen=True, slots=True)
class ApplicationError(JsonContract):
    """One bounded, transport-safe application error."""

    code: ApplicationErrorCode
    message: str
    stage_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, ApplicationErrorCode):
            raise TypeError("code must be an ApplicationErrorCode")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string")
        if self.stage_id is not None and (
            not isinstance(self.stage_id, str) or not self.stage_id.strip()
        ):
            raise ValueError("stage_id must be a non-empty string or None")


__all__ = [
    "ApplicationError",
    "ApplicationErrorCode",
]
