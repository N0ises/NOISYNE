from __future__ import annotations

import numpy as np

from phasenox.audio.io.models import AudioData

from .base import BaseAnalyzer


class RMSAnalyzer(BaseAnalyzer):
    """
    Computes the Root Mean Square (RMS) level of an audio signal.
    """

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = np.asarray(audio.samples)

        return float(
            np.sqrt(
                np.mean(
                    np.square(samples)
                )
            )
        )
