from __future__ import annotations

import numpy as np

from phasenox.audio.io.models import AudioData

from .base import BaseAnalyzer


class PeakAnalyzer(BaseAnalyzer):
    """
    Computes the absolute peak amplitude of an audio signal.
    """

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = np.asarray(audio.samples)

        return float(
            np.max(
                np.abs(samples)
            )
        )
