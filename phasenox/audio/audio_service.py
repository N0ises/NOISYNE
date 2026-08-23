from __future__ import annotations

from pathlib import Path

from phasenox.audio.io.models import (
    AudioAttributes,
    AudioData,
    AudioMetadata,
)
from phasenox.audio.io.providers.soundfile_provider import SoundFileProvider


class AudioService:

    def __init__(self):

        self._backend = SoundFileProvider()

    def load(
        self,
        path: str | Path,
    ) -> AudioData:

        path = Path(path)

        result = self._backend.load(path)

        samples = result["samples"]
        sample_rate = result["sample_rate"]

        metadata = AudioMetadata(
            path=path,
            filename=path.name,
            extension=path.suffix.lower(),
            format=path.suffix.lower().replace(".", ""),
            codec=None,
            sample_rate=sample_rate,
            channels=1 if samples.ndim == 1 else samples.shape[1],
            duration=len(samples) / sample_rate,
            bit_depth=None,
            file_size=path.stat().st_size,
        )

        return AudioData(
            samples=samples,
            metadata=metadata,
            attributes=AudioAttributes(
                provider="soundfile",
            ),
        )