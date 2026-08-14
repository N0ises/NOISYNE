from __future__ import annotations

import librosa
import numpy as np

from noisyne.audio.io.models import AudioData

from .base import BaseAnalyzer


class TempoAnalyzer(BaseAnalyzer):
    """
    Estimates the tempo (BPM) of an audio signal.
    """

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = self.prepare_samples(audio)

        tempo, _ = librosa.beat.beat_track(
            y=samples,
            sr=audio.metadata.sample_rate,
        )

        # librosa may return a scalar or an ndarray depending on the version.
        tempo = float(np.atleast_1d(tempo)[0])

        if tempo == 0.0:
            return 0.0

        return tempo
