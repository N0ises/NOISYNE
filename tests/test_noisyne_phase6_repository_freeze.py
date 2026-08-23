import sys
from pathlib import Path

from phasenox.infrastructure.config.loader import get_application_root

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DOCUMENT = PROJECT_ROOT / "docs" / "NOISYNE_TECHNICAL_RENAME_FREEZE.md"


def test_final_identity_matrix_records_canonical_and_compatibility_contracts():
    text = FREEZE_DOCUMENT.read_text(encoding="utf-8")

    for expected in (
        "| Display | NØISYNE |",
        "| ASCII | NOISYNE |",
        "| Distribution | `noisyne` |",
        "| Python namespace | `phasenox` | `brain` |",
        "| CLI | `noisyne` | `soundbrain` |",
        "| Service | `NoisyneService` | `SoundBrainService` |",
        "| Application root environment | `NOISYNE_ROOT` | `SOUNDBRAIN_ROOT` |",
        "| Engine key | `noisyne` | `soundbrain` |",
        "| Persisted Chroma collection | `soundbrain` |",
    ):
        assert expected in text


def test_repository_docs_report_completed_canonical_rename():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    freeze = FREEZE_DOCUMENT.read_text(encoding="utf-8")

    assert "Repository: N0ises/NOISYNE" in readme
    assert "Repository rename: completed" in readme
    assert "Canonical origin: https://github.com/N0ises/NOISYNE.git" in readme
    assert "Repository rename: **COMPLETE**" in freeze
    assert "Canonical repository: `N0ises/NOISYNE`" in freeze
    assert "Canonical origin: `https://github.com/N0ises/NOISYNE.git`" in freeze


def test_setup_docs_do_not_require_repository_basename():
    for relative_path in ("README.md", "CONTRIBUTING.md"):
        text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "cd SoundBrain" not in text
        assert "cd NOISYNE" not in text
        assert "cd <repository-directory>" in text or relative_path == "CONTRIBUTING.md"


def test_application_root_uses_structure_in_arbitrary_repository_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("NOISYNE_ROOT", raising=False)
    monkeypatch.delenv("SOUNDBRAIN_ROOT", raising=False)

    checkout = tmp_path / "arbitrary-checkout-7f3a"
    config_file = checkout / "phasenox" / "infrastructure" / "config" / "__init__.py"
    config_file.parent.mkdir(parents=True)
    config_file.write_text("", encoding="utf-8")
    (checkout / "pyproject.toml").write_text("", encoding="utf-8")

    config_module = sys.modules["phasenox.infrastructure.config"]
    monkeypatch.setattr(config_module, "__file__", str(config_file))

    assert checkout.name not in {"SoundBrain", "NOISYNE"}
    assert get_application_root() == checkout
