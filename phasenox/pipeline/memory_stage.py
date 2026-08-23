from __future__ import annotations

from phasenox.orchestration.state import State
from phasenox.pipeline import Stage


class MemoryStage(Stage):

    def run(
        self,
        state: State,
    ) -> State:

        return state