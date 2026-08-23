from __future__ import annotations

import pytest

from phasenox.knowledge import KnowledgeRegistry
from phasenox.knowledge.loader import KnowledgeLoader
from phasenox.knowledge.validator import KnowledgeValidator


def test_registry_loads_default_bundle() -> None:
    registry = KnowledgeRegistry()
    bundle = registry.load_default()

    assert bundle.version == "7.0.0"
    assert registry.version(bundle) == bundle.version


def test_registry_loads_from_dict() -> None:
    registry = KnowledgeRegistry()
    data = {
        "version": "7.2.0",
        "engineering_rules": {},
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {},
        "root_causes": {},
        "best_practices": {
            "processing_order": [],
            "max_chain_steps": 6,
        },
    }
    bundle = registry.load_from_dict(data)

    assert bundle.version == "7.2.0"


def test_registry_raises_on_invalid_bundle() -> None:
    registry = KnowledgeRegistry(
        loader=KnowledgeLoader(),
        validator=KnowledgeValidator(),
    )
    data = {
        "version": "",
        "engineering_rules": {},
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {},
        "root_causes": {},
        "best_practices": {},
    }

    with pytest.raises(ValueError):
        registry.load_from_dict(data)


def test_registry_is_valid() -> None:
    registry = KnowledgeRegistry()
    bundle = KnowledgeLoader().load()

    assert registry.is_valid(bundle)
