from __future__ import annotations

from phasenox.memory.vector import VectorManager, VectorRecord
from phasenox.memory.vector.naming import CollectionNames

from phasenox.text.embeddings.models import TextEmbedding


class TextMemory:

    def __init__(
        self,
        manager: VectorManager | None = None,
    ) -> None:

        self._manager = manager

    def _get_manager(
        self,
        embedding: TextEmbedding,
    ) -> VectorManager:

        if self._manager is not None:
            return self._manager

        return VectorManager(
            collection=CollectionNames.text(
                model=embedding.provider,
                dimension=embedding.dimension,
            )
        )

    def store(
        self,
        *,
        text_id: str,
        embedding: TextEmbedding,
        metadata: dict | None = None,
        document: str | None = None,
    ) -> None:

        manager = self._get_manager(embedding)

        manager.add(
            VectorRecord(
                id=text_id,
                embedding=embedding.vector.tolist(),
                metadata=metadata or {},
                document=document,
            )
        )

    def search(
        self,
        embedding: TextEmbedding,
        top_k: int = 5,
    ):

        manager = self._get_manager(embedding)

        return manager.search(
            embedding.vector.tolist(),
            top_k=top_k,
        )