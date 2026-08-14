from __future__ import annotations

from pathlib import Path

from noisyne.audio.io import AudioIOService
from noisyne.audio.io.models import AudioData


class AudioLoader:
    """Thin wrapper around AudioIOService for backward-compatible loading.

    This loader exists so that downstream modules (e.g. reference services)
    can depend on a small `AudioLoader` abstraction while the actual IO
    implementation stays in `AudioIOService`.
    """

    def __init__(self, io_service: AudioIOService | None = None) -> None:
        self._io = io_service or AudioIOService()

    def load(self, path: str | Path) -> AudioData:
        return self._io.load(path)
