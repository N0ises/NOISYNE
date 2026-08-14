from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from noisyne.orchestration.models import Plan


@dataclass
class State:

    # ------------------------------------------------------------------
    # User Input
    # ------------------------------------------------------------------

    question: str = ""

    # ------------------------------------------------------------------
    # V1 SoundBrain Request / Response
    # ------------------------------------------------------------------

    audio_path: str | Path | None = None
    reference_path: str | Path | None = None
    analysis_request: Any = None
    analysis_response: Any = None

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    plan: Plan = field(default_factory=Plan)

    pipeline: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Retrieved Data
    # ------------------------------------------------------------------

    documents: list = field(default_factory=list)

    context: str = ""

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    prompt: str = ""

    # ------------------------------------------------------------------
    # LLM Output
    # ------------------------------------------------------------------

    answer: str = ""

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    memory: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    audio: Any = None
    image: Any = None
    video: Any = None

    # ------------------------------------------------------------------
    # Optional Outputs
    # ------------------------------------------------------------------

    recommendation: Any = None
    report: Any = None

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    metadata: dict[str, Any] = field(default_factory=dict)
