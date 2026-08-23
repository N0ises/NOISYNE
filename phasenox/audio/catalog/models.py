from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IndexedAudio:

    file_hash: str

    path: str

    modified_time: float

    embedding_model: str