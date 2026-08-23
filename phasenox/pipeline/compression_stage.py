from __future__ import annotations

from phasenox.orchestration.state import State
from phasenox.pipeline import Stage
from phasenox.services import CompressionService


class CompressionStage(Stage):

    def __init__(self):

        self.service = CompressionService()

    def run(
        self,
        state: State,
    ) -> State:

        state.context = self.service.compress(
            state.question,
            state.documents,
        )

        return state