from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet

import numpy as np


@dataclass(slots=True, frozen=True)
class AudioEmbedding:

    model: str

    vector: np.ndarray


@dataclass(slots=True, frozen=True)
class EmbeddingCapability:

    name: str

    dimension: int

    tasks: FrozenSet[str]

    backend: str

    device: str