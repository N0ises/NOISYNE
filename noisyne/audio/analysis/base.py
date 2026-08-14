from __future__ import annotations

from abc import ABC

import numpy as np

from noisyne.audio.io.models import AudioData


class BaseAnalyzer(ABC):
    """
    Base class for all audio analyzers.
    """

    @staticmethod
    def prepare_samples(audio: AudioData) -> np.ndarray:
        samples = np.asarray(audio.samples)

        if samples.ndim == 2:
            samples = samples.mean(axis=1)

        return samples
