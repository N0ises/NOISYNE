"""Generate Desktop Core release manifest, SBOM, licenses, and checksums."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^ ;]+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locked_packages(lock: Path) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in lock.read_text(encoding="utf-8").splitlines():
        match = REQUIREMENT_RE.match(raw.strip())
        if match:
            current = {"name": match.group(1), "version": match.group(2), "hashes": []}
            packages.append(current)
        if current:
            current["hashes"].extend(re.findall(r"--hash=sha256:([0-9a-f]{64})", raw))
    return packages


def metadata_for(package: dict[str, Any]) -> dict[str, Any]:
    try:
        metadata = importlib.metadata.metadata(package["name"])
    except importlib.metadata.PackageNotFoundError:
        return {**package, "license": "UNKNOWN", "license_files": []}
    expressions = metadata.get_all("License-Expression") or []
    declared = expressions[0] if expressions else (metadata.get("License") or "UNKNOWN")
    return {
        **package,
        "license": declared.strip() or "UNKNOWN",
        "license_files": metadata.get_all("License-File") or [],
        "homepage": metadata.get("Project-URL") or metadata.get("Home-page") or "",
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--bundle-verification", type=Path, required=True)
    parser.add_argument("--build-context", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--windows-assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    evidence = output / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    verification = json.loads(args.bundle_verification.read_text(encoding="utf-8"))
    context = json.loads(args.build_context.read_text(encoding="utf-8-sig"))
    packages = locked_packages(args.runtime_lock)
    version = args.bundle.name.removeprefix("PHASENOX-").removesuffix("-win-x64")

    sbom_path = evidence / "PHASENOX-desktop-core.cdx.json"
    components = [
        {
            "type": "library",
            "name": item["name"],
            "version": item["version"],
            "hashes": [{"alg": "SHA-256", "content": value} for value in item["hashes"]],
            "purl": f"pkg:pypi/{item['name']}@{item['version']}",
        }
        for item in packages
    ]
    write_json(
        sbom_path,
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "serialNumber": f"urn:uuid:{uuid.UUID(hex=hashlib.sha256(context['git_sha'].encode()).hexdigest()[:32])}",
            "version": 1,
            "metadata": {
                "component": {
                    "type": "application",
                    "name": "PHASENOX Desktop Core",
                    "version": version,
                }
            },
            "components": components,
        },
    )

    licenses_path = evidence / "PHASENOX-desktop-core-licenses.json"
    write_json(
        licenses_path,
        {
            "schema_version": 1,
            "scope": "locked Desktop Core runtime dependencies only",
            "compliance_claim": "Inventory only; legal review remains required.",
            "packages": [metadata_for(item) for item in packages],
        },
    )

    manifest_path = evidence / "PHASENOX-release-manifest.json"
    manifest = {
        "schema_version": 1,
        "identity": {"display": "PHASENØX", "ascii": "PHASENOX"},
        "profile": "desktop-core",
        "platform": "windows-x64",
        "version": version,
        "pe_version": f"{version}.0",
        "installer_version": version,
        "git": {
            "sha": context["git_sha"],
            "branch": context["branch"],
            "clean": context["tracked_worktree_clean"],
        },
        "build": {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "python": context["python"],
            "pyinstaller": importlib.metadata.version("pyinstaller"),
            "pyside6_essentials": importlib.metadata.version("PySide6-Essentials"),
            "inno_setup": context["inno_setup"],
            "signing_status": "UNSIGNED",
        },
        "installer": {
            "app_id": profile["installer"]["app_id"],
            "privileges": profile["installer"]["privileges"],
            "uninstall_policy": profile["installer"]["uninstall_policy"],
        },
        "locked_dependencies": packages,
        "bundle_verification": verification,
        "approved_resource_hashes": {
            path.name: sha256(path)
            for path in sorted(args.windows_assets.iterdir())
            if path.is_file()
        },
        "native_closure": verification.get("native", {}),
        "vc_runtime_strategy": "app-local closure; clean-machine no-runtime case remains blocked pending VM proof",
        "probe_outcomes": verification.get("launch", {}),
        "artifacts": {
            "executable": {
                "path": str(args.bundle / "PHASENOX.exe"),
                "sha256": sha256(args.bundle / "PHASENOX.exe"),
            },
            "installer": {
                "path": str(args.installer),
                "sha256": sha256(args.installer),
                "size": args.installer.stat().st_size,
            },
            "sbom": {"path": str(sbom_path), "sha256": sha256(sbom_path)},
            "licenses": {"path": str(licenses_path), "sha256": sha256(licenses_path)},
        },
    }
    write_json(manifest_path, manifest)

    sums_path = output / f"PHASENOX-{version}-win-x64-SHA256SUMS.txt"
    checksum_targets = [
        args.bundle / "PHASENOX.exe",
        args.bundle_verification,
        args.installer,
        sbom_path,
        licenses_path,
        manifest_path,
    ]
    lines = [f"{sha256(path)}  {path.name}" for path in checksum_targets]
    sums_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"Generated release evidence and {sums_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
