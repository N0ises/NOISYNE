from __future__ import annotations

from typing import Type

from .base import TextEmbeddingModel


class EmbeddingRegistry:

    def __init__(self) -> None:

        self._providers: dict[str, Type[TextEmbeddingModel]] = {}

    def register(
        self,
        provider: Type[TextEmbeddingModel],
    ) -> None:

        self._providers[provider().name] = provider

    def get(
        self,
        name: str,
    ) -> Type[TextEmbeddingModel]:

        if name not in self._providers:

            raise KeyError(
                f"Embedding provider '{name}' is not registered."
            )

        return self._providers[name]

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._providers

    def names(
        self,
    ) -> list[str]:

        return sorted(self._providers.keys())