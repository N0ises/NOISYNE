from __future__ import annotations

import librosa
import numpy as np

from brain.audio.io.models import AudioData
from brain.infrastructure.config import settings

from .base import BaseAnalyzer


class MFCCAnalyzer(BaseAnalyzer):
    """
    Computes Mel-Frequency Cepstral Coefficients (MFCC).
    """

    def analyze(
        self,
        audio: AudioData,
        *,
        n_mfcc: int | None = None,
        n_fft: int = 2048,
        hop_length: int = 512,
    ) -> np.ndarray:

        samples = self.prepare_samples(audio)

        if n_mfcc is None:
            n_mfcc = settings.audio.n_mfcc

        return librosa.feature.mfcc(
            y=samples,
            sr=audio.metadata.sample_rate,
            n_mfcc=n_mfcc,
            n_fft=n_fft,
            hop_length=hop_length,
        )
