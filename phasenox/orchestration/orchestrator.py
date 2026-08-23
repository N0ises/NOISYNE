from __future__ import annotations

from pathlib import Path
from typing import Any

from phasenox.orchestration.executor import Executor
from phasenox.orchestration.planner import Planner
from phasenox.orchestration.router import Router
from phasenox.orchestration.state import State


class Orchestrator:

    def __init__(self):

        self.planner = Planner()
        self.router = Router()
        self.executor = Executor()

    def run(self, question: str) -> State:

        state = State(question=question)

        state = self.planner.plan(state)

        state = self.router.route(state)

        state = self.executor.execute(state)

        return state

    def analyze(
        self,
        audio_path: str | Path,
        reference_path: str | Path | None = None,
        *,
        intent: str = "",
        delivery_target: str = "",
        include_reasoning: bool = False,
        include_rag: bool = False,
        include_semantic_analysis: bool = False,
        output_path: str | Path | None = None,
        **kwargs: Any,
    ) -> State:
        """
        Execute the V1 PHASENOX deterministic analysis workflow.

        This is a dedicated path that bypasses the generic question planning
        pipeline and routes directly through ``PhasenoxService``.
        """
        from phasenox.application.phasenox_service import (
            AnalysisRequest,
            PhasenoxService,
        )

        request = AnalysisRequest(
            audio_path=audio_path,
            reference_path=reference_path,
            intent=intent,
            delivery_target=delivery_target,
            include_reasoning=include_reasoning,
            include_rag=include_rag,
            include_semantic_analysis=include_semantic_analysis,
            output_path=output_path,
            **kwargs,
        )

        service = PhasenoxService()
        response = service.analyze(request)

        return State(
            question=f"analyze {audio_path}",
            audio_path=audio_path,
            reference_path=reference_path,
            analysis_request=request,
            analysis_response=response,
            report=response.report,
        )
