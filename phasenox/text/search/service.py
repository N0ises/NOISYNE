from __future__ import annotations

from phasenox.text.pipeline import TextPipeline


class TextSearchService:

    def __init__(
        self,
        pipeline: TextPipeline | None = None,
    ) -> None:

        self._pipeline = pipeline or TextPipeline()

    def search(
        self,
        query: str,
        top_k: int = 5,
    ):

        return self._pipeline.search(
            text=query,
            top_k=top_k,
        )

    def index(
        self,
        *,
        text: str,
        text_id: str | None = None,
        metadata: dict | None = None,
        document: str | None = None,
    ):

        return self._pipeline.index(
            text=text,
            text_id=text_id,
            metadata=metadata,
            document=document,
        )