from __future__ import annotations

from noisyne.llm.service import LLMService as CoreLLMService


class LLMService:

    def __init__(self):

        self.llm = CoreLLMService()

    def ask(
        self,
        prompt: str,
    ) -> str:

        return self.llm.generate(prompt)