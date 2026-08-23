from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class IngestionError(Exception):
    """A structured, testable failure state for RAG ingestion problems.

    Attributes:
        reason: A short failure classification (e.g., ``stale_deletion_failed``).
        source: The source document whose stale chunks could not be removed.
        message: Human-readable explanation.
        details: Optional underlying exception or provider response.
    """

    reason: str
    source: str
    message: str
    details: Any = None

    def __str__(self) -> str:
        return f"Ingestion error ({self.reason}) for source {self.source!r}: {self.message}"
