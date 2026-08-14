from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class EmbeddingCapability:

    backend: str

    device: str


@dataclass(slots=True)
class TextEmbedding:

    provider: str

    vector: np.ndarray

    dimension: int