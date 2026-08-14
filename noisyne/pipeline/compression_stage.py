from __future__ import annotations

from noisyne.orchestration.state import State
from noisyne.pipeline import Stage
from noisyne.services import CompressionService


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