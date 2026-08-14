from __future__ import annotations


class PromptBuilder:
    """
    Builds the final LLM prompt.
    """

    SYSTEM_PROMPT = """
You are SoundBrain.

You are an expert audio engineer.

Use ONLY the provided context.

If the answer is not found inside the context,
say that the information is unavailable.

Always answer clearly.

Never invent facts.

Return markdown.
""".strip()

    def build(
        self,
        question: str,
        context: str,
    ) -> str:

        return f"""
{self.SYSTEM_PROMPT}

========================

QUESTION

{question}

========================

CONTEXT

{context}

========================

ANSWER
""".strip()