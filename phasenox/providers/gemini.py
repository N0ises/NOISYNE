from __future__ import annotations

from .base import BaseAIProvider
from .models import GenerateRequest, GenerateResponse


class GeminiProvider(BaseAIProvider):
    """Stub provider for Google Gemini. Reserved for future implementation."""

    name = "gemini"

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        raise NotImplementedError(
            "GeminiProvider is not yet implemented. Use QwenProvider or MockProvider."
        )
