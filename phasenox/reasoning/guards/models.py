from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ReasoningRules:

    allow_mastering: bool = True

    allow_mix_advice: bool = True

    allow_stem_advice: bool = True

    context_warning: str | None = None