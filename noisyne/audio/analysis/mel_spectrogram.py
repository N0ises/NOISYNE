from __future__ import annotations

import librosa
import numpy as np

from noisyne.audio.io.models import AudioData

from .base import BaseAnalyzer


class MelSpectrogramAnalyzer(BaseAnalyzer):
    """
    Computes the Mel Spectrogram of an audio signal.
    """

    def analyze(
        self,
        audio: AudioData,
        *,
        n_fft: int = 2048,
        hop_length: int = 512,
        n_mels: int = 128,
    ) -> np.ndarray:

        samples = self.prepare_samples(audio)

        mel = librosa.feature.melspectrogram(
            y=samples,
            sr=audio.metadata.sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
            power=2.0,
        )

        return mel
