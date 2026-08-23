"""Compatibility namespace for legacy :mod:`brain` imports.

The implementation lives exclusively under :mod:`phasenox`.  This package
installs a small import hook that maps every ``brain.*`` import to the matching
canonical module object, preserving class, enum, exception, registry, and
module-level state identity during the compatibility period.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from types import ModuleType

_LEGACY_PREFIX = __name__
_CANONICAL_PREFIX = "phasenox"
_FINDER_MARKER = "_phasenox_legacy_namespace_finder"
_canonical_package = importlib.import_module(_CANONICAL_PREFIX)


class _LegacyModuleLoader(importlib.abc.Loader):
    """Return an existing canonical module for a legacy module name."""

    def __init__(self, module: ModuleType) -> None:
        self.module = module
        self._metadata = {
            name: getattr(module, name, None)
            for name in ("__name__", "__loader__", "__package__", "__spec__")
        }

    def create_module(self, spec: object) -> ModuleType:
        return self.module

    def exec_module(self, module: ModuleType) -> None:
        # Import machinery temporarily applies the legacy spec to the returned
        # module. Restore canonical metadata so resources and introspection keep
        # reporting the authoritative ``phasenox.*`` module path.
        for name, value in self._metadata.items():
            setattr(module, name, value)


class _LegacyModuleFinder(importlib.abc.MetaPathFinder):
    """Resolve ``brain.*`` names to their existing ``phasenox.*`` modules."""

    _phasenox_legacy_namespace_finder = True

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        legacy_prefix = f"{_LEGACY_PREFIX}."
        if not fullname.startswith(legacy_prefix):
            return None

        canonical_name = f"{_CANONICAL_PREFIX}{fullname[len(_LEGACY_PREFIX):]}"
        module = importlib.import_module(canonical_name)
        loader = _LegacyModuleLoader(module)
        return importlib.util.spec_from_loader(
            fullname,
            loader,
            origin=getattr(getattr(module, "__spec__", None), "origin", None),
            is_package=hasattr(module, "__path__"),
        )


if not any(getattr(finder, _FINDER_MARKER, False) for finder in sys.meta_path):
    sys.meta_path.insert(0, _LegacyModuleFinder())


def __getattr__(name: str) -> object:
    """Forward root-level public attributes to the canonical package."""
    return getattr(_canonical_package, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_canonical_package)))
