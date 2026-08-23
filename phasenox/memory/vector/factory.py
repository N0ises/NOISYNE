from __future__ import annotations

from .config import DEFAULT_PROVIDER
from .registry import VectorRegistry


class VectorFactory:
    """
    Creates Vector providers.
    """

    @staticmethod
    def create(provider: str | None = None):
        provider_name = provider or DEFAULT_PROVIDER

        provider_cls = VectorRegistry.get(provider_name)

        return provider_cls()