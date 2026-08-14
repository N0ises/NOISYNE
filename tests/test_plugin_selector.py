from __future__ import annotations

from noisyne.audio.plugin.registry import PluginRegistry
from noisyne.audio.plugin.selector import PluginSelector


def test_selector_returns_options_by_category():
    registry = PluginRegistry(
        {"plugins": [{"brand": "FabFilter", "name": "Pro-Q 4", "category": "eq"}]}
    )
    selector = PluginSelector(registry)

    options = selector.select("eq")

    assert len(options) == 1
    assert options[0].category == "eq"


def test_selector_respects_limit():
    registry = PluginRegistry(
        {
            "plugins": [
                {"brand": "A", "name": "X", "category": "eq"},
                {"brand": "B", "name": "Y", "category": "eq"},
            ]
        }
    )
    selector = PluginSelector(registry)

    options = selector.select("eq", limit=1)

    assert len(options) == 1


def test_selector_returns_empty_for_unknown_category():
    registry = PluginRegistry({"plugins": []})
    selector = PluginSelector(registry)

    assert selector.select("eq") == []


def test_selector_filter_formats():
    registry = PluginRegistry(
        {
            "plugins": [
                {"brand": "A", "name": "X", "category": "eq", "formats": ["vst3"]},
                {"brand": "B", "name": "Y", "category": "eq", "formats": ["au"]},
            ]
        }
    )
    selector = PluginSelector(registry)

    options = selector.select("eq", formats=["au"])

    assert len(options) == 1
    assert options[0].brand == "B"
