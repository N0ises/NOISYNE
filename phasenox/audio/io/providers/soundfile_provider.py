from __future__ import annotations

from pathlib import Path

import soundfile as sf

from phasenox.audio.io.backend import AudioBackend


class SoundFileProvider(AudioBackend):
    """
    SoundFile backend implementation.
    """

    def load(
        self,
        path: Path,
    ):

        samples, sample_rate = sf.read(
            file=path,
            always_2d=False,
        )

        return {
            "samples": samples,
            "sample_rate": sample_rate,
        }

    def duration(self, path: Path) -> float:
        """Read stream metadata without materializing audio samples."""
        info = sf.info(path)
        if info.samplerate <= 0:
            raise ValueError(f"Audio file has an invalid sample rate: {path}")
        return float(info.frames / info.samplerate)

    def save(
        self,
        data,
        path: Path,
    ) -> None:

        sf.write(
            file=path,
            data=data["samples"],
            samplerate=data["sample_rate"],
        )
