from __future__ import annotations

import librosa
import numpy as np

from phasenox.audio.io.models import AudioData

from .base import BaseAnalyzer


class PitchAnalyzer(BaseAnalyzer):
    """
    Estimates the dominant pitch using librosa.yin().
    """

    def analyze(
        self,
        audio: AudioData,
        *,
        fmin: float = 65.0,
        fmax: float = 2093.0,
    ) -> float:

        samples = self.prepare_samples(audio)

        pitches = librosa.yin(
            samples,
            fmin=fmin,
            fmax=fmax,
            sr=audio.metadata.sample_rate,
        )

        pitches = pitches[np.isfinite(pitches)]

        if len(pitches) == 0:
            return 0.0

        return float(np.median(pitches))
