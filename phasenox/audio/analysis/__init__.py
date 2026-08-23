"""NØISYNE audio analysis package.

Heavy exports are loaded lazily via ``__getattr__`` so that importing
``phasenox.audio.analysis.models`` does not pull in the full analyzer at import time.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "AudioAnalyzer":
        from .analyzer import AudioAnalyzer

        return AudioAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return [
        "AudioAnalyzer",
    ]


__all__ = [
    "AudioAnalyzer",
]
