import json
import subprocess
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_package_metadata_and_console_scripts_are_canonical():
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["name"] == "phasenox"
    assert metadata["project"]["version"] == "1.0.0"
    assert metadata["project"]["description"].startswith("PHASENØX")
    assert metadata["project"]["scripts"] == {"phasenox": "phasenox.cli:main"}
    assert metadata["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "phasenox*",
        "brain",
    ]


def test_current_docs_present_canonical_interfaces_first():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    contributing = (PROJECT_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    for expected in (
        "Product: PHASENØX",
        "Distribution: phasenox",
        "Canonical Python package: phasenox",
        "Legacy Python package: brain (compatibility only)",
        "Canonical CLI: phasenox",
        "pip install phasenox",
        'pip install "phasenox[pdf]"',
        "PHASENOX_ROOT",
        "NOISYNE_ROOT",
        "SOUNDBRAIN_ROOT",
    ):
        assert expected in readme

    assert 'python -c "import phasenox"' in contributing
    assert "phasenox --help" in contributing
    assert "soundbrain --help" not in contributing
    assert "noisyne --help" not in contributing


def test_validation_tooling_prefers_canonical_cli_and_namespace():
    validation = (PROJECT_ROOT / "validate.ps1").read_text(encoding="utf-8")
    release_validation = (PROJECT_ROOT / "scripts" / "generate_v1_release_validation.py").read_text(
        encoding="utf-8"
    )

    assert "python -m phasenox.cli analyze" in validation
    assert '"compileall", "phasenox", "brain", "tests"' in release_validation
    assert '"-m",\n            "phasenox.cli"' in release_validation


def test_export_tool_groups_canonical_and_compatibility_packages(tmp_path):
    project = tmp_path / "arbitrary-repository-name"
    output = tmp_path / "export-output"
    canonical = project / "phasenox" / "audio" / "sample.py"
    compatibility = project / "brain" / "__init__.py"
    canonical.parent.mkdir(parents=True)
    compatibility.parent.mkdir(parents=True)
    canonical.write_text("VALUE = 'canonical'\n", encoding="utf-8")
    compatibility.write_text("LEGACY = True\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "export_project.py"),
            str(project),
            "--full",
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "VALUE = 'canonical'" in (output / "phasenox" / "audio.txt").read_text(encoding="utf-8")
    assert "LEGACY = True" in (output / "brain" / "compatibility.txt").read_text(encoding="utf-8")
    assert not (output / "brain" / "audio.txt").exists()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["product"] == "PHASENOX"
    assert manifest["distribution"] == "phasenox"
