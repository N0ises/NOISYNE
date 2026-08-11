from __future__ import annotations

import numpy as np

from brain.audio.analysis.base import BaseAnalyzer
from brain.audio.io.models import AudioData


class PhaseCorrelationAnalysis(BaseAnalyzer):

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = np.asarray(audio.samples)

        if samples.ndim != 2 or samples.shape[1] != 2:
            return float("nan")

        left = samples[:, 0].astype(np.float32)
        right = samples[:, 1].astype(np.float32)

        if np.std(left) == 0.0 or np.std(right) == 0.0:
            return 1.0

        correlation = np.corrcoef(
            left,
            right,
        )[0, 1]

        return float(
            np.clip(
                correlation,
                -1.0,
                1.0,
            )
        )