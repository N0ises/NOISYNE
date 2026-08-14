from __future__ import annotations

from noisyne.infrastructure.providers import LLMProvider


class BaseLLM(LLMProvider):

    @property
    def name(self) -> str:

        raise NotImplementedError

    def initialize(self) -> None:

        pass

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        raise NotImplementedError