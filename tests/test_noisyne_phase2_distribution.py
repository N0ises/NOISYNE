from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tomllib
import venv
import zipfile
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _project_metadata() -> dict[str, object]:
    with PYPROJECT.open("rb") as stream:
        return tomllib.load(stream)


def _venv_executable(directory: Path, name: str) -> Path:
    scripts = directory / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return scripts / f"{name}{suffix}"


def _assert_no_private_artifacts(names: set[str], *, strip_root: bool = False) -> None:
    forbidden_directories = {
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "cache",
        "data",
        "dist",
        "outputs",
        "reports",
        "venv",
    }
    forbidden_suffixes = {
        ".aif",
        ".aiff",
        ".bin",
        ".db",
        ".env",
        ".flac",
        ".key",
        ".mp3",
        ".onnx",
        ".p12",
        ".pem",
        ".safetensors",
        ".sqlite",
        ".sqlite3",
        ".wav",
    }

    for name in names:
        parts = PurePosixPath(name).parts
        if strip_root:
            parts = parts[1:]
        assert forbidden_directories.isdisjoint(parts), name
        assert not PurePosixPath(name).name.endswith(tuple(forbidden_suffixes)), name


class TestDistributionMetadata:
    def test_project_name_is_noisyne(self) -> None:
        assert _project_metadata()["project"]["name"] == "noisyne"

    def test_python_namespace_and_package_discovery_remain_brain(self) -> None:
        metadata = _project_metadata()

        assert metadata["tool"]["setuptools"]["packages"]["find"]["include"] == ["brain*"]
        assert (ROOT / "brain" / "__init__.py").is_file()
        assert not (ROOT / "noisyne").exists()

        import brain

        assert brain.__name__ == "brain"

    def test_distribution_installs_both_cli_entry_points(self) -> None:
        scripts = _project_metadata()["project"]["scripts"]

        assert scripts == {
            "noisyne": "brain.cli:main",
            "soundbrain": "brain.cli:main",
        }


@pytest.mark.packaging
def test_built_distribution_identity_and_fresh_install(tmp_path: Path) -> None:
    metadata = _project_metadata()["project"]
    version = metadata["version"]
    artifacts = tmp_path / "dist"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--sdist",
            "--outdir",
            str(artifacts),
            str(ROOT),
        ],
        check=True,
        cwd=ROOT,
    )

    wheel = artifacts / f"noisyne-{version}-py3-none-any.whl"
    sdist = artifacts / f"noisyne-{version}.tar.gz"
    assert wheel.is_file()
    assert sdist.is_file()

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        assert "brain/__init__.py" in names
        assert {
            "brain/infrastructure/config/resources/audio.yaml",
            "brain/infrastructure/config/resources/models.yaml",
            "brain/infrastructure/config/resources/runtime.yaml",
        } <= names
        assert f"noisyne-{version}.dist-info/METADATA" in names
        assert not any(name.startswith("noisyne/") for name in names)
        _assert_no_private_artifacts(names)

    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
        assert names
        assert all(
            name == f"noisyne-{version}" or name.startswith(f"noisyne-{version}/") for name in names
        )
        _assert_no_private_artifacts(names, strip_root=True)

    installed = tmp_path / "installed"
    venv.EnvBuilder(with_pip=True).create(installed)
    python = _venv_executable(installed, "python")
    noisyne = _venv_executable(installed, "noisyne")
    soundbrain = _venv_executable(installed, "soundbrain")

    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
        check=True,
    )
    metadata_result = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import brain; from importlib.metadata import version; "
                "print(brain.__name__); print(version('noisyne'))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert metadata_result.stdout.splitlines() == ["brain", version]

    for command in (noisyne, soundbrain):
        result = subprocess.run(
            [str(command), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert "N\u00d8ISYNE" in result.stdout
