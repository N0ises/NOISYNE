from __future__ import annotations

from pathlib import Path

from brain.audio.io.models import AudioData, AudioMetadata
from brain.audio.io.providers.soundfile_provider import SoundFileProvider
from brain.infrastructure.config import settings


class AudioIOService:
    """
    High-level audio I/O service.

    Converts backend output into AudioData.
    """

    def __init__(self) -> None:
        self._backend = SoundFileProvider()

    def load(
        self,
        path: str | Path,
    ) -> AudioData:

        path = Path(path)

        duration = self._backend.duration(path)
        max_duration = settings.audio.max_duration_seconds
        if duration > max_duration:
            raise ValueError(
                f"Audio file duration ({duration:.2f}s) exceeds the configured "
                f"maximum of {max_duration}s: {path}"
            )

        raw = self._backend.load(path)

        samples = raw["samples"]

        metadata = AudioMetadata(
            path=path,
            filename=path.name,
            extension=path.suffix.lower(),
            format=path.suffix.lower().lstrip("."),
            codec=None,
            sample_rate=raw["sample_rate"],
            channels=1 if samples.ndim == 1 else samples.shape[1],
            duration=len(samples) / raw["sample_rate"],
            bit_depth=None,
            file_size=path.stat().st_size,
        )

        return AudioData(
            samples=samples,
            metadata=metadata,
        )

    def save(
        self,
        audio: AudioData,
        path: str | Path,
    ) -> None:

        self._backend.save(
            {
                "samples": audio.samples,
                "sample_rate": audio.metadata.sample_rate,
            },
            Path(path),
        )
