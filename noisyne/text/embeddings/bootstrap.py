from __future__ import annotations

from .factory import EmbeddingFactory
from .registry import EmbeddingRegistry
from .bge import BGEEmbedding


def create_embedding_registry() -> EmbeddingRegistry:

    registry = EmbeddingRegistry()

    registry.register(
        BGEEmbedding,
    )

    return registry


def create_embedding_factory() -> EmbeddingFactory:

    registry = create_embedding_registry()

    return EmbeddingFactory(
        registry=registry,
    )