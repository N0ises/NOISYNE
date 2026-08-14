from __future__ import annotations

from .base import AudioEmbeddingModel
from .registry import EmbeddingRegistry


class EmbeddingFactory:
    """
    Creates embedding providers.
    """

    def __init__(
        self,
        registry: EmbeddingRegistry,
    ) -> None:

        self._registry = registry

    def create(
        self,
        provider: str,
    ) -> AudioEmbeddingModel:

        return self._registry.get(provider)