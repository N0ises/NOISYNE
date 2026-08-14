from __future__ import annotations

import librosa
import numpy as np

from noisyne.audio.analysis.base import BaseAnalyzer
from noisyne.audio.io.models import AudioData


class SpectralCentroidAnalysis(BaseAnalyzer):

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = self.prepare_samples(audio).astype(np.float32)

        centroid = librosa.feature.spectral_centroid(
            y=samples,
            sr=audio.metadata.sample_rate,
        )

        return float(
            np.mean(centroid)
        )