from __future__ import annotations

import numpy as np

from phasenox.audio.analysis.base import BaseAnalyzer
from phasenox.audio.io.models import AudioData


class StereoWidthAnalysis(BaseAnalyzer):

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = np.asarray(audio.samples)

        if samples.ndim != 2 or samples.shape[1] != 2:
            return float("nan")

        left = samples[:, 0].astype(np.float32)
        right = samples[:, 1].astype(np.float32)

        mid = (left + right) * 0.5
        side = (left - right) * 0.5

        mid_energy = np.mean(mid ** 2)
        side_energy = np.mean(side ** 2)

        total = mid_energy + side_energy

        if total <= 0.0:
            return 0.0

        return float(side_energy / total)