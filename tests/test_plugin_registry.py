from __future__ import annotations

from phasenox.audio.plugin.models import PluginMatch
from phasenox.audio.plugin.registry import PluginRegistry


def test_registry_loads_from_dict():
    data = {
        "plugins": [
            {"brand": "FabFilter", "name": "Pro-Q 4", "category": "eq", "formats": ["vst3"]},
        ]
    }
    registry = PluginRegistry(data)

    assert len(registry) == 1
    matches = registry.matches("eq")
    assert len(matches) == 1
    assert matches[0].brand == "FabFilter"
    assert matches[0].category == "eq"


def test_registry_filters_by_format():
    data = {
        "plugins": [
            {"brand": "A", "name": "X", "category": "eq", "formats": ["vst3"]},
            {"brand": "B", "name": "Y", "category": "eq", "formats": ["au"]},
        ]
    }
    registry = PluginRegistry(data)

    matches = registry.matches("eq", formats=["au"])
    assert len(matches) == 1
    assert matches[0].brand == "B"


def test_registry_categories():
    registry = PluginRegistry(
        {
            "plugins": [
                {"brand": "A", "name": "X", "category": "eq"},
                {"brand": "B", "name": "Y", "category": "compressor"},
            ]
        }
    )

    assert registry.categories() == ["compressor", "eq"]


def test_register_adds_match():
    registry = PluginRegistry({"plugins": []})
    registry.register(PluginMatch("FabFilter", "Pro-Q 4", category="eq"))

    assert len(registry) == 1
