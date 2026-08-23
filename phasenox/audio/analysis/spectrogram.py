from __future__ import annotations

import librosa
import numpy as np

from phasenox.audio.io.models import AudioData

from .base import BaseAnalyzer


class SpectrogramAnalyzer(BaseAnalyzer):
    """
    Computes the magnitude spectrogram of an audio signal.
    """

    def analyze(
        self,
        audio: AudioData,
        *,
        n_fft: int = 2048,
        hop_length: int = 512,
    ) -> np.ndarray:

        samples = self.prepare_samples(audio)

        spectrogram = np.abs(
            librosa.stft(
                y=samples,
                n_fft=n_fft,
                hop_length=hop_length,
            )
        )

        return spectrogram
