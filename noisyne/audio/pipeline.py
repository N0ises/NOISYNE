from __future__ import annotations

from pathlib import Path

from noisyne.audio.embeddings.bootstrap import create_embedding_registry
from noisyne.audio.embeddings.encoder import AudioEncoder
from noisyne.audio.embeddings.factory import EmbeddingFactory
from noisyne.audio.embeddings.tasks import EmbeddingTask

from noisyne.audio.io import AudioIOService
from noisyne.audio.memory import AudioMemory


class AudioPipeline:
    """
    High-level audio indexing and semantic search pipeline.
    """

    def __init__(self) -> None:
        self.io = AudioIOService()

        registry = create_embedding_registry()

        factory = EmbeddingFactory(registry)

        self.encoder = AudioEncoder(
            factory=factory,
        )

        self.memory = AudioMemory()

    def index(
        self,
        audio_path: str | Path,
        *,
        audio_id: str,
        metadata: dict,
        document: str | None = None,
    ) -> None:

        audio = self.io.load(audio_path)

        embedding = self.encoder.encode(
            audio,
            task=EmbeddingTask.SEMANTIC_SEARCH,
        )

        self.memory.store(
            audio_id=audio_id,
            embedding=embedding,
            metadata=metadata,
            document=document,
        )

    def search(
        self,
        audio_path: str | Path,
        *,
        top_k: int = 5,
    ):

        audio = self.io.load(audio_path)

        embedding = self.encoder.encode(
            audio,
            task=EmbeddingTask.SEMANTIC_SEARCH,
        )

        return self.memory.search(
            embedding,
            top_k,
        )