from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MemoryConfigurationError(Exception):
    """A structured, testable failure state for memory configuration problems.

    Attributes:
        reason: One of ``missing`` or ``invalid``.
        path: The configuration file or directory involved.
        message: Human-readable explanation.
        details: Optional additional context (e.g., the underlying exception).
    """

    reason: str
    path: Path | None
    message: str
    details: Any = None

    def __str__(self) -> str:
        path_str = str(self.path) if self.path else "<unknown>"
        return f"Memory configuration {self.reason}: {path_str} — {self.message}"
