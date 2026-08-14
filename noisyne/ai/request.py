from __future__ import annotations

from dataclasses import dataclass

from noisyne.audio.io.models import AudioData

from .tasks import AITask


@dataclass(slots=True)
class BrainRequest:

    task: AITask

    audio: AudioData | None = None

    text: str | None = None

    image: object | None = None

    metadata: dict | None = None