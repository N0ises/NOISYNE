from __future__ import annotations

from noisyne.orchestration.state import State
from noisyne.pipeline import Stage


class MemoryStage(Stage):

    def run(
        self,
        state: State,
    ) -> State:

        return state