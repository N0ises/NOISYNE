from __future__ import annotations

from .base import BaseAIProvider


class ProviderRegistry:
    """Registry for AI provider instances."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseAIProvider] = {}

    def register(self, provider: BaseAIProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> BaseAIProvider:
        if name not in self._providers:
            raise LookupError(f"AI provider '{name}' is not registered.")
        return self._providers[name]

    def exists(self, name: str) -> bool:
        return name in self._providers

    def list(self) -> list[str]:
        return sorted(self._providers.keys())

    def all(self) -> list[BaseAIProvider]:
        return list(self._providers.values())
