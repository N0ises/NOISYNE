from __future__ import annotations

from phasenox.llm.base import BaseLLM
from phasenox.llm.lmstudio import LMStudioLLM


class LLMManager:

    def __init__(self) -> None:

        self._providers: dict[str, BaseLLM] = {}

        self.register(
            LMStudioLLM()
        )

    def register(
        self,
        provider: BaseLLM,
    ) -> None:

        self._providers[
            provider.name
        ] = provider

    def get(
        self,
        name: str,
    ) -> BaseLLM:

        if name not in self._providers:

            raise LookupError(
                f"LLM provider '{name}' not found."
            )

        return self._providers[name]