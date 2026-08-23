from __future__ import annotations

import pytest

from phasenox.integration import AdapterFactory, WorkflowAdapter
from phasenox.integration.ableton import AbletonAdapter
from phasenox.integration.cubase import CubaseAdapter
from phasenox.integration.flstudio import FLStudioAdapter
from phasenox.integration.reaper import ReaperAdapter
from phasenox.integration.studio_one import StudioOneAdapter

EXPECTED_ADAPTERS = {"ableton", "reaper", "cubase", "flstudio", "studio_one"}


def test_factory_lists_all_adapters():
    names = AdapterFactory.list()
    assert set(names) == EXPECTED_ADAPTERS


@pytest.mark.parametrize("name", sorted(EXPECTED_ADAPTERS))
def test_factory_get_returns_adapter(name: str):
    adapter = AdapterFactory.get(name)
    assert isinstance(adapter, WorkflowAdapter)
    assert adapter.name == name


def test_factory_get_missing_returns_none():
    assert AdapterFactory.get("protools") is None


def test_factory_default_is_ableton():
    adapter = AdapterFactory.default()
    assert isinstance(adapter, AbletonAdapter)
    assert adapter.name == "ableton"


def test_adapter_classes_have_names():
    assert AbletonAdapter.name == "ableton"
    assert ReaperAdapter.name == "reaper"
    assert CubaseAdapter.name == "cubase"
    assert FLStudioAdapter.name == "flstudio"
    assert StudioOneAdapter.name == "studio_one"
