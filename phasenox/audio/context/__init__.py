"""PHASENOX audio context package.

Heavy exports are loaded lazily via ``__getattr__`` so that importing
``phasenox.audio.context.models`` does not pull in CLAP or transformers at import time.
"""

from __future__ import annotations

from .models import AudioContext, AudioSemanticLabel
from .rules import ContextRuleEngine

__all__ = [
    "AudioContext",
    "AudioSemanticLabel",
    "ContextRuleEngine",
]


def __getattr__(name: str):
    if name == "AudioContextDetector":
        from .detector import AudioContextDetector

        return AudioContextDetector
    if name == "AudioClassifier":
        from .classifier import AudioClassifier

        return AudioClassifier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return __all__ + [
        "AudioContextDetector",
        "AudioClassifier",
    ]
