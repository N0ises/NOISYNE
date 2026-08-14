from __future__ import annotations

from noisyne.orchestration.state import State
from noisyne.pipeline import Stage
from noisyne.services.rag_service import RAGService


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