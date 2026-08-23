from __future__ import annotations

from typing import Any

from phasenox.runtime import (
    Capability,
    LoadedModelAssets,
    ModelRuntime,
    ModelSpec,
)


class RuntimeService:
    """
    High-level facade over ModelRuntime.

    Application layers (Audio, RAG, LLM, API, CLI, UI)
    should depend on this service instead of accessing
    ModelRuntime directly.
    """

    def __init__(
        self,
        runtime: ModelRuntime | None = None,
    ) -> None:
        self._runtime = runtime or ModelRuntime.shared()

    @property
    def runtime(self) -> ModelRuntime:
        return self._runtime

    def load(self, **kwargs: Any) -> LoadedModelAssets:
        return self._runtime.load(**kwargs)

    def unload(
        self,
        spec: ModelSpec,
    ) -> None:
        self._runtime.unload(spec)

    def unload_model(
        self,
        model_name: str,
        model_cls: type,
        **identity: Any,
    ) -> None:
        self._runtime.unload_model(
            model_name,
            model_cls,
            **identity,
        )

    def clear_cache(self) -> None:
        self._runtime.clear_cache()

    def available_models(self) -> tuple[ModelSpec, ...]:
        return self._runtime.available_models()

    def model_info(
        self,
        model_name: str | ModelSpec,
        model_cls: type | None = None,
        **identity: Any,
    ) -> LoadedModelAssets | None:
        return self._runtime.model_info(
            model_name,
            model_cls,
            **identity,
        )

    def processor(
        self,
        model_name: str | ModelSpec,
        model_cls: type | None = None,
        **identity: Any,
    ):
        return self._runtime.processor(
            model_name,
            model_cls,
            **identity,
        )

    def tokenizer(
        self,
        model_name: str | ModelSpec,
        model_cls: type | None = None,
        **identity: Any,
    ):
        return self._runtime.tokenizer(
            model_name,
            model_cls,
            **identity,
        )

    def capabilities(self) -> tuple[Capability, ...]:
        return self._runtime.capabilities()

    def has_capability(
        self,
        name: str,
    ) -> bool:
        return self._runtime.has_capability(name)