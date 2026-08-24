from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPOSITORY / "tools/packaging/profiles/desktop-core-windows-x64.json"
RUNTIME_LOCK = REPOSITORY / "tools/packaging/requirements/desktop-core-windows-x64.lock"
SPEC_PATH = REPOSITORY / "tools/packaging/phasenox_desktop_core.spec"
INNO_PATH = REPOSITORY / "tools/packaging/installer/PHASENOX.iss"
MATRIX_PATH = REPOSITORY / "tools/packaging/clean-machine-matrix.json"


def profile() -> dict[str, object]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def test_desktop_core_canonical_identity_and_installer_contract() -> None:
    selected = profile()
    application = selected["application"]
    installer = selected["installer"]
    assert application["executable"] == "PHASENOX.exe"
    assert application["entry_module"] == "phasenox/ui/__main__.py"
    assert installer == {
        "technology": "Inno Setup",
        "tool_version": "7.1.0-x64",
        "app_id": "{A6B2A61D-05B0-4CE7-85A3-C443B36D703B}",
        "privileges": "lowest",
        "uninstall_policy": "application-only",
    }


def test_runtime_lock_is_exact_hashed_and_forbids_heavy_profiles() -> None:
    lock = RUNTIME_LOCK.read_text(encoding="utf-8")
    requirements = re.findall(r"(?m)^([A-Za-z0-9_.-]+)==([^ ;\\]+)", lock)
    assert requirements
    assert lock.count("--hash=sha256:") >= len(requirements)
    names = {name.casefold().replace("_", "-") for name, _version in requirements}
    forbidden = {name.casefold() for name in profile()["forbidden_distributions"]}
    assert names.isdisjoint(forbidden)


def test_spec_is_windowed_one_folder_and_excludes_forbidden_profiles() -> None:
    spec = SPEC_PATH.read_text(encoding="utf-8")
    assert 'name="PHASENOX"' in spec
    assert "console=False" in spec
    assert "upx=False" in spec
    assert "COLLECT(" in spec
    assert 'PROFILE["forbidden_module_roots"]' in spec


def test_inno_setup_preserves_data_root_and_removes_application_only() -> None:
    script = INNO_PATH.read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in script
    assert "UsePreviousAppDir=yes" in script
    assert "SignedUninstaller=no" in script
    assert "installer-data-root.json" in script
    assert "data-root.json" in script
    assert "SaveStringToFile(HandoffPath()" in script
    assert "SaveStringToFile(PointerPath()" not in script
    assert "[UninstallDelete]" not in script
    assert "ChangesEnvironment=no" in script


def test_version_and_brand_resource_identity_are_authoritative() -> None:
    project = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    generator = (REPOSITORY / "tools/packaging/generate_windows_assets.py").read_text(
        encoding="utf-8"
    )
    assert project["project"]["version"]
    assert "PHASENØX" in generator
    assert "OriginalFilename" in generator
    assert "PHASENOX.exe" in generator
    for fragment in ("assets", "brand", "exports", "phasenox-logo-1024x1024.png"):
        assert f'"{fragment}"' in generator


def test_clean_machine_rows_remain_external_acceptance_pending() -> None:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    assert len(matrix["rows"]) >= 18
    assert all(row["status"] == "EXTERNAL_ACCEPTANCE_PENDING" for row in matrix["rows"])
    assert all(row["result"] == "NOT_EXECUTED" for row in matrix["rows"])
    assert matrix["candidate"] == {
        "git_sha": "7123116aa0d5f48adcbaa671b91d6530db2d3a34",
        "installer_sha256": (
            "0026e42b2101f2bf404cd4f7f7ec4e65749e4f590114449e01249b26f9f00fa4"
        ),
        "executable_sha256": (
            "9caedfefeb10b5e0cb39fa8b16b301cb757d337fadb419f744d418483aa22744"
        ),
    }
    assert matrix["infrastructure_audit"]["result"] == "EXTERNAL_ACCEPTANCE_PENDING"


def test_no_legacy_product_artifact_names() -> None:
    for path in (
        PROFILE_PATH,
        SPEC_PATH,
        INNO_PATH,
        REPOSITORY / "tools/release/build_desktop_core.ps1",
    ):
        text = path.read_text(encoding="utf-8").casefold()
        assert "noisyne.exe" not in text
        assert "soundbrain.exe" not in text
        assert "noisyne-setup" not in text
        assert "soundbrain-setup" not in text


def test_clean_machine_harness_preserves_native_argument_boundaries() -> None:
    script = (REPOSITORY / "tools/release/validate_windows_install.ps1").read_text(encoding="utf-8")
    assert "ProcessStartInfo" in script
    assert "ArgumentList.Add" in script
    assert "ExpectedInstallerSha256" in script
    assert "Confirm-FirstLaunchDataRoot" in script
    assert '[string]$DataRoot = ""' in script
    assert "ValuePattern" in script
    assert "Start-Process -FilePath $Executable -ArgumentList" not in script
