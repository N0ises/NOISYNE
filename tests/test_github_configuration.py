from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_canonical_github_configuration_targets_main() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "phasenox-ci.yml").read_text(
        encoding="utf-8"
    )
    codeowners = (PROJECT_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")

    assert workflow.count("      - main") == 2
    assert "v2-development" not in workflow
    assert "develop" not in workflow
    assert "NOISYNE" not in workflow
    assert "* @N0ises" in codeowners
