from __future__ import annotations

import numpy as np

from sentence_transformers import SentenceTransformer

from phasenox.infrastructure.config import settings
from phasenox.runtime import ModelRuntime

from .base import TextEmbeddingModel
from .models import EmbeddingCapability


class BGEEmbedding(TextEmbeddingModel):

    def __init__(self, runtime: ModelRuntime | None = None) -> None:
        self._runtime = runtime or ModelRuntime.shared()

    @property
    def _assets(self):
        model_entry = settings.models.text_embedding
        return self._runtime.load(
            model_name=model_entry.name,
            model_cls=SentenceTransformer,
            backend="sentence-transformers",
            revision=model_entry.revision,
            trust_remote_code=model_entry.trust_remote_code,
        )

    @property
    def name(self) -> str:

        return "bge-m3"

    @property
    def dimension(self) -> int:

        return 1024

    @property
    def capability(self) -> EmbeddingCapability:

        return EmbeddingCapability(
            backend="sentence-transformers",
            device=str(self._assets.device),
        )

    def encode(
        self,
        text: str | list[str],
    ) -> np.ndarray:

        model: SentenceTransformer = self._assets.model

        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return np.asarray(
            embedding,
            dtype=np.float32,
        )
