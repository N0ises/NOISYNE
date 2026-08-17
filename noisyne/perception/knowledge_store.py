from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .knowledge_contracts import (
    KNOWLEDGE_FOUNDATION_SCHEMA_VERSION,
    KnowledgeFilter,
    KnowledgeQuery,
    KnowledgeRetrievalResult,
    MemoryItem,
    MemoryScope,
    RetrievedKnowledgeItem,
)


@runtime_checkable
class MemoryStore(Protocol):
    """Backend-neutral storage interface for Sprint 13 memory items.

    Implementations must preserve deterministic identity, scope isolation, and
    provenance.  They must not silently promote session memory to persistent
    memory or leak project-local data into global user memory.
    """

    def put(self, item: MemoryItem) -> MemoryItem:
        """Store or replace an item by memory_id and return the stored item."""
        ...

    def get(self, memory_id: str) -> MemoryItem | None:
        """Retrieve one item by exact memory_id, or None if absent."""
        ...

    def search(self, query: KnowledgeQuery) -> KnowledgeRetrievalResult:
        """Return deterministic ordered results matching the query filter."""
        ...

    def list(
        self,
        *,
        scope: MemoryScope | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> tuple[MemoryItem, ...]:
        """List stored items with optional scope/project/user filtering."""
        ...

    def delete(self, memory_id: str) -> bool:
        """Delete one item.  Return True if it existed, False otherwise."""
        ...

    def clear_scope(
        self,
        scope: MemoryScope,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Delete all items in the given scope, returning deletion count."""
        ...


@dataclass(frozen=True, slots=True)
class InMemoryMemoryStore:
    """Deterministic local backend for Sprint 13 tests.

    Stores items in memory only.  Scope isolation is enforced by filters;
    deletion is explicit and does not affect unrelated scopes.
    """

    _items: dict[str, MemoryItem] = field(default_factory=dict, repr=False)
    provider_identity: str = "noisyne.in_memory_memory_store"
    retrieval_policy: str = "deterministic_filter_sort"
    schema_version: str = KNOWLEDGE_FOUNDATION_SCHEMA_VERSION

    def put(self, item: MemoryItem) -> MemoryItem:
        self._items[item.memory_id] = item
        return item

    def get(self, memory_id: str) -> MemoryItem | None:
        return self._items.get(memory_id)

    def search(self, query: KnowledgeQuery) -> KnowledgeRetrievalResult:
        results: list[RetrievedKnowledgeItem] = []
        for rank, item in enumerate(self._matching_items(query.filters)):
            result_id = f"{query.query_id}::{item.memory_id}"
            results.append(
                RetrievedKnowledgeItem(
                    result_id=result_id,
                    query_id=query.query_id,
                    memory_item=item,
                    rank=rank,
                )
            )
        return KnowledgeRetrievalResult(
            query_id=query.query_id,
            provider_identity=self.provider_identity,
            results=results,
            retrieval_policy=self.retrieval_policy,
        )

    def list(
        self,
        *,
        scope: MemoryScope | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> tuple[MemoryItem, ...]:
        matching = []
        for item in self._items.values():
            if scope is not None and item.scope is not scope:
                continue
            if project_id is not None and item.project_id != project_id:
                continue
            if user_id is not None and item.user_id != user_id:
                continue
            matching.append(item)
        return tuple(sorted(matching, key=lambda i: (i.created_at or "", i.memory_id)))

    def delete(self, memory_id: str) -> bool:
        return self._items.pop(memory_id, None) is not None

    def clear_scope(
        self,
        scope: MemoryScope,
        *,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        to_delete = [
            memory_id
            for memory_id, item in self._items.items()
            if item.scope is scope
            and (project_id is None or item.project_id == project_id)
            and (user_id is None or item.user_id == user_id)
        ]
        for memory_id in to_delete:
            del self._items[memory_id]
        return len(to_delete)

    def count(self) -> int:
        return len(self._items)

    def _matching_items(self, filters: KnowledgeFilter) -> list[MemoryItem]:
        matching = []
        for item in self._items.values():
            if filters.memory_types and item.memory_type not in filters.memory_types:
                continue
            if filters.scopes and item.scope not in filters.scopes:
                continue
            if filters.provenance_kinds and item.provenance not in filters.provenance_kinds:
                continue
            if filters.project_id is not None and item.project_id != filters.project_id:
                continue
            if filters.user_id is not None and item.user_id != filters.user_id:
                continue
            if (
                filters.source_identity is not None
                and item.source_identity != filters.source_identity
            ):
                continue
            if filters.trust_basis and item.trust_basis not in filters.trust_basis:
                continue
            if (
                filters.created_after is not None
                and (item.created_at or "") < filters.created_after
            ):
                continue
            if (
                filters.created_before is not None
                and (item.created_at or "") > filters.created_before
            ):
                continue
            matching.append(item)
        return sorted(matching, key=lambda i: (i.created_at or "", i.memory_id))


__all__ = [
    "InMemoryMemoryStore",
    "MemoryStore",
]
