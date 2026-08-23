from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PromptFeatures:

    sections: list[str] = field(
        default_factory=list
    )

    include_context: bool = True

    include_engineer: bool = True

    include_analysis: bool = True