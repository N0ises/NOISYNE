"""NØISYNE audio package.

Heavy exports are loaded lazily via ``__getattr__`` so that importing
submodules like ``noisyne.audio.io.models`` does not pull in torch or
transformers at import time.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "AudioPipeline":
        from .pipeline import AudioPipeline

        return AudioPipeline
    if name == "AudioMemory":
        from .memory import AudioMemory

        return AudioMemory
    if name == "AudioSearchService":
        from .search.service import AudioSearchService

        return AudioSearchService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return [
        "AudioPipeline",
        "AudioMemory",
        "AudioSearchService",
    ]


__all__ = [
    "AudioMemory",
    "AudioPipeline",
    "AudioSearchService",
]
