from __future__ import annotations

from phasenox.orchestration.state import State
from phasenox.pipeline import Stage

from phasenox.services import LLMService


class LLMStage(Stage):

    def __init__(self):

        self.llm = LLMService()

    def run(
        self,
        state: State,
    ) -> State:

        state.answer = self.llm.ask(
            state.prompt
        )

        return state