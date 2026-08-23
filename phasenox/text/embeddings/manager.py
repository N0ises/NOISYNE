from __future__ import annotations

from .factory import EmbeddingFactory
from .models import TextEmbedding


class TextEmbeddingManager:

    def __init__(
        self,
        provider: str = "bge-m3",
        factory: EmbeddingFactory | None = None,
    ) -> None:

        self._factory = factory or EmbeddingFactory()

        self._provider = self._factory.create(provider)

    @property
    def provider(self):

        return self._provider

    def encode(
        self,
        text: str | list[str],
    ) -> TextEmbedding:

        vector = self._provider.encode(text)

        return TextEmbedding(
            provider=self._provider.name,
            vector=vector,
            dimension=self._provider.dimension,
        )