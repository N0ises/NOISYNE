from __future__ import annotations

from pathlib import Path
from typing import Any

from .loader import MemoryLoader
from .models import MemoryBundle


class MemoryRegistry:
    """Load and validate MemoryBundle instances."""

    def __init__(self, loader: MemoryLoader | None = None) -> None:
        self._loader = loader or MemoryLoader()

    def load(self, path: str | Path) -> MemoryBundle:
        """Load a bundle from an explicit master file path."""
        bundle = self._loader.load_from_path(path)
        self._validate_or_raise(bundle)
        return bundle

    def load_default(self) -> MemoryBundle:
        """Load the default bundle from the loader's root directory."""
        bundle = self._loader.load()
        self._validate_or_raise(bundle)
        return bundle

    def load_from_dict(self, data: dict[str, Any]) -> MemoryBundle:
        """Load a bundle from an inline dictionary."""
        bundle = self._loader.load_from_dict(data)
        self._validate_or_raise(bundle)
        return bundle

    def version(self, bundle: MemoryBundle) -> str:
        return bundle.version

    def _validate_or_raise(self, bundle: MemoryBundle) -> None:
        errors: list[str] = []
        if not bundle.version:
            errors.append("version is required")
        if not bundle.user_profile.user_id:
            errors.append("user_profile.user_id is required")
        if not bundle.project_profile.project_id:
            errors.append("project_profile.project_id is required")
        if errors:
            raise ValueError(f"Invalid memory bundle: {errors}")
