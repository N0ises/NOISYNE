from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from brain.application.soundbrain_service import (
    AnalysisRequest,
    SoundBrainService,
)


AUDIO_PATH = Path("tests/assets/test.wav")


@dataclass
class FakeReasoningResult:
    answer: str = "This is a fake LLM summary."
    confidence: float = 1.0
    reasoning: list[str] = field(default_factory=list)


class FakeReasoningEngine:
    def ask(self, context):
        return FakeReasoningResult()


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_reasoning_wires_llm_answer_into_report(
    monkeypatch,
):
    """When reasoning succeeds, the report ai_summary uses the LLM answer."""
    monkeypatch.setattr(
        "brain.reasoning.engine.ReasoningEngine",
        FakeReasoningEngine,
    )

    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        intent="mastering check",
        include_reasoning=True,
    )

    service = SoundBrainService()
    response = service.analyze(request)

    assert response.report is not None
    assert response.report.ai_summary == "This is a fake LLM summary."


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_reasoning_fails_gracefully(monkeypatch):
    """When reasoning raises, the deterministic report is still returned."""

    class BrokenReasoningEngine:
        def ask(self, context):
            raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        "brain.reasoning.engine.ReasoningEngine",
        BrokenReasoningEngine,
    )

    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        include_reasoning=True,
    )

    service = SoundBrainService()
    response = service.analyze(request)

    assert response.report is not None
    assert response.analysis is not None
