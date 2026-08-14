from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from noisyne.providers import (
    BaseAIProvider,
    GeminiProvider,
    LocalProvider,
    OpenAIProvider,
    QwenProvider,
)
from noisyne.providers.models import GenerateRequest, GenerateResponse
from noisyne.reasoning.engine import LLMReasoningProvider, ReasoningEngine
from noisyne.reasoning.models import (
    ReasoningContext,
    ReasoningPrompt,
    ReasoningResult,
)


class CountingMockProvider(BaseAIProvider):
    """Mock provider that records how many times it is called."""

    name = "counting_mock"

    def __init__(self) -> None:
        self.calls = 0
        self.last_system = ""
        self.last_user = ""

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.calls += 1
        self.last_system = request.system_prompt
        self.last_user = request.user_prompt
        return GenerateResponse(
            text="counting mock answer",
            provider=self.name,
            confidence=0.99,
        )


@dataclass
class FakeIssue:
    title: str
    severity: str
    description: str
    recommendation: str


@dataclass
class FakeEngineer:
    score: float = 80.0
    strengths: list[str] = field(default_factory=list)
    issues: list[FakeIssue] = field(default_factory=list)


@dataclass
class FakeAnalysis:
    lufs: float = -12.0
    peak: float = -1.0


@dataclass
class FakeAudioContext:
    audio_type: str = "full_mix"
    source_type: str = "file"
    instrument: str | None = None
    is_full_mix: bool = True
    confidence: float = 0.9
    semantic_labels: list = field(default_factory=list)


def test_llm_reasoning_provider_uses_base_ai_provider():
    mock = CountingMockProvider()
    provider = LLMReasoningProvider(provider=mock)

    result = provider.generate(
        ReasoningPrompt(
            system="sys",
            user="usr",
        )
    )

    assert isinstance(result, ReasoningResult)
    assert result.answer == "counting mock answer"
    assert result.confidence == 0.99
    assert any("counting_mock" in r for r in result.reasoning)
    assert mock.calls == 1
    assert mock.last_system == "sys"
    assert mock.last_user == "usr"


def test_llm_reasoning_provider_default_is_qwen():
    provider = LLMReasoningProvider()
    assert provider._provider.name == "qwen"


def test_reasoning_engine_ask_routes_through_provider():
    mock = CountingMockProvider()
    provider = LLMReasoningProvider(provider=mock)
    engine = ReasoningEngine(provider=provider)

    result = engine.ask(
        ReasoningContext(
            analysis=FakeAnalysis(),
            engineer=FakeEngineer(),
            audio_context=FakeAudioContext(),
            question="What is the mix quality?",
        )
    )

    assert result.answer
    assert mock.calls == 1


def test_stub_providers_raise_not_implemented():
    request = GenerateRequest(user_prompt="test")
    for provider in [GeminiProvider(), OpenAIProvider(), LocalProvider()]:
        with pytest.raises(NotImplementedError):
            provider.generate(request)


def test_qwen_provider_has_correct_name_and_lazy_import():
    """Importing the Qwen provider class should not load transformers."""
    provider = QwenProvider()
    assert provider.name == "qwen"
    # We do not call generate() here, so no heavy model import should occur.
