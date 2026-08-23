from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Plan:

    use_rag: bool = False
    use_memory: bool = False
    use_audio: bool = False
    use_vision: bool = False
    use_reasoning: bool = False
    use_tools: bool = False
    use_recommendation: bool = False
    use_report: bool = False

    selected_agents: list[str] = field(default_factory=list)
    selected_tools: list[str] = field(default_factory=list)

