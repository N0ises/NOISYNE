from __future__ import annotations

from .bootstrap import create_embedding_factory
from .factory import EmbeddingFactory
from .manager import TextEmbeddingManager
from .models import TextEmbedding


class TextEncoder:

    def __init__(
        self,
        provider: str = "bge-m3",
        factory: EmbeddingFactory | None = None,
    ) -> None:

        if factory is None:
            factory = create_embedding_factory()

        self._manager = TextEmbeddingManager(
            provider=provider,
            factory=factory,
        )

    def encode(
        self,
        text: str | list[str],
    ) -> TextEmbedding:

        return self._manager.encode(text)