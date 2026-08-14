from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BrainResponse:

    task: str

    provider: str

    result: object