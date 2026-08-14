"""SoundBrain audio I/O package.

Heavy exports are loaded lazily via ``__getattr__`` so that importing
``noisyne.audio.io.models`` does not pull in backend providers at import time.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "AudioIOService":
        from .service import AudioIOService
        return AudioIOService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return [
        "AudioIOService",
    ]


__all__ = [
    "AudioIOService",
]
