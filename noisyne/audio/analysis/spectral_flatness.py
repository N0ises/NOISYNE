from __future__ import annotations

import librosa
import numpy as np

from noisyne.audio.analysis.base import BaseAnalyzer
from noisyne.audio.io.models import AudioData


class SpectralFlatnessAnalysis(BaseAnalyzer):

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = self.prepare_samples(audio).astype(np.float32)

        flatness = librosa.feature.spectral_flatness(
            y=samples,
        )

        return float(
            np.mean(flatness)
        )