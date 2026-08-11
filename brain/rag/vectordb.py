from __future__ import annotations

from chromadb import PersistentClient
from chromadb.api.types import EmbeddingFunction

from brain.infrastructure.config import get_application_root, settings


client = PersistentClient(
    path=str(
        get_application_root() / settings.chroma.path
    )
)


class QwenEmbeddingFunction(
    EmbeddingFunction
):

    @property
    def model(self):
        # Lazy import to avoid a Windows segfault when sentence_transformers
        # is loaded at module import time alongside chromadb's
        # EmbeddingFunction Protocol.
        from brain.embedding import get_embedding_model

        return get_embedding_model()

    def __call__(
        self,
        input,
    ):

        if isinstance(
            input,
            str,
        ):
            input = [input]

        embeddings = self.model.encode(
            input,
            normalize_embeddings=True,
            batch_size=64,
            show_progress_bar=False,
        )

        return embeddings.tolist()


embedding_function = (
    QwenEmbeddingFunction()
)


collection = (
    client.get_or_create_collection(
        name=settings.chroma.collection,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )
)


def get_collection():
    """Return the shared Chroma collection."""
    return collection
