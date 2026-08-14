from __future__ import annotations

import logging

from noisyne.orchestration.state import State

from noisyne.pipeline.engine import PipelineEngine


from noisyne.pipeline.memory_stage import MemoryStage
from noisyne.pipeline.rag_stage import RAGStage
from noisyne.pipeline.compression_stage import CompressionStage
from noisyne.pipeline.prompt_stage import PromptStage
from noisyne.pipeline.llm_stage import LLMStage
from noisyne.pipeline.vision_stage import VisionStage


logger = logging.getLogger(__name__)


class Executor:

    def __init__(self):

        self.engine = PipelineEngine()

        self.engine.register(
            "memory",
            MemoryStage(),
        )

        self.engine.register(
            "rag",
            RAGStage(),
        )

        self.engine.register(
            "compression",
            CompressionStage(),
        )

        self.engine.register(
            "prompt",
            PromptStage(),
        )

        self.engine.register(
            "llm",
            LLMStage(),
        )

        self.engine.register(
            "vision",
            VisionStage(),
        )

    def execute(
        self,
        state: State,
    ) -> State:

        logger.info("EXECUTION")

        return self.engine.run(state)