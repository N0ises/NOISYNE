from __future__ import annotations

from phasenox.providers import MockProvider, ProviderService
from phasenox.providers.models import GenerateRequest, GenerateResponse


def test_mock_provider_returns_deterministic_response():
    provider = MockProvider()
    request = GenerateRequest(
        system_prompt="system text",
        user_prompt="user text",
    )
    response = provider.generate(request)

    assert isinstance(response, GenerateResponse)
    assert response.provider == "mock"
    assert response.confidence == 1.0
    assert response.finish_reason == "mock"
    assert "[MOCK:mock]" in response.text
    assert "user text" in response.text


def test_mock_provider_truncates_long_prompt():
    provider = MockProvider()
    long_prompt = "word " * 100
    request = GenerateRequest(user_prompt=long_prompt)
    response = provider.generate(request)

    assert len(response.text) < len(long_prompt) + 50


def test_provider_service_uses_mock_provider():
    service = ProviderService(provider=MockProvider())
    request = GenerateRequest(user_prompt="test")
    response = service.generate(request)

    assert response.provider == "mock"
    assert "test" in response.text


def test_provider_service_default_is_qwen():
    service = ProviderService()
    assert service.provider.name == "qwen"
