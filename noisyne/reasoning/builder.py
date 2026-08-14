from __future__ import annotations


from .models import (
    ReasoningContext,
    ReasoningPrompt,
)


from .formatter import (
    ReasoningFormatter,
)


from .prompts import (
    SYSTEM_PROMPT,
)



class PromptBuilder:


    def __init__(self) -> None:


        self._formatter = ReasoningFormatter()



    def build(
        self,
        context: ReasoningContext,
    ) -> ReasoningPrompt:


        return ReasoningPrompt(

            system=SYSTEM_PROMPT,

            user=self._formatter.build(

                context

            ),

        )