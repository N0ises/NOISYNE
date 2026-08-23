from __future__ import annotations

from .exceptions import ModelLoadError, UnsupportedBackendError
from .models import LoadedModelAssets, ModelSpec
from .repository import ModelRepository
from .strategies import LoaderStrategy, SentenceTransformersStrategy, TransformersStrategy


class ModelLoader:
    """
    Loads models through an injected repository and explicit backend strategy.
    """

    def __init__(
        self,
        repository: ModelRepository,
        strategies: dict[str, LoaderStrategy] | None = None,
    ) -> None:
        self.repository = repository
        self._strategies = strategies or {
            "transformers": TransformersStrategy(),
            "sentence-transformers": SentenceTransformersStrategy(),
        }

    def load(
        self,
        *,
        spec: ModelSpec,
        model_cls: type,
        processor_cls: type | None = None,
        tokenizer_cls: type | None = None,
        feature_extractor_cls: type | None = None,
    ) -> LoadedModelAssets:
        strategy = self._strategies.get(spec.backend)
        if strategy is None:
            raise UnsupportedBackendError(
                f"Unsupported model backend: {spec.backend!r}"
            )
        source, local = self.repository.resolve(spec.name)
        try:
            return strategy.load(
                spec,
                source,
                model_cls,
                processor_cls,
                tokenizer_cls,
                feature_extractor_cls,
                local,
            )
        except Exception as exc:
            raise ModelLoadError(
                f"Unable to load model '{spec.name}'."
            ) from exc
