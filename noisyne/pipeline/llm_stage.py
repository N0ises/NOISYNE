from __future__ import annotations

from noisyne.orchestration.state import State
from noisyne.pipeline import Stage

from noisyne.services import LLMService


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