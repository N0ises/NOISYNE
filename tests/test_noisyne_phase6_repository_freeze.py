import sys
from pathlib import Path

from phasenox.infrastructure.config.loader import get_application_root

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DOCUMENT = PROJECT_ROOT / "docs" / "NOISYNE_TECHNICAL_RENAME_FREEZE.md"
CURRENT_FREEZE_DOCUMENT = PROJECT_ROOT / "docs" / "PHASENOX_TECHNICAL_IDENTITY_FREEZE.md"

CURRENT_REPOSITORY_DOCUMENTS = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "docs" / "ARCHITECTURE_v2.md",
    PROJECT_ROOT / "docs" / "CAPABILITY_REGISTRY.md",
    PROJECT_ROOT / "docs" / "DECISIONS_v2.md",
    PROJECT_ROOT / "docs" / "EXECUTION_PLAN_v2.md",
    PROJECT_ROOT / "docs" / "MODULE_MAP.md",
    CURRENT_FREEZE_DOCUMENT,
    PROJECT_ROOT / "docs" / "ROADMAP_v2.md",
)


def test_final_identity_matrix_records_canonical_and_compatibility_contracts():
    text = FREEZE_DOCUMENT.read_text(encoding="utf-8")

    for expected in (
        "| Display | NØISYNE |",
        "| ASCII | NOISYNE |",
        "| Distribution | `phasenox` |",
        "| Python namespace | `phasenox` | `brain` |",
        "| CLI | `phasenox` | — |",
        "| Service | `PhasenoxService` | `NoisyneService`, `SoundBrainService` |",
        "| Application root environment | `PHASENOX_ROOT` | `NOISYNE_ROOT`, `SOUNDBRAIN_ROOT` |",
        "| Engine key | `noisyne` | `soundbrain` |",
        "| Persisted Chroma collection | `soundbrain` |",
    ):
        assert expected in text


def test_repository_docs_report_completed_canonical_rename():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    freeze = CURRENT_FREEZE_DOCUMENT.read_text(encoding="utf-8")

    assert "Repository: N0ises/PHASENOX" in readme
    assert "Repository rename: completed" in readme
    assert "Canonical origin: https://github.com/N0ises/PHASENOX.git" in readme
    assert "| Repository identity | `N0ises/PHASENOX` |" in freeze


def test_current_repository_documents_have_no_stale_repository_identity():
    for path in CURRENT_REPOSITORY_DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        assert "N0ises/NOISYNE" not in text, path
        assert "github.com/N0ises/NOISYNE" not in text, path
        assert "N0ises/PHASENOX" in text, path


def test_setup_docs_do_not_require_repository_basename():
    for relative_path in ("README.md", "CONTRIBUTING.md"):
        text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "cd SoundBrain" not in text
        assert "cd NOISYNE" not in text
        assert "cd <repository-directory>" in text or relative_path == "CONTRIBUTING.md"

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "git clone https://github.com/N0ises/PHASENOX.git <repository-directory>" in readme


def test_application_root_uses_structure_in_arbitrary_repository_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("PHASENOX_ROOT", raising=False)
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
