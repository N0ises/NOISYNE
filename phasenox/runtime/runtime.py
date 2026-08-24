from __future__ import annotations

import gc
from collections.abc import Mapping
from threading import RLock
from typing import Any

import torch

from phasenox.infrastructure.config import settings

from .cache import ModelCache
from .capabilities import Capability, CapabilityRegistry, registry
from .device import DeviceManager
from .loader import ModelLoader
from .models import LoadedModelAssets, ModelSpec, freeze_options
from .repository import ModelRepository


class ModelRuntime:
    """
    Shared runtime for every AI model.
    """

    _shared: ModelRuntime | None = None
    _shared_lock = RLock()

    def __init__(
        self,
        loader: ModelLoader | None = None,
        repository: ModelRepository | None = None,
        device: torch.device | None = None,
    ) -> None:
        self.device = device or DeviceManager.detect()
        self.cache = ModelCache()
        self.loader = loader or ModelLoader(
            repository
            or ModelRepository(
                root=str(settings.runtime.model_root),
                cache_dir=str(settings.runtime.model_cache_dir),
            )
        )
        self._capabilities: CapabilityRegistry = registry
        self._model_locks: dict[ModelSpec, RLock] = {}
        self._model_locks_lock = RLock()

    @classmethod
    def shared(cls) -> ModelRuntime:
        with cls._shared_lock:
            if cls._shared is None:
                cls._shared = cls()
            return cls._shared

    @property
    def dtype(self) -> torch.dtype:
        return torch.float16 if self.device.type == "cuda" else torch.float32

    def capabilities(self) -> tuple[Capability, ...]:
        return self._capabilities.all()

    def capability(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def has_capability(self, name: str) -> bool:
        return self._capabilities.exists(name)

    def load(
        self,
        *,
        model_name: str,
        model_cls: type,
        backend: str = "transformers",
        revision: str | None = None,
        device: torch.device | None = None,
        dtype: torch.dtype | None = None,
        processor_cls: type | None = None,
        tokenizer_cls: type | None = None,
        feature_extractor_cls: type | None = None,
        trust_remote_code: bool = False,
        model_options: Mapping[str, Any] | None = None,
        tokenizer_options: Mapping[str, Any] | None = None,
        processor_options: Mapping[str, Any] | None = None,
    ) -> LoadedModelAssets:
        target_device = device or self.device
        target_dtype = dtype or self.dtype
        spec = ModelSpec(
            backend=backend,
            name=model_name,
            model_class=f"{model_cls.__module__}.{model_cls.__qualname__}",
            revision=revision,
            device=str(target_device),
            dtype=str(target_dtype),
            trust_remote_code=trust_remote_code,
            model_options=freeze_options(model_options),
            tokenizer_options=freeze_options(tokenizer_options),
            processor_options=freeze_options(processor_options),
        )
        with self._lock_for(spec):
            cached = self.cache.get(spec)
            if cached is not None:
                return cached
            assets = self.loader.load(
                spec=spec,
                model_cls=model_cls,
                processor_cls=processor_cls,
                tokenizer_cls=tokenizer_cls,
                feature_extractor_cls=feature_extractor_cls,
            )
            if hasattr(assets.model, "to") and "device_map" not in dict(spec.model_options):
                assets.model = assets.model.to(target_device, dtype=target_dtype)
            assets.device = target_device
            assets.dtype = target_dtype
            self.cache.put(spec, assets)
            return assets

    def clear_cache(self) -> None:
        for spec in self.cache.specs():
            self.unload(spec)

    def unload(self, spec: ModelSpec) -> None:
        with self._lock_for(spec):
            assets = self.cache.pop(spec)
            if assets is None:
                return
            if hasattr(assets.model, "to"):
                assets.model.to("cpu")
            assets.model = None
            assets.processor = None
            assets.tokenizer = None
            assets.feature_extractor = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def unload_model(self, model_name: str, model_cls: type, **identity: Any) -> None:
        self.unload(self._spec_for(model_name, model_cls, **identity))

    def available_models(self) -> tuple[ModelSpec, ...]:
        return self.cache.specs()

    def model_info(
        self, model_name: str | ModelSpec, model_cls: type | None = None, **identity: Any
    ):
        spec = (
            model_name
            if isinstance(model_name, ModelSpec)
            else self._spec_for(model_name, model_cls, **identity)
        )
        return self.cache.get(spec)

    def processor(
        self, model_name: str | ModelSpec, model_cls: type | None = None, **identity: Any
    ):
        assets = self.model_info(model_name, model_cls, **identity)
        return assets.processor if assets else None

    def tokenizer(
        self, model_name: str | ModelSpec, model_cls: type | None = None, **identity: Any
    ):
        assets = self.model_info(model_name, model_cls, **identity)
        return assets.tokenizer if assets else None

    def _lock_for(self, spec: ModelSpec) -> RLock:
        with self._model_locks_lock:
            return self._model_locks.setdefault(spec, RLock())

    def _spec_for(
        self, model_name: str, model_cls: type | None = None, **identity: Any
    ) -> ModelSpec:
        return ModelSpec(
            backend=identity.get("backend", "transformers"),
            name=model_name,
            model_class=(
                f"{model_cls.__module__}.{model_cls.__qualname__}"
                if model_cls
                else identity.get("model_class", "unknown")
            ),
            revision=identity.get("revision"),
            device=str(identity.get("device", self.device)),
            dtype=str(identity.get("dtype", self.dtype)),
            trust_remote_code=identity.get("trust_remote_code", False),
            model_options=freeze_options(identity.get("model_options")),
            tokenizer_options=freeze_options(identity.get("tokenizer_options")),
            processor_options=freeze_options(identity.get("processor_options")),
        )
