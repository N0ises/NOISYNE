from __future__ import annotations

from noisyne.infrastructure.providers import provider_registry
from noisyne.llm.lmstudio import LMStudioLLM


class LLMService:

    def __init__(self):

        if not provider_registry.exists("lmstudio"):

            provider_registry.register(
                LMStudioLLM()
            )

        self.provider = provider_registry.get(
            "lmstudio"
        )

    def generate(
        self,
        prompt: str,
    ) -> str:

        return self.provider.generate(prompt)