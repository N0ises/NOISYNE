from __future__ import annotations

import numpy as np
import librosa

from noisyne.audio.io.models import AudioData
from noisyne.audio.io.processor import AudioProcessor


class DefaultAudioProcessor(AudioProcessor):

    def to_mono(
        self,
        audio: AudioData,
    ) -> AudioData:

        if audio.samples.ndim == 1:
            return audio

        audio.samples = np.mean(
            audio.samples,
            axis=1,
        )

        return audio

    def normalize(
        self,
        audio: AudioData,
    ) -> AudioData:

        peak = np.max(np.abs(audio.samples))

        if peak > 0:
            audio.samples = audio.samples / peak

        return audio

    def resample(
        self,
        audio: AudioData,
        sample_rate: int,
    ) -> AudioData:

        if audio.metadata.sample_rate == sample_rate:
            return audio

        audio.samples = librosa.resample(
            audio.samples,
            orig_sr=audio.metadata.sample_rate,
            target_sr=sample_rate,
        )

        return audio