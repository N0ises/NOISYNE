from __future__ import annotations

import numpy as np

from phasenox.audio.analysis.base import BaseAnalyzer
from phasenox.audio.io.models import AudioData


class CrestFactorAnalysis(BaseAnalyzer):

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = self.prepare_samples(audio).astype(np.float32)

        peak = np.max(
            np.abs(samples)
        )

        rms = np.sqrt(
            np.mean(
                samples ** 2
            )
        )

        if rms <= 0.0:
            return 0.0

        crest = peak / rms

        return float(
            20.0 * np.log10(
                crest
            )
        )