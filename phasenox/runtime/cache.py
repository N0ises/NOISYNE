from __future__ import annotations

from threading import RLock

from .models import LoadedModelAssets, ModelSpec


class ModelCache:
    """Thread-safe storage; Runtime owns loading coordination and lifecycle."""

    def __init__(self) -> None:
        self._models: dict[ModelSpec, LoadedModelAssets] = {}
        self._lock = RLock()

    def get(self, spec: ModelSpec) -> LoadedModelAssets | None:
        with self._lock:
            return self._models.get(spec)

    def put(self, spec: ModelSpec, assets: LoadedModelAssets) -> None:
        with self._lock:
            self._models[spec] = assets

    def pop(self, spec: ModelSpec) -> LoadedModelAssets | None:
        with self._lock:
            return self._models.pop(spec, None)

    def specs(self) -> tuple[ModelSpec, ...]:
        with self._lock:
            return tuple(self._models)

    def size(self) -> int:
        with self._lock:
            return len(self._models)
