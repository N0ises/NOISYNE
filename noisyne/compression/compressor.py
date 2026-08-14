from __future__ import annotations

from noisyne.compression.prompt import build_prompt
from noisyne.services.llm_service import LLMService


class Compressor:

    def __init__(self):

        self.llm = LLMService()

    def compress(
        self,
        question: str,
        documents: list,
    ) -> str:

        if not documents:
            return ""

        context = "\n\n".join(
            doc.text
            for doc in documents
        )

        prompt = build_prompt(
            question,
            context,
        )

        return self.llm.ask(prompt)


_compressor = Compressor()


def compress(
    question: str,
    documents: list,
) -> str:

    return _compressor.compress(
        question,
        documents,
    )