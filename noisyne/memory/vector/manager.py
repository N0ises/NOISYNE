from __future__ import annotations

from .config import DEFAULT_COLLECTION, DEFAULT_TOP_K
from .database import VectorDatabase
from .models import SearchResult, VectorRecord
from .search import VectorSearch


class VectorManager:
    """
    High-level API for vector memory.
    """

    def __init__(
        self,
        provider: str | None = None,
        collection: str = DEFAULT_COLLECTION,
    ) -> None:

        self.database = VectorDatabase(provider)
        self.collection = self.database.collection(collection)

    @property
    def collection_name(self) -> str:
        return self.collection.name

    def add(
        self,
        record: VectorRecord,
    ) -> None:

        # Chroma's raw ``add()`` fails or silently no-ops on duplicate ids
        # depending on the version. Use upsert so repeated adds of the same
        # record id update the existing vector instead of creating stale
        # duplicates.
        self.collection.provider.upsert(
            collection=self.collection.name,
            ids=[record.id],
            embeddings=[record.embedding],
            metadatas=[record.metadata],
            documents=[record.document] if record.document else None,
        )

    def delete(
        self,
        ids: list[str],
    ) -> None:

        self.collection.delete(ids)

    def count(self) -> int:

        return self.collection.count()

    def search(
        self,
        embedding: list[float],
        top_k: int = DEFAULT_TOP_K,
    ) -> SearchResult:

        result = self.collection.provider.query(
            collection=self.collection.name,
            embedding=embedding,
            top_k=top_k,
        )

        return VectorSearch.parse(result)