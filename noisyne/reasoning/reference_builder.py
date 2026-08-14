from __future__ import annotations

from dataclasses import dataclass

from .prompts import SYSTEM_PROMPT
from .reference_formatter import ReferenceReasoningFormatter
from .reference_models import ReferenceReasoningContext


@dataclass(slots=True)
class ReferencePrompt:

    system: str

    user: str


class ReferencePromptBuilder:

    def __init__(
        self,
        formatter: ReferenceReasoningFormatter | None = None,
    ) -> None:

        self._formatter = formatter or ReferenceReasoningFormatter()

    def build(
        self,
        context: ReferenceReasoningContext,
    ) -> ReferencePrompt:

        return ReferencePrompt(

            system=SYSTEM_PROMPT,

            user=self._formatter.build(
                context,
            ),

        )