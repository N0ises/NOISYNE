from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from .ableton import AbletonAdapter
from .base import WorkflowAdapter
from .cubase import CubaseAdapter
from .flstudio import FLStudioAdapter
from .reaper import ReaperAdapter
from .studio_one import StudioOneAdapter


class AdapterFactory:
    """
    Registry and factory for workflow adapters.

    All adapters are registered at import time. No DAW communication is performed
    by the factory; adapters are pure contract placeholders.
    """

    _registry: ClassVar[dict[str, Callable[..., WorkflowAdapter]]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        factory: Callable[..., WorkflowAdapter],
    ) -> None:
        cls._registry[name] = factory

    @classmethod
    def get(cls, name: str) -> WorkflowAdapter | None:
        factory = cls._registry.get(name)
        if factory is None:
            return None
        return factory()

    @classmethod
    def list(cls) -> list[str]:
        return sorted(cls._registry.keys())

    @classmethod
    def default(cls) -> WorkflowAdapter:
        """Return the first registered adapter, or raise if none exist."""
        if not cls._registry:
            raise RuntimeError("No workflow adapters are registered")
        return cls.get(cls.list()[0]) or cls._registry[cls.list()[0]]()


AdapterFactory.register("ableton", AbletonAdapter)
AdapterFactory.register("reaper", ReaperAdapter)
AdapterFactory.register("cubase", CubaseAdapter)
AdapterFactory.register("flstudio", FLStudioAdapter)
AdapterFactory.register("studio_one", StudioOneAdapter)
