from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class AudioMetadata:
    """
    Immutable metadata describing an audio file.
    """

    path: Path

    filename: str

    extension: str

    format: str

    codec: str | None

    sample_rate: int

    channels: int

    duration: float

    bit_depth: int | None

    file_size: int


@dataclass(slots=True)
class AudioCache:
    """
    Runtime cache for expensive computations.

    Every analysis stage stores its results here instead
    of recomputing them.
    """

    features: dict[str, Any] = field(default_factory=dict)

    embeddings: dict[str, Any] = field(default_factory=dict)

    analysis: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AudioAttributes:
    """
    Runtime information.

    This data is not part of the audio file itself.
    """

    provider: str = ""

    device: str = "cpu"

    loaded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class AudioData:
    """
    Domain representation of an audio file.

    This object is the single source of truth for the
    complete audio analysis pipeline.
    """

    samples: Any

    metadata: AudioMetadata

    cache: AudioCache = field(default_factory=AudioCache)

    attributes: AudioAttributes = field(
        default_factory=AudioAttributes,
    )