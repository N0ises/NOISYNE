from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from noisyne.infrastructure.config import settings
from noisyne.runtime import ModelRuntime
from noisyne.text.embeddings.base import TextEmbeddingModel


class SentenceTransformerEmbedding(TextEmbeddingModel):

    MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

    def __init__(self, runtime: ModelRuntime | None = None) -> None:
        self._runtime = runtime or ModelRuntime.shared()

    @property
    def _model(self) -> SentenceTransformer:
        return self._runtime.load(
            model_name=self.MODEL_NAME,
            model_cls=SentenceTransformer,
            backend="sentence-transformers",
            trust_remote_code=settings.models.text_embedding.trust_remote_code,
        ).model

    @property
    def name(self) -> str:
        return "sentence-transformer"

    @property
    def dimension(self) -> int:
        return 1024

    def encode(
        self,
        text: str | list[str],
    ) -> np.ndarray:

        embedding = self._model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return embedding
