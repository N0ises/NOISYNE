from __future__ import annotations

from phasenox.orchestration.state import State
from phasenox.pipeline import Stage
from phasenox.services.rag_service import RAGService


class RAGStage(Stage):

    def __init__(self):

        self.rag = RAGService()

    def run(
        self,
        state: State,
    ) -> State:

        result = self.rag.ask(
            state.question
        )

        state.documents = result["documents"]

        return state