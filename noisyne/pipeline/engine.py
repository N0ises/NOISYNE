from __future__ import annotations

import logging

from noisyne.orchestration.state import State


logger = logging.getLogger(__name__)


class PipelineEngine:

    def __init__(self):

        self.stages: dict[str, object] = {}

    def register(
        self,
        name: str,
        stage,
    ) -> None:

        self.stages[name] = stage

    def run(
        self,
        state: State,
    ) -> State:

        logger.info("Pipeline: %s", state.pipeline)

        for stage_name in state.pipeline:

            stage = self.stages.get(stage_name)

            if stage is None:

                logger.debug("Skipping -> %s", stage_name)

                continue

            logger.debug("Running -> %s", stage_name)

            state = stage.run(state)

        return state