from __future__ import annotations

from noisyne.audio.embeddings.clap import CLAPEmbedding
from noisyne.audio.embeddings.factory import EmbeddingFactory
from noisyne.audio.embeddings.models import EmbeddingCapability
from noisyne.audio.embeddings.registry import EmbeddingRegistry
from noisyne.audio.embeddings.tasks import EmbeddingTask
from noisyne.runtime import DeviceManager


def create_embedding_registry() -> EmbeddingRegistry:

    registry = EmbeddingRegistry()

    provider = CLAPEmbedding()

    registry.register(
        capability=EmbeddingCapability(
            name=provider.name,
            dimension=provider.dimension,
            tasks=frozenset(
                {
                    EmbeddingTask.SEMANTIC_SEARCH.value,
                }
            ),
            backend="transformers",
            device=str(DeviceManager.detect()),
        ),
        provider=provider,
    )

    return registry


def create_embedding_factory() -> EmbeddingFactory:

    registry = create_embedding_registry()

    return EmbeddingFactory(
        registry=registry,
    )
