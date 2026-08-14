"""NØISYNE audio engineering package.

Heavy exports are loaded lazily via ``__getattr__`` so that importing
``noisyne.audio.engineer.models`` does not pull in the rule engine at import time.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "AudioEngineer":
        from .engineer import AudioEngineer

        return AudioEngineer
    if name == "EngineerReport":
        from .report import EngineerReport

        return EngineerReport
    if name == "EngineerSelector":
        from .selector import EngineerSelector

        return EngineerSelector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return [
        "AudioEngineer",
        "EngineerReport",
        "EngineerSelector",
    ]


__all__ = [
    "AudioEngineer",
    "EngineerReport",
    "EngineerSelector",
]
