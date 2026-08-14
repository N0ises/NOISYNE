from __future__ import annotations

from noisyne.audio.embeddings.encoder import AudioEncoder
from noisyne.memory.vector import VectorManager
from noisyne.memory.vector.naming import CollectionNames


class AudioSearchService:

    def __init__(
        self,
        model: str = "clap",
        dimension: int = 512,
    ) -> None:

        self._encoder = AudioEncoder(
            provider=model,
        )

        self._manager = VectorManager(
            collection=CollectionNames.audio(
                model=model,
                dimension=dimension,
            )
        )

    def search(
        self,
        text: str,
        top_k: int = 5,
    ):

        embedding = self._encoder.encode_text(
            text,
        )

        return self._manager.search(
            embedding.vector.tolist(),
            top_k,
        )

    def search_embedding(
        self,
        embedding: list[float],
        top_k: int = 5,
    ):

        return self._manager.search(
            embedding,
            top_k,
        )