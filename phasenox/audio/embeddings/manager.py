from __future__ import annotations

from phasenox.audio.embeddings.factory import EmbeddingFactory
from phasenox.audio.embeddings.models import AudioEmbedding
from phasenox.audio.embeddings.tasks import EmbeddingTask
from phasenox.audio.io.models import AudioData


class EmbeddingManager:

    def __init__(
        self,
        factory: EmbeddingFactory,
    ) -> None:

        self._factory = factory

    def audio_provider(
        self,
        provider: str,
    ):

        return self._factory.create(provider)

    def encode(
        self,
        provider: str,
        audio: AudioData,
        task: EmbeddingTask | None = None,
    ) -> AudioEmbedding:

        model = self.audio_provider(provider)

        vector = model.encode_audio(
            audio,
            task=task,
        )

        return AudioEmbedding(
            model=model.name,
            vector=vector,
        )

    def encode_text(
        self,
        provider: str,
        text: str | list[str],
    ) -> AudioEmbedding:

        model = self.audio_provider(provider)

        vector = model.encode_text(text)

        return AudioEmbedding(
            model=model.name,
            vector=vector,
        )