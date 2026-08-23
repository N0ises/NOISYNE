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
    "Capability": ("phasenox.runtime.capabilities", "Capability"),
    "CapabilityRegistry": ("phasenox.runtime.capabilities", "CapabilityRegistry"),
    "CapabilityStatus": ("phasenox.runtime.capabilities", "CapabilityStatus"),
    "registry": ("phasenox.runtime.capabilities", "registry"),
    "ModelCache": ("phasenox.runtime.cache", "ModelCache"),
    "DeviceManager": ("phasenox.runtime.device", "DeviceManager"),
    "ModelInfo": ("phasenox.runtime.models", "ModelInfo"),
    "ModelSpec": ("phasenox.runtime.models", "ModelSpec"),
    "ModelLoader": ("phasenox.runtime.loader", "ModelLoader"),
    "ModelRuntime": ("phasenox.runtime.runtime", "ModelRuntime"),
    "RuntimeErrorBase": ("phasenox.runtime.exceptions", "RuntimeErrorBase"),
    "ModelLoadError": ("phasenox.runtime.exceptions", "ModelLoadError"),
    "ModelNotFoundError": ("phasenox.runtime.exceptions", "ModelNotFoundError"),
    "UnsupportedBackendError": ("phasenox.runtime.exceptions", "UnsupportedBackendError"),
    "ModelRepository": ("phasenox.runtime.repository", "ModelRepository"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module 'phasenox.runtime' has no attribute {name!r}")
    module_path, attr_name = _LAZY_IMPORTS[name]
    module = __import__(module_path, fromlist=[attr_name])
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
