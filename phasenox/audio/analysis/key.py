from __future__ import annotations

import librosa
import numpy as np

from phasenox.audio.analysis.base import BaseAnalyzer
from phasenox.audio.io.models import AudioData


class KeyAnalysis(BaseAnalyzer):

    KEYS = (
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "A#",
        "B",
    )

    # Krumhansl-Kessler / Temperley-style key profiles.
    MAJOR_PROFILE = np.array(
        [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 3.22],
        dtype=np.float32,
    )
    MINOR_PROFILE = np.array(
        [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
        dtype=np.float32,
    )

    def analyze(
        self,
        audio: AudioData,
    ) -> str:

        samples = self.prepare_samples(audio).astype(np.float32)

        chroma = librosa.feature.chroma_stft(
            y=samples,
            sr=audio.metadata.sample_rate,
        )

        chroma_mean = np.mean(
            chroma,
            axis=1,
        )

        if np.sum(chroma_mean) <= 0.0:
            return "unknown"

        chroma_mean = chroma_mean / np.linalg.norm(chroma_mean)

        best_score = -1.0
        best_key = "unknown"

        for i, key in enumerate(self.KEYS):
            major_profile = np.roll(self.MAJOR_PROFILE, i)
            minor_profile = np.roll(self.MINOR_PROFILE, i)

            major_score = np.corrcoef(chroma_mean, major_profile)[0, 1]
            minor_score = np.corrcoef(chroma_mean, minor_profile)[0, 1]

            if not np.isfinite(major_score):
                major_score = -1.0
            if not np.isfinite(minor_score):
                minor_score = -1.0

            if major_score > best_score:
                best_score = major_score
                best_key = key + " major"

            if minor_score > best_score:
                best_score = minor_score
                best_key = key + " minor"

        return best_key
