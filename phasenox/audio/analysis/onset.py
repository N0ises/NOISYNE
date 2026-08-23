from __future__ import annotations

import librosa
import numpy as np

from phasenox.audio.analysis.base import BaseAnalyzer
from phasenox.audio.io.models import AudioData


class OnsetAnalysis(BaseAnalyzer):

    def analyze(
        self,
        audio: AudioData,
    ) -> list[float]:

        samples = self.prepare_samples(audio).astype(np.float32)

        onset_frames = librosa.onset.onset_detect(
            y=samples,
            sr=audio.metadata.sample_rate,
            units="frames",
        )

        onset_times = librosa.frames_to_time(
            onset_frames,
            sr=audio.metadata.sample_rate,
        )

        return onset_times.tolist()