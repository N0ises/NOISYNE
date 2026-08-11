from __future__ import annotations

import logging
from typing import Any

import requests

from brain.infrastructure.config import settings

from .base import BaseAIProvider
from .models import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)


class QwenProvider(BaseAIProvider):
    """
    Production provider backed by LM Studio's local OpenAI-compatible HTTP API.

    This provider does NOT import or load transformers, torch, or HuggingFace
    models. All generation is performed through HTTP requests to a configurable
    LM Studio endpoint (default ``http://127.0.0.1:1234/v1``).

    The model name is resolved from configuration first; if the configuration
    uses the placeholder ``local-model`` name, the provider asks LM Studio for
    the loaded model via ``GET /v1/models`` and falls back to ``local-model``.
    """

    name = "qwen"

    def __init__(self) -> None:
        self._base_url = settings.llm.base_url.rstrip("/")
        self._api_key = settings.llm.api_key
        self._model_name: str | None = None

    def _resolve_model_name(self) -> str:
        """Return the model name to send to LM Studio."""
        if self._model_name is not None:
            return self._model_name

        configured = settings.llm.model
        if configured and configured != "local-model":
            self._model_name = configured
            logger.debug("Using configured LLM model name: %s", self._model_name)
            return self._model_name

        try:
            response = requests.get(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            models = data.get("data", [])
            if models and isinstance(models, list):
                self._model_name = str(models[0].get("id", "local-model"))
                logger.debug("Resolved LLM model name from LM Studio: %s", self._model_name)
                return self._model_name
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to query LM Studio /v1/models: %s", exc)

        self._model_name = "local-model"
        logger.debug("Falling back to LLM model name: %s", self._model_name)
        return self._model_name

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate a chat completion through LM Studio.

        Raises ``requests.RequestException`` when LM Studio is unreachable or
        returns an error. Callers (e.g. ``SoundBrainService``) are expected to
        catch this and degrade gracefully.
        """
        model_name = self._resolve_model_name()

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        response = requests.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("LM Studio returned no completion choices")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        answer = content.strip()
        finish_reason = choice.get("finish_reason")
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens")

        return GenerateResponse(
            text=answer.strip(),
            provider=self.name,
            confidence=1.0,
            tokens_used=tokens_used,
            finish_reason=finish_reason,
        )
