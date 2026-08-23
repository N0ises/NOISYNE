from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import torch


def freeze_options(options: Mapping[str, Any] | None) -> tuple[tuple[str, Any], ...]:
    """Create a deterministic, hashable representation of loader options."""
    if not options:
        return ()
    return tuple(sorted((name, _freeze(value)) for name, value in options.items()))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return freeze_options(value)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(item) for item in value))
    return value


@dataclass(slots=True, frozen=True)
class ModelSpec:
    """Identity and load policy for one cached model asset bundle."""

    backend: str
    name: str
    model_class: str
    revision: str | None
    device: str
    dtype: str
    trust_remote_code: bool = False
    model_options: tuple[tuple[str, Any], ...] = ()
    tokenizer_options: tuple[tuple[str, Any], ...] = ()
    processor_options: tuple[tuple[str, Any], ...] = ()


@dataclass(slots=True, frozen=True)
class ModelInfo:
    """Static metadata that is safe to inspect without loading a model."""

    name: str
    backend: str = "transformers"
    revision: str | None = None
    local_path: Path | None = None
    dtype: torch.dtype = torch.float32


@dataclass(slots=True)
class LoadedModelAssets:
    """Model and optional companion assets owned by the Runtime cache."""

    model: Any
    processor: Any | None = None
    tokenizer: Any | None = None
    feature_extractor: Any | None = None
    config: Any | None = None
    device: torch.device | None = None
    dtype: torch.dtype | None = None
