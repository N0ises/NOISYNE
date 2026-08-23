from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
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


@pytest.fixture
def external_tmp_path() -> Path:
    with tempfile.TemporaryDirectory(prefix="phasenox-r3-") as raw:
        yield Path(raw)


class TestDistributionMetadata:
    def test_project_name_is_phasenox(self) -> None:
        assert _project_metadata()["project"]["name"] == "phasenox"

    def test_canonical_and_compatibility_package_discovery(self) -> None:
        metadata = _project_metadata()

        assert metadata["tool"]["setuptools"]["packages"]["find"]["include"] == [
            "phasenox*",
            "brain",
        ]
        assert (ROOT / "phasenox" / "__init__.py").is_file()
        assert (ROOT / "brain" / "__init__.py").is_file()
        compatibility_sources = {
            path.relative_to(ROOT / "brain")
            for path in (ROOT / "brain").rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        assert compatibility_sources == {Path("__init__.py")}

        import brain
        import phasenox

        assert phasenox.__name__ == "phasenox"
        assert brain.__name__ == "brain"

    def test_distribution_installs_only_phasenox_cli_entry_point(self) -> None:
        scripts = _project_metadata()["project"]["scripts"]

        assert scripts == {"phasenox": "phasenox.cli:main"}


@pytest.mark.packaging
def test_built_distribution_identity_and_fresh_install(external_tmp_path: Path) -> None:
    tmp_path = external_tmp_path
    metadata = _project_metadata()["project"]
    version = metadata["version"]
    source = tmp_path / "source"
    artifacts = tmp_path / "dist"

    shutil.copytree(
        ROOT / "phasenox",
        source / "phasenox",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        ROOT / "brain",
        source / "brain",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(PYPROJECT, source / "pyproject.toml")
    shutil.copy2(ROOT / "main.py", source / "main.py")
    shutil.copy2(ROOT / "LICENSE", source / "LICENSE")
    (source / "docs").mkdir()
    shutil.copy2(ROOT / "docs" / "README_v2.md", source / "docs" / "README_v2.md")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--sdist",
            "--outdir",
            str(artifacts),
            str(source),
        ],
        check=True,
        cwd=source,
    )

    wheel = artifacts / f"phasenox-{version}-py3-none-any.whl"
    sdist = artifacts / f"phasenox-{version}.tar.gz"
    assert wheel.is_file()
    assert sdist.is_file()

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        assert "brain/__init__.py" in names
        assert {
            "phasenox/infrastructure/config/resources/audio.yaml",
            "phasenox/infrastructure/config/resources/models.yaml",
            "phasenox/infrastructure/config/resources/runtime.yaml",
        } <= names
        assert f"phasenox-{version}.dist-info/METADATA" in names
        entry_points = archive.read(f"phasenox-{version}.dist-info/entry_points.txt").decode(
            "utf-8"
        )
        assert entry_points.splitlines() == [
            "[console_scripts]",
            "phasenox = phasenox.cli:main",
        ]
        assert {name for name in names if name.startswith("brain/")} == {"brain/__init__.py"}
        assert len({name for name in names if name.startswith("phasenox/")}) > 300
        _assert_no_private_artifacts(names)

    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
        assert names
        assert all(
            name == f"phasenox-{version}" or name.startswith(f"phasenox-{version}/")
            for name in names
        )
        _assert_no_private_artifacts(names, strip_root=True)

    installed = tmp_path / "installed"
    venv.EnvBuilder(with_pip=True).create(installed)
    python = _venv_executable(installed, "python")
    phasenox = _venv_executable(installed, "phasenox")
    noisyne = _venv_executable(installed, "noisyne")
    soundbrain = _venv_executable(installed, "soundbrain")

    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
        check=True,
    )
    subprocess.run(
        [str(python), "-m", "pip", "install", "PyYAML"],
        check=True,
    )
    metadata_result = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import brain, phasenox; from importlib.metadata import version; "
                "from importlib.resources import files; from pathlib import Path; "
                "from phasenox.application import NoisyneService; "
                "from brain.application import SoundBrainService; "
                "from phasenox.infrastructure.config import get_application_root; "
                "resources = files('phasenox.infrastructure.config').joinpath('resources'); "
                "print(phasenox.__name__); print(brain.__name__); "
                "print(NoisyneService is SoundBrainService); print(version('phasenox')); "
                "print(','.join(name for name in ('audio.yaml', 'models.yaml', 'runtime.yaml') "
                "if resources.joinpath(name).is_file())); "
                "print(get_application_root() == Path(phasenox.__file__).resolve().parent.parent)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert metadata_result.stdout.splitlines() == [
        "phasenox",
        "brain",
        "True",
        version,
        "audio.yaml,models.yaml,runtime.yaml",
        "True",
    ]

    assert phasenox.is_file()
    assert not noisyne.exists()
    assert not soundbrain.exists()

    result = subprocess.run(
        [str(phasenox), "--help"],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.stdout.startswith("usage: phasenox")
    assert "PHASEN\u00d8X" in result.stdout
