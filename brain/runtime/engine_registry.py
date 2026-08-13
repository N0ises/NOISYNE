from __future__ import annotations

from collections.abc import Callable
from typing import Any


class EngineRegistry:
    """
    Named registry for production engine factories.

    The registry stores callables (usually classes or factory functions) by name.
    It is intentionally lightweight and does not instantiate engines itself.
    """

    def __init__(self) -> None:
        self._engines: dict[str, Callable[..., Any]] = {}

    def register(
        self,
        name: str,
        factory: Callable[..., Any],
    ) -> None:
        """Register an engine factory under a unique name."""
        self._engines[name] = factory

    def get(
        self,
        name: str,
    ) -> Callable[..., Any] | None:
        """Return the registered factory, or ``None`` if not found."""
        return self._engines.get(name)

    def list(self) -> list[str]:
        """Return all registered engine names in sorted order."""
        return sorted(self._engines.keys())

    def exists(self, name: str) -> bool:
        return name in self._engines

    def __contains__(self, name: str) -> bool:
        return self.exists(name)

    def __len__(self) -> int:
        return len(self._engines)


# Global registry instance.
registry = EngineRegistry()


def _register_default_engines() -> None:
    """
    Register the V1 engines.

    Imports are deferred to keep this module lightweight at import time.
    """
    from brain.application.audio_review_service import AudioReviewService
    from brain.application.noisyne_service import NoisyneService
    from brain.reference.pipeline import ReferencePipeline

    registry.register("audio_review", AudioReviewService)
    registry.register("reference_comparison", ReferencePipeline)
    registry.register("noisyne", NoisyneService)
    registry.register("soundbrain", NoisyneService)


_register_default_engines()

__all__ = [
    "EngineRegistry",
    "registry",
]
