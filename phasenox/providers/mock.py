from __future__ import annotations

from .base import BaseAIProvider
from .models import GenerateRequest, GenerateResponse


class MockProvider(BaseAIProvider):
    """
    Deterministic mock provider for tests and offline development.

    Never calls a real model. Returns a safe, predictable response containing the
    provider name and a snippet of the user prompt.
    """

    name = "mock"

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        snippet = request.user_prompt[:60].replace("\n", " ")
        return GenerateResponse(
            text=f"[MOCK:{self.name}] {snippet}",
            provider=self.name,
            confidence=1.0,
            finish_reason="mock",
        )
