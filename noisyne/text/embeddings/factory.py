from __future__ import annotations

from .registry import EmbeddingRegistry
from .bge import BGEEmbedding


_registry = EmbeddingRegistry()

_registry.register(
    BGEEmbedding,
)


class EmbeddingFactory:

    def __init__(
        self,
        registry: EmbeddingRegistry | None = None,
    ) -> None:

        self._registry = registry or _registry

    def create(
        self,
        provider: str = "bge-m3",
    ):

        cls = self._registry.get(provider)

        return cls()