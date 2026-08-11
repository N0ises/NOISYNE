from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from .errors import IngestionError


def _source_fingerprint(source: str) -> str:
    """Return a short, deterministic identifier for a source path/name."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _chunk_id(source: str, index: int) -> str:
    """Return a deterministic chunk id for a source + chunk index."""
    return f"{_source_fingerprint(source)}:{index}"


def _flatten_ids(raw_ids) -> list[str]:
    """Normalize Chroma's list-of-lists-or-list ids into a flat list."""
    flat: list[str] = []
    if not raw_ids:
        return flat
    for item in raw_ids:
        if isinstance(item, list):
            flat.extend(item)
        elif isinstance(item, str):
            flat.append(item)
    return flat


def ingest_chunks(
    collection,
    chunks: list,
    batch_size: int = 64,
) -> tuple[int, int]:
    """Idempotently ingest RAG chunks into a Chroma collection.

    For each source, existing chunks with the same ``source`` metadata are
    removed before the new representation is upserted. Chunk ids are derived
    deterministically from the source and chunk index, so repeated ingestion of
    an unchanged source updates the same records and does not duplicate them.

    If stale-chunk removal fails for a source, the function raises
    :class:`IngestionError` instead of silently leaving stale data behind.

    Returns ``(sources_updated, chunks_upserted)``.
    """

    by_source: dict[str, list[tuple[int, Any]]] = defaultdict(list)
    for chunk_index, chunk in enumerate(chunks):
        source = chunk.metadata.get("source", "")
        by_source[source].append((chunk_index, chunk))

    sources_updated = 0
    chunks_upserted = 0

    for source, items in by_source.items():
        # Remove any stale chunks belonging to this source. Using a metadata
        # filter means we do not need to know the exact ids or chunk count from
        # the previous ingestion. If this lookup or deletion fails, we must not
        # silently continue because stale chunks would remain while the caller
        # is told ingestion succeeded.
        try:
            existing = collection.get(where={"source": source})
            existing_ids = _flatten_ids(existing.get("ids"))
            if existing_ids:
                collection.delete(ids=existing_ids)
        except Exception as exc:
            raise IngestionError(
                reason="stale_deletion_failed",
                source=source,
                message="Could not remove stale chunks for the source before upsert.",
                details=exc,
            ) from exc

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for source_index, (_, chunk) in enumerate(items):
            ids.append(_chunk_id(source, source_index))
            documents.append(chunk.page_content)
            metadata = dict(chunk.metadata)
            metadata.setdefault("source", source)
            metadata.setdefault("chunk_index", source_index)
            metadatas.append(metadata)

        total = len(ids)
        for i in range(0, total, batch_size):
            collection.upsert(
                ids=ids[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
            )

        sources_updated += 1
        chunks_upserted += total

    return sources_updated, chunks_upserted
