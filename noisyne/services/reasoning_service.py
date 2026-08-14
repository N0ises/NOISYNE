from __future__ import annotations


class ReasoningService:
    """
    Handles reasoning decisions before the LLM call.
    """

    def think(
        self,
        question: str,
    ) -> bool:

        # فعلاً نسخه ساده
        # بعداً اینجا Chain-of-Thought / Deep Reasoning
        # یا حتی یک LLM جدا قرار می‌گیرد.

        return True