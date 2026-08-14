from __future__ import annotations

from noisyne.audio.embeddings.bootstrap import create_embedding_factory
from noisyne.audio.embeddings.factory import EmbeddingFactory
from noisyne.audio.embeddings.manager import EmbeddingManager
from noisyne.audio.embeddings.models import AudioEmbedding
from noisyne.audio.embeddings.tasks import EmbeddingTask
from noisyne.audio.io.models import AudioData


class AudioEncoder:

    def __init__(
        self,
        provider: str = "clap",
        factory: EmbeddingFactory | None = None,
    ) -> None:

        if factory is None:
            factory = create_embedding_factory()

        self._provider = provider

        self._manager = EmbeddingManager(factory)

    def encode(
        self,
        audio: AudioData,
        task: EmbeddingTask | None = None,
    ) -> AudioEmbedding:

        return self._manager.encode(
            provider=self._provider,
            audio=audio,
            task=task,
        )

    def encode_text(
        self,
        text: str | list[str],
    ) -> AudioEmbedding:

        return self._manager.encode_text(
            provider=self._provider,
            text=text,
        )