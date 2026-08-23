from __future__ import annotations

from phasenox.audio.embeddings.models import AudioEmbedding
from phasenox.memory.vector import VectorManager, VectorRecord
from phasenox.memory.vector.naming import CollectionNames


class AudioMemory:

    def __init__(
        self,
        manager: VectorManager | None = None,
    ) -> None:

        self._manager = manager

    def _manager_for_embedding(
        self,
        embedding: AudioEmbedding,
    ) -> VectorManager:

        if self._manager is not None:
            return self._manager

        return VectorManager(
            collection=CollectionNames.audio(
                model=embedding.model,
                dimension=len(embedding.vector),
            )
        )

    def store(
        self,
        *,
        audio_id: str,
        embedding: AudioEmbedding,
        metadata: dict,
        document: str | None = None,
    ) -> None:

        manager = self._manager_for_embedding(embedding)

        record = VectorRecord(
            id=audio_id,
            embedding=embedding.vector.tolist(),
            metadata=metadata,
            document=document,
        )

        manager.add(record)

    def search(
        self,
        embedding: AudioEmbedding,
        top_k: int = 5,
    ):

        manager = self._manager_for_embedding(embedding)

        return manager.search(
            embedding.vector.tolist(),
            top_k,
        )