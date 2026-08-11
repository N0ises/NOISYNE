from __future__ import annotations

from abc import ABC, abstractmethod

from brain.infrastructure.config import settings
from brain.providers.base import BaseAIProvider

from .builder import PromptBuilder
from .guards.output import OutputGuard
from .models import (
    AudioFact,
    EngineeringFinding,
    ReasoningContext,
    ReasoningPrompt,
    ReasoningRecommendation,
    ReasoningResult,
    StructuredReasoningResponse,
)
from .parser import ResponseParser


class BaseReasoningProvider(ABC):
    """Abstract contract for reasoning providers."""

    @abstractmethod
    def generate(
        self,
        prompt: ReasoningPrompt,
    ) -> ReasoningResult: ...


class LLMReasoningProvider(BaseReasoningProvider):
    """
    Reasoning provider backed by the new AI provider layer.

    This implementation depends only on ``BaseAIProvider`` and routes generation
    calls through the provider's standard ``GenerateRequest`` / ``GenerateResponse``
    contract. The default provider is the configured production provider (Qwen by
    default), which keeps the reasoning engine free of provider-specific logic.
    """

    def __init__(
        self,
        provider: BaseAIProvider | None = None,
    ) -> None:
        from brain.providers.factory import ProviderFactory
        from brain.providers.models import GenerateRequest

        self._provider = provider or ProviderFactory.default()
        self._request_cls = GenerateRequest

    def generate(
        self,
        prompt: ReasoningPrompt,
    ) -> ReasoningResult:
        request_kwargs: dict = {
            "system_prompt": prompt.system,
            "user_prompt": prompt.user,
            "temperature": settings.llm.temperature,
            "top_p": settings.llm.top_p,
        }
        if hasattr(settings.llm, "max_tokens"):
            request_kwargs["max_tokens"] = settings.llm.max_tokens

        response = self._provider.generate(self._request_cls(**request_kwargs))

        return ReasoningResult(
            answer=response.text,
            confidence=response.confidence,
            reasoning=[f"Provider: {response.provider}"],
            finish_reason=response.finish_reason,
        )


class ReasoningEngine:
    """High-level reasoning entry point."""

    def __init__(
        self,
        provider: BaseReasoningProvider | None = None,
    ) -> None:
        self._builder = PromptBuilder()
        self._provider = provider or LLMReasoningProvider()
        self._output_guard = OutputGuard()
        self._parser = ResponseParser()

    def _filter_structured(
        self,
        structured: StructuredReasoningResponse,
    ) -> StructuredReasoningResponse:
        """Apply the output guard to each text field individually."""

        def _guard(text: str) -> str:
            return self._output_guard.filter(text)

        filtered_facts = [
            AudioFact(
                name=_guard(fact.name),
                value=_guard(fact.value),
            )
            for fact in structured.facts
        ]

        filtered_findings = [
            EngineeringFinding(
                title=_guard(finding.title),
                severity=_guard(finding.severity),
                description=_guard(finding.description),
                recommendation=_guard(finding.recommendation),
            )
            for finding in structured.findings
        ]

        filtered_recommendations = [
            ReasoningRecommendation(text=_guard(item.text))
            for item in structured.recommendations
        ]

        return StructuredReasoningResponse(
            facts=filtered_facts,
            findings=filtered_findings,
            recommendations=filtered_recommendations,
            conclusion=_guard(structured.conclusion),
        )

    def ask(
        self,
        context: ReasoningContext,
    ) -> ReasoningResult:
        prompt = self._builder.build(context)
        result = self._provider.generate(prompt)

        raw_answer = result.answer
        parsed_result = self._parser.parse(raw_answer)

        confidence = result.confidence
        reasoning = [f"Raw answer: {raw_answer}"] if raw_answer else ["Raw answer: <empty>"]
        reasoning.extend(result.reasoning)

        if result.finish_reason == "length":
            confidence = max(0.0, confidence - 0.25)
            reasoning.append("Warning: LLM response was truncated (finish_reason=length).")

        if parsed_result.structured is not None:
            filtered_structured = self._filter_structured(parsed_result.structured)
            parsed_result = ReasoningResult(
                answer=self._output_guard.filter(
                    self._parser._render(filtered_structured)
                ),
                confidence=confidence,
                reasoning=reasoning,
                structured=filtered_structured,
            )
        else:
            parsed_result.confidence = confidence
            parsed_result.reasoning = reasoning

        return parsed_result
