from __future__ import annotations

import uuid

from phasenox.text.embeddings.encoder import TextEncoder
from phasenox.text.embeddings.models import TextEmbedding
from phasenox.text.memory import TextMemory


class TextPipeline:

    def __init__(
        self,
        encoder: TextEncoder | None = None,
        memory: TextMemory | None = None,
    ) -> None:

        self.encoder = encoder or TextEncoder()

        self.memory = memory or TextMemory()

    def index(
        self,
        *,
        text: str,
        text_id: str | None = None,
        metadata: dict | None = None,
        document: str | None = None,
    ) -> TextEmbedding:

        embedding = self.encoder.encode(text)

        if text_id is None:
            text_id = str(uuid.uuid4())

        self.memory.store(
            text_id=text_id,
            embedding=embedding,
            metadata=metadata or {},
            document=document or text,
        )

        return embedding

    def search(
        self,
        *,
        text: str,
        top_k: int = 5,
    ):

        embedding = self.encoder.encode(text)

        return self.memory.search(
            embedding=embedding,
            top_k=top_k,
        )