from __future__ import annotations

import numpy as np

from brain.audio.analysis.base import BaseAnalyzer
from brain.audio.io.models import AudioData


class DynamicRangeAnalysis(BaseAnalyzer):

    def analyze(
        self,
        audio: AudioData,
    ) -> float:

        samples = self.prepare_samples(audio).astype(np.float32)

        peak = np.max(np.abs(samples))
        rms = np.sqrt(np.mean(samples ** 2))

        # Compute crest factor as a safe fallback.
        crest = peak / rms if rms > 0.0 else 0.0
        crest_db = 20.0 * np.log10(crest) if crest > 0.0 else 0.0

        if peak <= 0.0 or rms <= 0.0:
            return 0.0

        # Block-based dynamic range: use a short-term amplitude envelope.
        sr = audio.metadata.sample_rate
        block_size = max(1, int(0.05 * sr))
        n_blocks = len(samples) // block_size

        if n_blocks < 2:
            return float(crest_db)

        blocks = samples[: n_blocks * block_size].reshape(n_blocks, block_size)
        block_rms = np.sqrt(np.mean(blocks ** 2, axis=1))

        if np.any(block_rms <= 0.0):
            return float(crest_db)

        p95 = np.percentile(block_rms, 95)
        p10 = np.percentile(block_rms, 10)

        if p10 <= 0.0 or p95 <= 0.0:
            return float(crest_db)

        return float(20.0 * np.log10(p95 / p10))
