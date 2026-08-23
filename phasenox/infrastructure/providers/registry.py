from __future__ import annotations

from typing import Dict

from phasenox.infrastructure.providers.base import Provider


class ProviderRegistry:

    def __init__(self):

        self._providers: Dict[str, Provider] = {}

    def register(
        self,
        provider: Provider,
    ) -> None:

        self._providers[
            provider.name
        ] = provider

    def get(
        self,
        name: str,
    ) -> Provider:

        return self._providers[name]

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._providers

    def all(self):

        return list(
            self._providers.values()
        )


provider_registry = ProviderRegistry()