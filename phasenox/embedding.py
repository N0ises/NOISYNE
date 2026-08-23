from __future__ import annotations

from phasenox.infrastructure.config import settings
from phasenox.runtime import ModelRuntime


def get_embedding_model():
    """
    Lazily load the configured sentence-transformer embedding model.

    ``sentence_transformers`` is imported inside the function so that importing
    ``phasenox.embedding`` does not pull heavy dependencies at module level.
    """
    from sentence_transformers import SentenceTransformer

    assets = ModelRuntime.shared().load(
        model_name=str(settings.embedding.model_path),
        model_cls=SentenceTransformer,
        backend="sentence-transformers",
        trust_remote_code=settings.models.text_embedding.trust_remote_code,
    )
    return assets.model


__all__ = ["get_embedding_model"]
