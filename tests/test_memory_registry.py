from __future__ import annotations

import pytest

from phasenox.memory import MemoryRegistry


def test_registry_loads_default_bundle() -> None:
    registry = MemoryRegistry()
    bundle = registry.load_default()

    assert bundle.version == "8.0.0"
    assert registry.version(bundle) == bundle.version


def test_registry_loads_from_dict() -> None:
    registry = MemoryRegistry()
    data = {
        "version": "8.2.0",
        "user_profile": {"user_id": "u"},
        "project_profile": {"project_id": "p"},
    }
    bundle = registry.load_from_dict(data)

    assert bundle.version == "8.2.0"


def test_registry_raises_on_missing_version() -> None:
    registry = MemoryRegistry()
    data = {
        "version": "",
        "user_profile": {"user_id": "u"},
        "project_profile": {"project_id": "p"},
    }

    with pytest.raises(ValueError):
        registry.load_from_dict(data)


def test_registry_raises_on_missing_user_id() -> None:
    registry = MemoryRegistry()
    data = {
        "version": "8.0.0",
        "user_profile": {"user_id": ""},
        "project_profile": {"project_id": "p"},
    }

    with pytest.raises(ValueError):
        registry.load_from_dict(data)
