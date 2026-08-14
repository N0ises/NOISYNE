from __future__ import annotations

from typing import Any, Protocol

from .models import LoadedModelAssets, ModelSpec


class LoaderStrategy(Protocol):
    def load(
        self,
        spec: ModelSpec,
        source: str,
        model_cls: type,
        processor_cls: type | None,
        tokenizer_cls: type | None,
        feature_extractor_cls: type | None,
        local: bool,
    ) -> LoadedModelAssets: ...


class TransformersStrategy:
    """Loads Hugging Face model bundles through ``from_pretrained``."""

    def load(
        self,
        spec: ModelSpec,
        source: str,
        model_cls: type,
        processor_cls: type | None,
        tokenizer_cls: type | None,
        feature_extractor_cls: type | None,
        local: bool,
    ) -> LoadedModelAssets:
        model_options = self._options(spec.model_options, spec, local)
        asset_options = self._options((), spec, local)
        return LoadedModelAssets(
            model=model_cls.from_pretrained(source, **model_options),
            processor=self._load_asset(processor_cls, source, asset_options, spec.processor_options),
            tokenizer=self._load_asset(tokenizer_cls, source, asset_options, spec.tokenizer_options),
            feature_extractor=self._load_asset(feature_extractor_cls, source, asset_options, ()),
        )

    @staticmethod
    def _options(
        options: tuple[tuple[str, Any], ...],
        spec: ModelSpec,
        local: bool,
    ) -> dict[str, Any]:
        result = dict(options)
        result["trust_remote_code"] = spec.trust_remote_code
        if spec.revision is not None:
            result["revision"] = spec.revision
        if local:
            result["local_files_only"] = True
        return result

    def _load_asset(
        self,
        asset_cls: type | None,
        source: str,
        base: dict[str, Any],
        options: tuple[tuple[str, Any], ...],
    ) -> Any | None:
        if asset_cls is None:
            return None
        return asset_cls.from_pretrained(source, **(base | dict(options)))


class SentenceTransformersStrategy:
    """Loads sentence-transformer backends without class-name dispatch."""

    def load(
        self,
        spec: ModelSpec,
        source: str,
        model_cls: type,
        processor_cls: type | None,
        tokenizer_cls: type | None,
        feature_extractor_cls: type | None,
        local: bool,
    ) -> LoadedModelAssets:
        options = TransformersStrategy._options(spec.model_options, spec, local)
        return LoadedModelAssets(model=model_cls(source, **options))
