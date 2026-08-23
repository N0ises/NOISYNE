from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VectorRecord:
    id: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    document: str | None = None


@dataclass(slots=True)
class SearchResult:
    ids: list[str]
    distances: list[float]
    metadatas: list[dict]
    documents: list[str]