from __future__ import annotations

import pytest

from noisyne.providers import (
    BaseAIProvider,
    GeminiProvider,
    LocalProvider,
    MockProvider,
    OpenAIProvider,
    ProviderFactory,
    ProviderRegistry,
    QwenProvider,
)

EXPECTED_PROVIDERS = {"mock", "qwen", "gemini", "openai", "local"}


def test_factory_lists_all_default_providers():
    names = ProviderFactory.list()
    assert set(names) == EXPECTED_PROVIDERS


@pytest.mark.parametrize("name", sorted(EXPECTED_PROVIDERS))
def test_factory_get_returns_provider(name: str):
    provider = ProviderFactory.get(name)
    assert isinstance(provider, BaseAIProvider)
    assert provider.name == name


def test_factory_get_missing_raises():
    with pytest.raises(LookupError):
        ProviderFactory.get("unknown")


def test_factory_default_is_qwen():
    provider = ProviderFactory.default()
    assert isinstance(provider, QwenProvider)
    assert provider.name == "qwen"


def test_registry_register_and_get():
    registry = ProviderRegistry()
    registry.register(MockProvider())
    registry.register(QwenProvider())

    assert registry.list() == ["mock", "qwen"]
    assert registry.get("mock").name == "mock"
    assert registry.exists("qwen")
    assert not registry.exists("gemini")


def test_provider_names_are_class_attributes():
    assert MockProvider.name == "mock"
    assert QwenProvider.name == "qwen"
    assert GeminiProvider.name == "gemini"
    assert OpenAIProvider.name == "openai"
    assert LocalProvider.name == "local"
