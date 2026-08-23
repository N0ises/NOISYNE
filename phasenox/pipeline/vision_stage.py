from __future__ import annotations

from phasenox.orchestration.state import State
from phasenox.pipeline import Stage

from phasenox.services import VisionService


class VisionStage(Stage):

    def __init__(self):

        self.vision = VisionService()

    def run(
        self,
        state: State,
    ) -> State:

        if state.image is not None:

            state.image = self.vision.process(
                state.image
            )

        return state