from __future__ import annotations

from typing import TYPE_CHECKING

from .models import MemoryBundle
from .registry import MemoryRegistry
from .resolver import MemoryResolver

if TYPE_CHECKING:
    from phasenox.knowledge.service import KnowledgeService


class MemoryService:
    """
    Singleton-style facade for the Memory layer.

    Memory is optional and isolated. It wraps a ``MemoryBundle`` and an
    optional ``KnowledgeService`` to produce a ``MemoryResolver`` that can
    override Knowledge preferences when appropriate.
    """

    def __init__(
        self,
        registry: MemoryRegistry | None = None,
        knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self._registry = registry or MemoryRegistry()
        self._knowledge_service = knowledge_service
        self._bundle_cache: MemoryBundle | None = None
        self._resolver_cache: MemoryResolver | None = None

    def resolver(self) -> MemoryResolver:
        """Return a MemoryResolver backed by the loaded bundle and Knowledge."""
        if self._resolver_cache is None:
            knowledge_resolver = None
            if self._knowledge_service is not None:
                knowledge_resolver = self._knowledge_service.resolver()
            self._resolver_cache = MemoryResolver(self._bundle(), knowledge_resolver)
        return self._resolver_cache

    def reload(self) -> None:
        """Reload memory from the default source and clear caches."""
        self._bundle_cache = self._registry.load_default()
        self._resolver_cache = None

    def version(self) -> str:
        return self._bundle().version

    def is_loaded(self) -> bool:
        return self._bundle_cache is not None

    def bundle(self) -> MemoryBundle:
        return self._bundle()

    def _bundle(self) -> MemoryBundle:
        if self._bundle_cache is None:
            self._bundle_cache = self._registry.load_default()
        return self._bundle_cache
