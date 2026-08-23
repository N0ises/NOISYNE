from __future__ import annotations

from phasenox.orchestration.state import State
from phasenox.pipeline import Stage

from phasenox.services import PromptService


class PromptStage(Stage):

    def __init__(self):

        self.prompt = PromptService()

    def run(
        self,
        state: State,
    ) -> State:

        state.context, state.prompt = self.prompt.build(
            question=state.question,
            documents=state.documents,
        )

        return state