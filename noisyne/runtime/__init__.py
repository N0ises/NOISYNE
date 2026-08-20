"""Lazy runtime package exports to keep heavy model/torch imports deferred."""

from __future__ import annotations

from typing import Any

__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CapabilityStatus",
    "DeviceManager",
    "ModelCache",
    "ModelInfo",
    "ModelLoadError",
    "ModelLoader",
    "ModelNotFoundError",
    "ModelRepository",
    "ModelRuntime",
    "ModelSpec",
    "RuntimeErrorBase",
    "UnsupportedBackendError",
    "registry",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "Capability": ("noisyne.runtime.capabilities", "Capability"),
    "CapabilityRegistry": ("noisyne.runtime.capabilities", "CapabilityRegistry"),
    "CapabilityStatus": ("noisyne.runtime.capabilities", "CapabilityStatus"),
    "registry": ("noisyne.runtime.capabilities", "registry"),
    "ModelCache": ("noisyne.runtime.cache", "ModelCache"),
    "DeviceManager": ("noisyne.runtime.device", "DeviceManager"),
    "ModelInfo": ("noisyne.runtime.models", "ModelInfo"),
    "ModelSpec": ("noisyne.runtime.models", "ModelSpec"),
    "ModelLoader": ("noisyne.runtime.loader", "ModelLoader"),
    "ModelRuntime": ("noisyne.runtime.runtime", "ModelRuntime"),
    "RuntimeErrorBase": ("noisyne.runtime.exceptions", "RuntimeErrorBase"),
    "ModelLoadError": ("noisyne.runtime.exceptions", "ModelLoadError"),
    "ModelNotFoundError": ("noisyne.runtime.exceptions", "ModelNotFoundError"),
    "UnsupportedBackendError": ("noisyne.runtime.exceptions", "UnsupportedBackendError"),
    "ModelRepository": ("noisyne.runtime.repository", "ModelRepository"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module 'noisyne.runtime' has no attribute {name!r}")
    module_path, attr_name = _LAZY_IMPORTS[name]
    module = __import__(module_path, fromlist=[attr_name])
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
