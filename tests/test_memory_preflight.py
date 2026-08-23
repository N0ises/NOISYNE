from __future__ import annotations

from pathlib import Path

import pytest

from phasenox.infrastructure.config import get_application_root
from phasenox.memory import MemoryLoader
from phasenox.memory.errors import MemoryConfigurationError


def test_loader_root_is_absolute_and_application_relative():
    loader = MemoryLoader()
    assert loader._root.is_absolute()
    assert loader._root.is_relative_to(get_application_root())


def test_loader_default_bundle_still_works():
    """Normal configuration that exists loads as before."""
    bundle = MemoryLoader().load()
    assert bundle.version == "8.0.0"
    assert bundle.user_profile.user_id == "default"
    assert bundle.project_profile.project_id == "default"


def test_missing_referenced_section_raises_structured_error(tmp_path: Path):
    master = tmp_path / "memory_bundle.yaml"
    master.write_text(
        "version: '8.0.0'\n"
        "user_profile: missing_user_profile.yaml\n"
        "project_profile: missing_project_profile.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(MemoryConfigurationError) as exc_info:
        MemoryLoader(root=tmp_path).load_from_path(master)

    err = exc_info.value
    assert err.reason == "missing"
    assert err.path is not None
    assert "missing_user_profile.yaml" in str(err.path)
    assert "user_profile" in err.message


def test_missing_master_bundle_raises_structured_error(tmp_path: Path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(MemoryConfigurationError) as exc_info:
        MemoryLoader(root=tmp_path).load_from_path(missing)

    err = exc_info.value
    assert err.reason == "missing"
    assert err.path == missing


def test_invalid_yaml_bundle_raises_structured_error(tmp_path: Path):
    master = tmp_path / "memory_bundle.yaml"
    master.write_text("user_profile: [not: valid", encoding="utf-8")

    with pytest.raises(MemoryConfigurationError) as exc_info:
        MemoryLoader(root=tmp_path).load_from_path(master)

    err = exc_info.value
    assert err.reason == "invalid"


def test_non_dict_bundle_raises_structured_error(tmp_path: Path):
    master = tmp_path / "memory_bundle.yaml"
    master.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(MemoryConfigurationError) as exc_info:
        MemoryLoader(root=tmp_path).load_from_path(master)

    err = exc_info.value
    assert err.reason == "invalid"


def test_intentionally_empty_inline_profile_is_allowed():
    """An inline {} section is an intentionally empty profile, not a failure."""
    bundle = MemoryLoader().load_from_dict(
        {
            "version": "8.0.0",
            "user_profile": {},
            "project_profile": {},
        }
    )
    assert bundle.user_profile.user_id == "default"
    assert bundle.project_profile.project_id == "default"
