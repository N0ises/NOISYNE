from __future__ import annotations


class RuntimeErrorBase(Exception):
    """Base runtime exception."""


class ModelLoadError(RuntimeErrorBase):
    """Raised when a model cannot be loaded."""


class UnsupportedBackendError(RuntimeErrorBase):
    """Raised when the requested backend is not supported."""


class ModelNotFoundError(RuntimeErrorBase):
    """Raised when a requested model is unavailable."""