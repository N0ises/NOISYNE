from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

from brain.infrastructure.config.loader import get_application_root


def _patch_config_file(monkeypatch, config_file: Path):
    """Point sys.modules[brain.infrastructure.config].__file__ at a fake path."""
    module = sys.modules["brain.infrastructure.config"]
    monkeypatch.setattr(module, "__file__", str(config_file))


@pytest.fixture
def no_env_root(monkeypatch):
    monkeypatch.delenv("SOUNDBRAIN_ROOT", raising=False)


def test_source_checkout_root_resolution(no_env_root, monkeypatch):
    """A source checkout with pyproject.toml resolves to the checkout root."""
    with tempfile.TemporaryDirectory() as raw:
        checkout = Path(raw) / "repo"
        checkout.mkdir()
        (checkout / "pyproject.toml").write_text("", encoding="utf-8")
        config_file = checkout / "brain" / "infrastructure" / "config" / "__init__.py"
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
        config_file = checkout / "brain" / "infrastructure" / "config" / "__init__.py"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("", encoding="utf-8")

        _patch_config_file(monkeypatch, config_file)
        assert get_application_root() == checkout


def test_installed_wheel_root_resolution(no_env_root, monkeypatch):
    """An installed wheel under site-packages resolves to site-packages."""
    with tempfile.TemporaryDirectory() as raw:
        site_packages = Path(raw) / "venv" / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)
        config_file = (
            site_packages / "brain" / "infrastructure" / "config" / "__init__.py"
        )
        config_file.parent.mkdir(parents=True)
        config_file.write_text("", encoding="utf-8")

        # No pyproject.toml or configs dir anywhere in the parents.
        _patch_config_file(monkeypatch, config_file)
        assert get_application_root() == site_packages


def test_sounbrain_root_env_overrides(no_env_root, monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        env_root = Path(raw) / "custom_root"
        env_root.mkdir()
        monkeypatch.setenv("SOUNDBRAIN_ROOT", str(env_root))
        # Even if the module file points elsewhere, the env variable wins.
        _patch_config_file(monkeypatch, Path(raw) / "irrelevant" / "__init__.py")
        assert get_application_root() == env_root
