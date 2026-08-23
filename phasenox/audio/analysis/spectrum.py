from __future__ import annotations

import numpy as np

from phasenox.audio.io.models import AudioData

from .base import BaseAnalyzer


class SpectrumAnalyzer(BaseAnalyzer):
    """
    Computes the magnitude spectrum of an audio signal.
    """

    def analyze(
        self,
        audio: AudioData,
    ) -> np.ndarray:

        samples = self.prepare_samples(audio)

        spectrum = np.fft.rfft(samples)

        return np.abs(spectrum)
