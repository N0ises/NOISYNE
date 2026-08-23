from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .models import EmbeddingCapability


class TextEmbeddingModel(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @property
    @abstractmethod
    def capability(self) -> EmbeddingCapability:
        ...

    @abstractmethod
    def encode(
        self,
        text: str | list[str],
    ) -> np.ndarray:
        ...