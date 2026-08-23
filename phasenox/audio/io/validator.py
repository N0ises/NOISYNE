from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from pathlib import Path


class AudioValidator(ABC):
    """
    Validates audio files before loading.
    """

    @abstractmethod
    def validate(
        self,
        path: Path,
    ) -> None:
        """
        Raises an AudioValidationError
        if validation fails.
        """
        ...