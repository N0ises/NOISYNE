from __future__ import annotations

import builtins
import sys
from unittest import mock

import pytest

from phasenox.providers import QwenProvider
from phasenox.providers.models import GenerateRequest, GenerateResponse


@pytest.fixture
def lmstudio_config():
    """Patch LLM settings to a predictable LM Studio endpoint and model."""
    with mock.patch("phasenox.providers.qwen.settings") as settings:
        settings.llm.base_url = "http://127.0.0.1:1234/v1"
        settings.llm.api_key = "lm-studio"
        settings.llm.model = "local-model"
        yield settings


def test_qwen_provider_returns_lmstudio_completion(lmstudio_config):
    """Successful generation should call LM Studio and return the answer."""
    provider = QwenProvider()

    with mock.patch("phasenox.providers.qwen.requests") as mock_requests:
        mock_requests.get.return_value.json.return_value = {"data": [{"id": "qwen2.5-7b-instruct"}]}
        mock_requests.get.return_value.raise_for_status = mock.Mock()
        mock_requests.post.return_value.json.return_value = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "  Turn down the highs.  "},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 42},
        }
        mock_requests.post.return_value.raise_for_status = mock.Mock()

        response = provider.generate(
            GenerateRequest(
                system_prompt="You are an expert audio engineer.",
                user_prompt="How does this mix sound?",
                max_tokens=256,
                temperature=0.3,
                top_p=0.95,
            )
        )

    assert isinstance(response, GenerateResponse)
    assert response.text == "Turn down the highs."
    assert response.provider == "qwen"
    assert response.tokens_used == 42
    assert response.finish_reason == "stop"
    assert response.confidence == 1.0

    mock_requests.get.assert_called_once()
    assert mock_requests.get.call_args[0][0] == "http://127.0.0.1:1234/v1/models"

    mock_requests.post.assert_called_once()
    assert mock_requests.post.call_args.args[0] == "http://127.0.0.1:1234/v1/chat/completions"
    payload = mock_requests.post.call_args.kwargs["json"]
    assert payload["model"] == "qwen2.5-7b-instruct"
    assert payload["max_tokens"] == 256
    assert payload["temperature"] == 0.3
    assert payload["top_p"] == 0.95
    assert payload["messages"] == [
        {"role": "system", "content": "You are an expert audio engineer."},
        {"role": "user", "content": "How does this mix sound?"},
    ]


def test_qwen_provider_uses_configured_model_name(lmstudio_config):
    """If a concrete model name is configured, skip the /v1/models query."""
    lmstudio_config.llm.model = "my-custom-qwen"
    provider = QwenProvider()

    with mock.patch("phasenox.providers.qwen.requests") as mock_requests:
        mock_requests.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 1},
        }
        mock_requests.post.return_value.raise_for_status = mock.Mock()

        response = provider.generate(GenerateRequest(user_prompt="test"))

    assert response.text == "OK"
    mock_requests.get.assert_not_called()
    mock_requests.post.assert_called_once()
    assert mock_requests.post.call_args.kwargs["json"]["model"] == "my-custom-qwen"


def test_qwen_provider_falls_back_when_model_list_unreachable(lmstudio_config):
    """If /v1/models fails, the provider should fall back to 'local-model'."""
    provider = QwenProvider()

    with mock.patch("phasenox.providers.qwen.requests") as mock_requests:
        mock_requests.get.side_effect = ConnectionError("LM Studio is offline")
        mock_requests.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Fallback"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 2},
        }
        mock_requests.post.return_value.raise_for_status = mock.Mock()

        response = provider.generate(GenerateRequest(user_prompt="test"))

    assert response.text == "Fallback"
    assert mock_requests.post.call_args.kwargs["json"]["model"] == "local-model"


def test_qwen_provider_gracefully_fails_when_lmstudio_unreachable(lmstudio_config):
    """A network failure during chat/completions should surface as a request exception."""
    provider = QwenProvider()

    with mock.patch("phasenox.providers.qwen.requests") as mock_requests:
        mock_requests.get.return_value.json.return_value = {"data": [{"id": "qwen2.5-7b-instruct"}]}
        mock_requests.get.return_value.raise_for_status = mock.Mock()
        mock_requests.post.side_effect = ConnectionError("LM Studio not running")

        with pytest.raises(ConnectionError):
            provider.generate(GenerateRequest(user_prompt="test"))


def test_qwen_provider_module_does_not_import_transformers():
    """Importing and constructing QwenProvider must not load transformers or torch."""
    original_import = builtins.__import__
    blocked = {"transformers", "torch"}

    def blocking_import(name, *args, **kwargs):
        if name in blocked or name.startswith(("transformers.", "torch.")):
            raise AssertionError(
                f"QwenProvider must not import {name}; use LM Studio HTTP API instead"
            )
        return original_import(name, *args, **kwargs)

    sys.modules.pop("phasenox.providers.qwen", None)
    builtins.__import__ = blocking_import
    try:
        import phasenox.providers.qwen as qwen_module

        provider = qwen_module.QwenProvider()
        assert provider.name == "qwen"
    finally:
        builtins.__import__ = original_import
