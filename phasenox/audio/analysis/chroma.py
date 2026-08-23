from __future__ import annotations

import librosa
import numpy as np

from phasenox.audio.io.models import AudioData

from .base import BaseAnalyzer


class ChromaAnalyzer(BaseAnalyzer):
    """
    Computes chroma features of an audio signal.

    Returns a chromagram with 12 pitch classes.
    """

    def analyze(
        self,
        audio: AudioData,
        *,
        hop_length: int = 512,
    ) -> np.ndarray:

        samples = self.prepare_samples(audio)

        return librosa.feature.chroma_stft(
            y=samples,
            sr=audio.metadata.sample_rate,
            hop_length=hop_length,
        )
