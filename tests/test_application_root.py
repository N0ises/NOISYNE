from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

from phasenox.infrastructure.config.loader import get_application_root


def _patch_config_file(monkeypatch, config_file: Path):
    """Point sys.modules[phasenox.infrastructure.config].__file__ at a fake path."""
    module = sys.modules["phasenox.infrastructure.config"]
    monkeypatch.setattr(module, "__file__", str(config_file))


@pytest.fixture
def no_env_root(monkeypatch):
    monkeypatch.delenv("PHASENOX_ROOT", raising=False)
    monkeypatch.delenv("NOISYNE_ROOT", raising=False)
    monkeypatch.delenv("SOUNDBRAIN_ROOT", raising=False)


def test_phasenox_root_env_overrides(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        env_root = Path(raw) / "canonical_root"
        env_root.mkdir()
        monkeypatch.setenv("PHASENOX_ROOT", str(env_root))
        _patch_config_file(monkeypatch, Path(raw) / "irrelevant" / "__init__.py")
        assert get_application_root() == env_root


def test_phasenox_root_wins_over_noisyne_root(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        canonical_root = Path(raw) / "canonical_root"
        legacy_root = Path(raw) / "noisyne_root"
        canonical_root.mkdir()
        legacy_root.mkdir()
        monkeypatch.setenv("PHASENOX_ROOT", str(canonical_root))
        monkeypatch.setenv("NOISYNE_ROOT", str(legacy_root))

        with pytest.warns(RuntimeWarning, match="PHASENOX_ROOT.*NOISYNE_ROOT"):
            assert get_application_root() == canonical_root


def test_phasenox_root_wins_over_soundbrain_root(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        canonical_root = Path(raw) / "canonical_root"
        legacy_root = Path(raw) / "soundbrain_root"
        canonical_root.mkdir()
        legacy_root.mkdir()
        monkeypatch.setenv("PHASENOX_ROOT", str(canonical_root))
        monkeypatch.setenv("SOUNDBRAIN_ROOT", str(legacy_root))

        with pytest.warns(RuntimeWarning, match="PHASENOX_ROOT.*SOUNDBRAIN_ROOT"):
            assert get_application_root() == canonical_root


def test_phasenox_root_reports_all_conflicting_legacy_roots(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        canonical_root = Path(raw) / "canonical_root"
        noisyne_root = Path(raw) / "noisyne_root"
        soundbrain_root = Path(raw) / "soundbrain_root"
        for root in (canonical_root, noisyne_root, soundbrain_root):
            root.mkdir()
        monkeypatch.setenv("PHASENOX_ROOT", str(canonical_root))
        monkeypatch.setenv("NOISYNE_ROOT", str(noisyne_root))
        monkeypatch.setenv("SOUNDBRAIN_ROOT", str(soundbrain_root))

        with pytest.warns(RuntimeWarning) as warning_records:
            assert get_application_root() == canonical_root

        message = str(warning_records[0].message)
        assert "NOISYNE_ROOT" in message
        assert "SOUNDBRAIN_ROOT" in message


def test_empty_phasenox_root_is_unset(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        legacy_root = Path(raw) / "legacy_root"
        legacy_root.mkdir()
        monkeypatch.setenv("PHASENOX_ROOT", "")
        monkeypatch.setenv("NOISYNE_ROOT", str(legacy_root))
        assert get_application_root() == legacy_root


def test_phasenox_root_preserves_path_normalization(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        normalized_root = Path(raw) / "normalized_root"
        normalized_root.mkdir()
        configured_root = normalized_root / "nested" / ".."
        monkeypatch.setenv("PHASENOX_ROOT", str(configured_root))
        assert get_application_root() == normalized_root.resolve()


def test_noisyne_root_env_overrides(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        env_root = Path(raw) / "custom_root"
        env_root.mkdir()
        monkeypatch.setenv("NOISYNE_ROOT", str(env_root))
        # Even if the module file points elsewhere, the env variable wins.
        _patch_config_file(monkeypatch, Path(raw) / "irrelevant" / "__init__.py")
        assert get_application_root() == env_root


def test_soundbrain_root_env_legacy_fallback(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        env_root = Path(raw) / "legacy_root"
        env_root.mkdir()
        monkeypatch.setenv("SOUNDBRAIN_ROOT", str(env_root))
        _patch_config_file(monkeypatch, Path(raw) / "irrelevant" / "__init__.py")
        assert get_application_root() == env_root


def test_noisyne_root_wins_over_soundbrain_root(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        new_root = Path(raw) / "new_root"
        legacy_root = Path(raw) / "legacy_root"
        new_root.mkdir()
        legacy_root.mkdir()
        monkeypatch.setenv("NOISYNE_ROOT", str(new_root))
        monkeypatch.setenv("SOUNDBRAIN_ROOT", str(legacy_root))
        _patch_config_file(monkeypatch, Path(raw) / "irrelevant" / "__init__.py")
        assert get_application_root() == new_root


def test_source_checkout_root_resolution(no_env_root, monkeypatch):
    """A source checkout with pyproject.toml resolves to the checkout root."""
    with tempfile.TemporaryDirectory() as raw:
        checkout = Path(raw) / "repo"
        checkout.mkdir()
        (checkout / "pyproject.toml").write_text("", encoding="utf-8")
        config_file = checkout / "phasenox" / "infrastructure" / "config" / "__init__.py"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("", encoding="utf-8")

        _patch_config_file(monkeypatch, config_file)
        assert get_application_root() == checkout


def test_source_checkout_with_configs_dir(no_env_root, monkeypatch):
    """A source checkout with a configs directory also resolves to the root."""
    with tempfile.TemporaryDirectory() as raw:
        checkout = Path(raw) / "repo"
        checkout.mkdir()
        (checkout / "configs").mkdir()
        config_file = checkout / "phasenox" / "infrastructure" / "config" / "__init__.py"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("", encoding="utf-8")

        _patch_config_file(monkeypatch, config_file)
        assert get_application_root() == checkout


def test_installed_wheel_root_resolution(no_env_root, monkeypatch):
    """An installed wheel under site-packages resolves to site-packages."""
    with tempfile.TemporaryDirectory() as raw:
        site_packages = Path(raw) / "venv" / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)
        config_file = site_packages / "phasenox" / "infrastructure" / "config" / "__init__.py"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("", encoding="utf-8")

        # No pyproject.toml or configs dir anywhere in the parents.
        _patch_config_file(monkeypatch, config_file)
        assert get_application_root() == site_packages
