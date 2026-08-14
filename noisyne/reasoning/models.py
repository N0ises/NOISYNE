from __future__ import annotations


from dataclasses import dataclass, field

from typing import Any



@dataclass(slots=True)
class ReasoningPrompt:
    """
    Prompt payload sent to the LLM.
    """

    system: str

    user: str




@dataclass(slots=True)
class ReasoningContext:
    """
    Complete context passed into the reasoning engine.
    """

    analysis: Any

    engineer: Any

    audio_context: Any

    question: str




@dataclass(slots=True)
class AudioFact:
    """
    Verified audio measurement.
    """

    name: str

    value: str




@dataclass(slots=True)
class EngineeringFinding:
    """
    Verified engineer issue.
    """

    title: str

    severity: str

    description: str

    recommendation: str




@dataclass(slots=True)
class ReasoningRecommendation:
    """
    Engineer-approved recommendation.
    """

    text: str




@dataclass(slots=True)
class StructuredReasoningResponse:
    """
    Structured response returned by the LLM.

    This is the internal representation.
    """

    facts: list[AudioFact] = field(
        default_factory=list
    )

    findings: list[EngineeringFinding] = field(
        default_factory=list
    )

    recommendations: list[ReasoningRecommendation] = field(
        default_factory=list
    )

    conclusion: str = ""




@dataclass(slots=True)
class ReasoningResult:
    """
    Public reasoning result used by the pipeline.
    """

    answer: str

    confidence: float

    reasoning: list[str]

    structured: StructuredReasoningResponse | None = None

    finish_reason: str | None = None