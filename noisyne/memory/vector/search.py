from __future__ import annotations

from .models import SearchResult


class VectorSearch:

    @staticmethod
    def parse(result) -> SearchResult:

        return SearchResult(
            ids=result["ids"][0],
            distances=result["distances"][0],
            metadatas=result["metadatas"][0],
            documents=result["documents"][0],
        )