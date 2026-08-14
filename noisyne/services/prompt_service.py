from __future__ import annotations

from noisyne.prompt.context_builder import ContextBuilder
from noisyne.prompt.prompt_builder import PromptBuilder


class PromptService:

    def __init__(self):

        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()

    def build(
        self,
        question: str,
        documents: list,
    ) -> tuple[str, str]:

        context = self.context_builder.build(
            documents
        )

        prompt = self.prompt_builder.build(
            question=question,
            context=context,
        )

        return context, prompt