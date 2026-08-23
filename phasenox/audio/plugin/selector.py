from __future__ import annotations

from .models import PluginMatch
from .registry import PluginRegistry


class PluginSelector:
    """Select concrete plugin options for a category. Blind to brand prestige."""

    def __init__(self, registry: PluginRegistry | None = None) -> None:
        if registry is None:
            self._registry = PluginRegistry()
        else:
            self._registry = registry

    def select(
        self,
        category: str,
        *,
        formats: list[str] | None = None,
        limit: int = 3,
    ) -> list[PluginMatch]:
        return self._registry.matches(category, formats)[:limit]
