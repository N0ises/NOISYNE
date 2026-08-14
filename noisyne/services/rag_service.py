from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from noisyne.rag.retriever import retrieve
from noisyne.rag.reranker import rerank


@dataclass(slots=True)
class SearchResult:
    text: str
    source: str
    page: int
    score: float
    rerank_score: float = 0.0


class RAGService:
    """
    Public API for the SoundBrain Retrieval-Augmented Generation subsystem.

    All higher-level modules (Executor, Audio, Vision, Recommendation,
    Reasoning, Agents...) must access RAG only through this class.

    Internal implementation can change without affecting callers.
    """

    def __init__(
        self,
        retrieve_k: int = 10,
        rerank_k: int = 5,
    ) -> None:

        self.retrieve_k = retrieve_k
        self.rerank_k = rerank_k

    # ---------------------------------------------------------
    # Low-level Search
    # ---------------------------------------------------------

    def search(
        self,
        query: str,
    ) -> list[SearchResult]:

        documents = retrieve(
            query=query,
            k=self.retrieve_k,
        )

        documents = rerank(
            query=query,
            documents=documents,
            top_k=self.rerank_k,
        )

        results: list[SearchResult] = []

        for doc in documents:

            results.append(
                SearchResult(
                    text=doc["text"],
                    source=doc.get("source", ""),
                    page=int(doc.get("page", 0)),
                    score=float(doc.get("score", 0.0)),
                    rerank_score=float(doc.get("rerank_score", 0.0)),
                )
            )

        return results

    # ---------------------------------------------------------
    # Context Builder
    # ---------------------------------------------------------

    def build_context(
        self,
        query: str,
        *,
        results: list[SearchResult] | None = None,
    ) -> str:

        if results is None:
            results = self.search(query)

        if not results:
            return ""

        blocks: list[str] = []

        for item in results:

            block = (
                f"[Source: {item.source} | Page: {item.page}]\n"
                f"{item.text}"
            )

            blocks.append(block)

        return "\n\n".join(blocks)

    # ---------------------------------------------------------
    # High-level API
    # ---------------------------------------------------------

    def ask(
        self,
        question: str,
    ) -> dict[str, Any]:

        results = self.search(question)
        context = self.build_context(question, results=results)

        return {
            "question": question,
            "context": context,
            "documents": results,
            "count": len(results),
        }