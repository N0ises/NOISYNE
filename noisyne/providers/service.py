from __future__ import annotations

from .base import BaseAIProvider
from .factory import ProviderFactory
from .models import GenerateRequest, GenerateResponse


class ProviderService:
    """Application-level facade for AI provider calls."""

    def __init__(self, provider: BaseAIProvider | None = None) -> None:
        self._provider = provider or ProviderFactory.default()

    @property
    def provider(self) -> BaseAIProvider:
        return self._provider

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        return self._provider.generate(request)
