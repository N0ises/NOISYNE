from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from noisyne.audio.io.models import AudioData


class AudioProcessor(ABC):
    """
    Audio processing contract.
    """

    @abstractmethod
    def to_mono(
        self,
        audio: AudioData,
    ) -> AudioData:
        ...

    @abstractmethod
    def normalize(
        self,
        audio: AudioData,
    ) -> AudioData:
        ...

    @abstractmethod
    def resample(
        self,
        audio: AudioData,
        sample_rate: int,
    ) -> AudioData:
        ...