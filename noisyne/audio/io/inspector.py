from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from pathlib import Path

from noisyne.audio.io.models import AudioMetadata


class AudioInspector(ABC):
    """
    Extracts metadata from an audio file.
    """

    @abstractmethod
    def inspect(
        self,
        path: Path,
    ) -> AudioMetadata:
        ...