from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GenerateRequest:
    """Payload for a provider generation call."""

    system_prompt: str = ""
    user_prompt: str = ""
    max_tokens: int = 1024
    temperature: float = 0.2
    top_p: float = 0.9
    stop_sequences: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GenerateResponse:
    """Result of a provider generation call."""

    text: str
    provider: str
    confidence: float = 1.0
    tokens_used: int | None = None
    finish_reason: str | None = None
