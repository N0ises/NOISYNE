from __future__ import annotations

from .base import BaseAIProvider
from .models import GenerateRequest, GenerateResponse


class OpenAIProvider(BaseAIProvider):
    """Stub provider for OpenAI-compatible APIs. Reserved for future implementation."""

    name = "openai"

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        raise NotImplementedError(
            "OpenAIProvider is not yet implemented. Use QwenProvider or MockProvider."
        )
