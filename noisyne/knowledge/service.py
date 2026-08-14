from __future__ import annotations

from .models import KnowledgeBundle
from .registry import KnowledgeRegistry
from .resolver import KnowledgeResolver


class KnowledgeService:
    """
    Singleton-style facade for the Knowledge Infrastructure.

    The service is optional and isolated. No business logic imports it in
    Sprint 7; future sprints will inject ``KnowledgeResolver`` into specific
    modules while keeping the service itself as a convenient loader.
    """

    def __init__(
        self,
        registry: KnowledgeRegistry | None = None,
    ) -> None:
        self._registry = registry or KnowledgeRegistry()
        self._bundle_cache: KnowledgeBundle | None = None
        self._resolver_cache: KnowledgeResolver | None = None

    def resolver(self) -> KnowledgeResolver:
        """Return a ``KnowledgeResolver`` for the loaded bundle."""
        if self._resolver_cache is None:
            self._resolver_cache = KnowledgeResolver(self._bundle())
        return self._resolver_cache

    def reload(self) -> None:
        """Reload knowledge from the default source and clear caches."""
        self._bundle_cache = self._registry.load_default()
        self._resolver_cache = None

    def version(self) -> str:
        return self._bundle().version

    def is_loaded(self) -> bool:
        return self._bundle_cache is not None

    def bundle(self) -> KnowledgeBundle:
        return self._bundle()

    def _bundle(self) -> KnowledgeBundle:
        if self._bundle_cache is None:
            self._bundle_cache = self._registry.load_default()
        return self._bundle_cache
