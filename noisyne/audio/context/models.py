from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AudioSemanticLabel:

    name: str

    confidence: float



@dataclass(slots=True)
class AudioContext:

    audio_type: str

    source_type: str


    detected_elements: list[str] = field(
        default_factory=list
    )


    # Only for stem / isolated audio
    instrument: str | None = None


    # CLAP semantic understanding
    semantic_labels: list[AudioSemanticLabel] = field(
        default_factory=list
    )


    is_full_mix: bool = False


    confidence: float = 0.0


    notes: list[str] = field(
        default_factory=list
    )