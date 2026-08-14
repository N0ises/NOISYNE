from __future__ import annotations

from typing import Dict, Type

from .base import BaseVectorProvider


class VectorRegistry:
    """
    Registry for Vector Database providers.
    """

    _providers: Dict[str, Type[BaseVectorProvider]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        provider: Type[BaseVectorProvider],
    ) -> None:
        cls._providers[name.lower()] = provider

    @classmethod
    def get(
        cls,
        name: str,
    ) -> Type[BaseVectorProvider]:
        key = name.lower()

        if key not in cls._providers:
            raise ValueError(f"Unknown vector provider: {name}")

        return cls._providers[key]

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._providers.keys())