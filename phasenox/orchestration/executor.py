from __future__ import annotations

import logging

from phasenox.orchestration.state import State

from phasenox.pipeline.engine import PipelineEngine


from phasenox.pipeline.memory_stage import MemoryStage
from phasenox.pipeline.rag_stage import RAGStage
from phasenox.pipeline.compression_stage import CompressionStage
from phasenox.pipeline.prompt_stage import PromptStage
from phasenox.pipeline.llm_stage import LLMStage
from phasenox.pipeline.vision_stage import VisionStage


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