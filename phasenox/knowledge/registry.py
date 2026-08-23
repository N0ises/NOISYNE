from __future__ import annotations

from pathlib import Path
from typing import Any

from .loader import KnowledgeLoader
from .models import KnowledgeBundle
from .validator import KnowledgeValidator


class KnowledgeRegistry:
    """
    Load and validate KnowledgeBundle instances.

    This is the canonical entry point for reading knowledge files. Validation
    errors are raised immediately so that bad knowledge cannot reach the
    resolver.
    """

    def __init__(
        self,
        loader: KnowledgeLoader | None = None,
        validator: KnowledgeValidator | None = None,
    ) -> None:
        self._loader = loader or KnowledgeLoader()
        self._validator = validator or KnowledgeValidator()

    def load(self, path: str | Path) -> KnowledgeBundle:
        """Load a bundle from an explicit master file path."""
        bundle = self._loader.load_from_path(path)
        self._validate_or_raise(bundle)
        return bundle

    def load_default(self) -> KnowledgeBundle:
        """Load the default bundle from the loader's root directory."""
        bundle = self._loader.load()
        self._validate_or_raise(bundle)
        return bundle

    def load_from_dict(self, data: dict[str, Any]) -> KnowledgeBundle:
        """Load a bundle from an inline dictionary."""
        bundle = self._loader.load_from_dict(data)
        self._validate_or_raise(bundle)
        return bundle

    def is_valid(self, bundle: KnowledgeBundle) -> bool:
        return self._validator.is_valid(bundle)

    def version(self, bundle: KnowledgeBundle) -> str:
        return bundle.version

    def _validate_or_raise(self, bundle: KnowledgeBundle) -> None:
        errors = self._validator.validate(bundle)
        if errors:
            raise ValueError(f"Invalid knowledge bundle: {errors}")
