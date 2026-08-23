from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Any


class AudioBackend(ABC):
    """
    Low-level audio backend.

    A backend is responsible ONLY for communicating with the
    underlying audio library.

    It never creates domain models.
    """

    @abstractmethod
    def load(
        self,
        path: Path,
    ) -> Any:
        """
        Load raw audio using the backend.

        Returns:
            Backend native object.
        """
        ...

    @abstractmethod
    def save(
        self,
        data: Any,
        path: Path,
    ) -> None:
        """
        Save backend native object.
        """
        ...