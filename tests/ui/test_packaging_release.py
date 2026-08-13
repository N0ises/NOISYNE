from __future__ import annotations

import os
import sys
import tomllib
from importlib import resources
from pathlib import Path

from PIL import Image

from brain.ui.brand_resources import APPROVED_BRAND_ASSETS, brand_asset_bytes
from brain.ui.branding import default_product_metadata
from brain.ui.paths import (
    desktop_path_layout,
    initialize_user_directories,
    prepare_packaged_runtime,
)
from tools.packaging.generate_windows_assets import ICON_SIZES, generate, project_version


def test_brand_and_config_resources_resolve_outside_repository_cwd(monkeypatch, tmp_path) -> None:
    unrelated = tmp_path / "Unrelated Working Directory"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    assert all(brand_asset_bytes(filename) for filename in APPROVED_BRAND_ASSETS)
    runtime = resources.files("brain.infrastructure.config").joinpath("resources", "runtime.yaml")
    assert runtime.is_file()
    assert "lazy_load: true" in runtime.read_text(encoding="utf-8")


def test_first_run_layout_is_user_scoped_and_idempotent(tmp_path) -> None:
    root = tmp_path / "User Profile With Spaces" / "SoundBrain" / "soundbrain.desktop"
    first = initialize_user_directories(root)
    second = initialize_user_directories(root)

    assert first == second == desktop_path_layout(root)
    assert first.models == root.parent / "Models"
    assert all(path.is_dir() for path in first.writable_directories)


def test_frozen_runtime_sets_backend_root_without_changing_source_mode(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.delenv("SOUNDBRAIN_ROOT", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    root = tmp_path / "packaged-state"

    layout = prepare_packaged_runtime(root)

    assert layout is not None
    assert os.environ["SOUNDBRAIN_ROOT"] == str(root.resolve())
    assert all(path.is_dir() for path in layout.writable_directories)

    monkeypatch.delattr(sys, "frozen", raising=False)
    assert prepare_packaged_runtime(tmp_path / "source-state") is None


def test_windows_icon_and_version_metadata_are_generated_from_central_sources(tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    icon_path, version_path = generate(project_root, tmp_path)

    with Image.open(icon_path) as icon:
        assert icon.format == "ICO"
        assert set(icon.ico.sizes()) == {(size, size) for size in ICON_SIZES}

    with (project_root / "pyproject.toml").open("rb") as stream:
        expected_version = str(tomllib.load(stream)["project"]["version"])
    metadata = version_path.read_text(encoding="utf-8")
    assert project_version(project_root) == expected_version
    assert default_product_metadata().version == expected_version
    assert "NØISYNE Desktop" in metadata
    assert "NOISYNE.exe" in metadata
    assert f"ProductVersion', '{expected_version}'" in metadata


def test_spec_is_auditable_onedir_windowed_configuration() -> None:
    project_root = Path(__file__).resolve().parents[2]
    spec = (project_root / "tools" / "packaging" / "noisyne.spec").read_text(encoding="utf-8")

    assert 'name="NOISYNE"' in spec
    assert "console=False" in spec
    assert "upx=False" in spec
    assert 'copy_metadata("soundbrain")' in spec
    assert 'collect_data_files("brain.ui.resources"' in spec
    assert "Refusing to package a CUDA Torch environment" in spec
    for development_only in ('"pytest"', '"pytestqt"', '"black"', '"ruff"'):
        assert development_only in spec
