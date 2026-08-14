from __future__ import annotations

from .base import BaseAIProvider
from .models import GenerateRequest, GenerateResponse


class LocalProvider(BaseAIProvider):
    """Stub provider for future local inference backends. Reserved for future implementation."""

    name = "local"

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        raise NotImplementedError(
            "LocalProvider is not yet implemented. Use QwenProvider or MockProvider."
        )
