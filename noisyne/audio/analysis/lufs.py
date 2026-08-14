from __future__ import annotations

import numpy as np
import pyloudnorm as pyln

from noisyne.audio.io.models import AudioData

from .base import BaseAnalyzer


class LUFSAnalyzer(BaseAnalyzer):
    """
    Computes Integrated Loudness (LUFS)
    using ITU-R BS.1770.
    """

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = np.asarray(audio.samples)

        meter = pyln.Meter(
            audio.metadata.sample_rate,
        )

        try:
            loudness = meter.integrated_loudness(
                samples,
            )
        except ValueError:
            # BS.1770 requires at least one full gating block (~0.4 s).
            # Very short inputs cannot produce a valid integrated loudness.
            return float("nan")

        return float(loudness)
