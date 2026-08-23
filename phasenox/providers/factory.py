from __future__ import annotations

from typing import ClassVar

from .base import BaseAIProvider
from .registry import ProviderRegistry


class ProviderFactory:
    """
    Factory and registry holder for AI providers.

    Providers are registered lazily on first access so that importing this module
    does not pull in heavy backends such as transformers or torch.
    """

    _registry: ClassVar[ProviderRegistry | None] = None

    @classmethod
    def _ensure_registry(cls) -> ProviderRegistry:
        if cls._registry is None:
            cls._registry = ProviderRegistry()
            cls._register_defaults()
        return cls._registry

    @classmethod
    def _register_defaults(cls) -> None:
        # Lazy imports keep the factory import-time lightweight.
        from .gemini import GeminiProvider
        from .local import LocalProvider
        from .mock import MockProvider
        from .openai import OpenAIProvider
        from .qwen import QwenProvider

        registry = cls._registry
        if registry is None:
            return
        registry.register(MockProvider())
        registry.register(QwenProvider())
        registry.register(GeminiProvider())
        registry.register(OpenAIProvider())
        registry.register(LocalProvider())

    @classmethod
    def register(cls, provider: BaseAIProvider) -> None:
        cls._ensure_registry().register(provider)

    @classmethod
    def get(cls, name: str) -> BaseAIProvider:
        return cls._ensure_registry().get(name)

    @classmethod
    def exists(cls, name: str) -> bool:
        return cls._ensure_registry().exists(name)

    @classmethod
    def list(cls) -> list[str]:
        return cls._ensure_registry().list()

    @classmethod
    def default(cls) -> BaseAIProvider:
        """
        Return the configured production provider.

        Reads ``settings.llm.provider`` and falls back to ``qwen`` when the
        configured provider is missing or unrecognized. This makes QwenProvider the
        default production provider while preserving configurability.
        """
        provider_name = "qwen"
        try:
            from phasenox.infrastructure.config import settings

            provider_name = settings.llm.provider
            if provider_name in ("lmstudio", "local-model"):
                provider_name = "qwen"
        except (ImportError, AttributeError, KeyError, ValueError, OSError):
            provider_name = "qwen"

        registry = cls._ensure_registry()
        if registry.exists(provider_name):
            return registry.get(provider_name)

        if registry.exists("qwen"):
            return registry.get("qwen")

        if registry.exists("mock"):
            return registry.get("mock")

        raise RuntimeError("No AI providers are registered.")
