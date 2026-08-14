from __future__ import annotations

from noisyne.orchestration.models import Plan
from noisyne.orchestration.state import State


FINAL_STAGES = (
    "compression",
    "prompt",
    "llm",
)


class Router:

    def route(self, state: State) -> State:

        plan = state.plan

        pipeline = []

        if plan.use_memory:
            pipeline.append("memory")

        if plan.use_rag:
            pipeline.append("rag")

        if plan.use_audio:
            pipeline.append("audio")

        if plan.use_vision:
            pipeline.append("vision")

        if plan.use_reasoning:
            pipeline.append("reasoning")

        if plan.use_tools:
            pipeline.append("tools")

        if plan.use_recommendation:
            pipeline.append("recommendation")

        if plan.use_report:
            pipeline.append("report")

        pipeline.extend(FINAL_STAGES)

        state.pipeline = pipeline

        return state