"""Fail-closed verification for a frozen PHASENOX Desktop Core bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import pefile

SECRET_PATTERNS = {
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(rb"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{36,255}"),
    "openai_token": re.compile(rb"(?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_-]{40,}"),
    "private_key": re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/]{32,}"
    ),
}
TEXT_SCAN_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
MODEL_SUFFIXES = {
    ".ckpt",
    ".engine",
    ".gguf",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
    ".tflite",
}
DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
FORBIDDEN_PATH_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "audits",
    "checkpoints",
    "docs",
    "logs",
    "models",
    "reports",
    "roadmaps",
    "tests",
    "venv",
    "weights",
}
ALLOWED_BUILD_WARNINGS = {
    'Hidden import "pycparser.lextab" not found!',
    'Hidden import "pycparser.yacctab" not found!',
    'Hidden import "scipy.special._cdflib" not found!',
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def load_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("profile") != "desktop-core" or profile.get("architecture") != "x64":
        raise ValueError("Verifier requires the desktop-core/windows-x64 profile")
    return profile


def pe_version_metadata(path: Path) -> dict[str, str]:
    pe = pefile.PE(str(path), fast_load=False)
    values: dict[str, str] = {}
    for group in getattr(pe, "FileInfo", ()):
        for entry in group:
            if getattr(entry, "Key", b"") != b"StringFileInfo":
                continue
            for table in entry.StringTable:
                for key, value in table.entries.items():
                    decoded_key = (
                        key.decode(errors="replace") if isinstance(key, bytes) else str(key)
                    )
                    decoded_value = (
                        value.decode(errors="replace") if isinstance(value, bytes) else str(value)
                    )
                    values[decoded_key] = decoded_value
    resource_ids = {entry.id for entry in getattr(pe, "DIRECTORY_ENTRY_RESOURCE", ()).entries}
    values["IconResourcePresent"] = str(3 in resource_ids)
    values["ManifestResourcePresent"] = str(24 in resource_ids)
    return values


def native_inventory(files: list[Path], bundle: Path) -> dict[str, Any]:
    pe_files = [path for path in files if path.suffix.casefold() in {".dll", ".exe", ".pyd"}]
    bundled_names = {path.name.casefold() for path in pe_files}
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    records = []
    unresolved: set[str] = set()
    app_local: set[str] = set()
    system: set[str] = set()
    parse_errors: list[str] = []
    for path in pe_files:
        try:
            pe = pefile.PE(str(path), fast_load=True)
            pe.parse_data_directories(
                directories=[
                    pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                    pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
                ]
            )
            imports = sorted(
                {
                    entry.dll.decode(errors="replace")
                    for attribute in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT")
                    for entry in getattr(pe, attribute, ())
                },
                key=str.casefold,
            )
        except pefile.PEFormatError as exc:
            parse_errors.append(f"{relative(path, bundle)}: {type(exc).__name__}")
            continue
        classifications = {}
        for imported in imports:
            folded = imported.casefold()
            if folded in bundled_names:
                classifications[imported] = "app_local"
                app_local.add(imported)
            elif (system32 / imported).is_file() or folded.startswith(("api-ms-win-", "ext-ms-")):
                classifications[imported] = "windows_system"
                system.add(imported)
            else:
                classifications[imported] = "unresolved"
                unresolved.add(imported)
        records.append({"path": relative(path, bundle), "imports": classifications})
    return {
        "tool": f"pefile {pefile.__version__}",
        "pe_file_count": len(pe_files),
        "app_local_imports": sorted(app_local, key=str.casefold),
        "windows_system_imports": sorted(system, key=str.casefold),
        "unresolved_imports": sorted(unresolved, key=str.casefold),
        "parse_errors": parse_errors,
        "files": records,
    }


def verify_build_warnings(path: Path | None) -> list[str]:
    if path is None:
        return []
    unexpected = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        marker = " WARNING: "
        if marker not in line:
            continue
        message = line.split(marker, 1)[1].strip()
        if message not in ALLOWED_BUILD_WARNINGS:
            unexpected.append(message)
    return unexpected


def scan_bundle(
    bundle: Path,
    profile: dict[str, Any],
    *,
    repository: Path | None,
    user_home: Path | None,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    top_level = sorted(path.name for path in bundle.iterdir())
    if top_level != ["PHASENOX.exe", "_internal"]:
        failures.append(f"Unexpected top-level payload: {top_level}")
    files = sorted((path for path in bundle.rglob("*") if path.is_file()), key=str)
    paths = {relative(path, bundle) for path in files}
    required = {
        "PHASENOX.exe",
        "_internal/python312.dll",
        "_internal/PySide6/plugins/platforms/qwindows.dll",
    }
    required.update(
        f"_internal/phasenox/infrastructure/config/resources/{name}"
        for name in profile["config_resources"]
    )
    required.update(
        f"_internal/phasenox/resources/branding/{name}" for name in profile["branding_resources"]
    )
    missing = sorted(required - paths)
    if missing:
        failures.append(f"Missing required payload: {missing}")

    brand_prefix = "_internal/phasenox/resources/branding/"
    actual_brand = {
        value.removeprefix(brand_prefix)
        for value in paths
        if value.startswith(brand_prefix) and value != brand_prefix + "__init__.py"
    }
    expected_brand = set(profile["branding_resources"])
    if actual_brand != expected_brand:
        failures.append(
            f"Runtime branding differs from profile: missing={sorted(expected_brand-actual_brand)}, "
            f"extra={sorted(actual_brand-expected_brand)}"
        )

    plugin_marker = "_internal/PySide6/plugins/"
    actual_plugins = {
        value.removeprefix(plugin_marker) for value in paths if value.startswith(plugin_marker)
    }
    expected_plugins = set(profile["qt_plugins"])
    if actual_plugins != expected_plugins:
        failures.append(
            f"Qt plugins differ from profile: missing={sorted(expected_plugins-actual_plugins)}, "
            f"extra={sorted(actual_plugins-expected_plugins)}"
        )

    forbidden_roots = tuple(f"/{name.casefold()}/" for name in profile["forbidden_module_roots"])
    sensitive_needles = []
    for candidate in (repository, user_home):
        if candidate is None:
            continue
        raw = str(candidate.resolve())
        sensitive_needles.extend(
            (raw.encode("utf-8"), raw.replace("\\", "/").encode("utf-8"), raw.encode("utf-16le"))
        )

    secret_hits: Counter[str] = Counter()
    for path in files:
        item = "/" + relative(path, bundle).replace("\\", "/").casefold()
        parts = set(Path(item).parts)
        if any(root in item for root in forbidden_roots):
            failures.append(f"Forbidden module payload: {relative(path, bundle)}")
        if FORBIDDEN_PATH_PARTS.intersection(parts):
            failures.append(f"Forbidden path category: {relative(path, bundle)}")
        if path.suffix.casefold() in MODEL_SUFFIXES | DATABASE_SUFFIXES:
            failures.append(f"Forbidden model/database file: {relative(path, bundle)}")
        if path.suffix.casefold() == ".zip" and path.name != "base_library.zip":
            failures.append(f"Unexpected nested archive: {relative(path, bundle)}")
        if path.name.casefold() in {".env", "index.db"}:
            failures.append(f"Forbidden state/secret filename: {relative(path, bundle)}")
        if any(pattern.casefold() in path.name.casefold() for pattern in ("noisyne", "soundbrain")):
            failures.append(f"Legacy product-facing artifact name: {relative(path, bundle)}")
        raw = path.read_bytes()
        if any(needle and needle in raw for needle in sensitive_needles):
            failures.append(f"Local absolute path serialized in: {relative(path, bundle)}")
        if path.suffix.casefold() in TEXT_SCAN_SUFFIXES:
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(raw):
                    secret_hits[name] += 1
                    failures.append(f"Potential {name} in: {relative(path, bundle)}")

    total_size = sum(path.stat().st_size for path in files)
    if total_size > int(profile["size_budget_bytes"]):
        failures.append(f"Bundle exceeds {profile['size_budget_bytes']} byte budget: {total_size}")
    largest = [
        {"path": relative(path, bundle), "bytes": path.stat().st_size}
        for path in sorted(files, key=lambda item: item.stat().st_size, reverse=True)[:25]
    ]
    footprints = {}
    for name, marker in {
        "qt": "/pyside6/",
        "numpy": "/numpy",
        "scipy": "/scipy",
        "librosa_numba_llvmlite": ("/librosa", "/numba", "/llvmlite"),
    }.items():
        markers = (marker,) if isinstance(marker, str) else marker
        footprints[name] = sum(
            path.stat().st_size
            for path in files
            if any(value in ("/" + relative(path, bundle).casefold()) for value in markers)
        )
    inventory = [
        {"path": relative(path, bundle), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ]
    native = native_inventory(files, bundle)
    if native["unresolved_imports"]:
        failures.append(f"Unresolved native imports: {native['unresolved_imports']}")
    if native["parse_errors"]:
        failures.append(f"Native PE parse failures: {native['parse_errors']}")
    report = {
        "schema_version": 1,
        "profile": "desktop-core",
        "bundle": bundle.name,
        "file_count": len(files),
        "aggregate_bytes": total_size,
        "largest_files": largest,
        "footprints": footprints,
        "pe_metadata": pe_version_metadata(bundle / "PHASENOX.exe"),
        "native": native,
        "secret_hit_counts": dict(secret_hits),
        "files": inventory,
    }
    return failures, report


def launch_probe(bundle: Path) -> tuple[list[str], dict[str, Any]]:
    failures = []
    before = {relative(path, bundle): sha256(path) for path in bundle.rglob("*") if path.is_file()}
    with tempfile.TemporaryDirectory(prefix="phasenox-desktop-core-probe-") as raw:
        temporary = Path(raw)
        local_appdata = temporary / "Local AppData"
        data_root = temporary / "PHASENOX Data"
        cwd = temporary / "arbitrary cwd"
        probe = temporary / "packaging-probe.json"
        data_root.mkdir(parents=True)
        cwd.mkdir()
        environment = os.environ.copy()
        environment.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HOME": str(temporary / "forbidden-hf-home"),
                "LOCALAPPDATA": str(local_appdata),
                "NO_PROXY": "*",
                "PHASENOX_DESKTOP_CORE": "1",
            }
        )
        completed = subprocess.run(
            [
                str(bundle / "PHASENOX.exe"),
                "--data-root",
                str(data_root),
                "--packaging-probe",
                str(probe),
            ],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            failures.append(
                f"Frozen launch probe failed ({completed.returncode}); stderr length="
                f"{len(completed.stderr)}"
            )
            probe_data: dict[str, Any] = {}
        elif not probe.is_file():
            failures.append("Frozen launch probe produced no result")
            probe_data = {}
        else:
            probe_data = json.loads(probe.read_text(encoding="utf-8"))
        if (temporary / "forbidden-hf-home").exists():
            failures.append("Frozen launch created a model cache while offline")
        pointer = local_appdata / "PHASENOX" / "phasenox.desktop" / "state" / "data-root.json"
        if not pointer.is_file():
            failures.append("Frozen launch did not create canonical Data Root pointer")
        unexpected_state = [
            str(path.relative_to(temporary))
            for path in temporary.rglob("soundbrain.desktop")
            if path.exists()
        ]
        if unexpected_state:
            failures.append(f"Frozen launch created legacy Desktop state: {unexpected_state}")
        launch = {
            "returncode": completed.returncode,
            "stderr_length": len(completed.stderr),
            "probe": probe_data,
            "canonical_pointer": pointer.is_file(),
            "arbitrary_cwd": True,
            "offline_environment": True,
            "model_cache_created": (temporary / "forbidden-hf-home").exists(),
        }
    after = {relative(path, bundle): sha256(path) for path in bundle.rglob("*") if path.is_file()}
    if before != after:
        failures.append("Frozen launch mutated the application bundle")
    launch["bundle_unchanged_after_launch"] = before == after
    return failures, launch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--pyinstaller-log", type=Path)
    parser.add_argument("--skip-launch", action="store_true")
    options = parser.parse_args()
    bundle = options.bundle.resolve()
    profile = load_profile(options.profile.resolve())
    failures, report = scan_bundle(
        bundle,
        profile,
        repository=options.repository,
        user_home=Path.home(),
    )
    unexpected_warnings = verify_build_warnings(options.pyinstaller_log)
    if unexpected_warnings:
        failures.append(f"Unexpected PyInstaller warnings: {unexpected_warnings}")
    report["pyinstaller_unexpected_warnings"] = unexpected_warnings
    if options.skip_launch:
        report["launch"] = {"status": "NOT_EXECUTED"}
    else:
        launch_failures, launch = launch_probe(bundle)
        failures.extend(launch_failures)
        report["launch"] = launch
    report["status"] = "PASS" if not failures else "FAIL"
    report["failures"] = failures
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print(
        f"Verified {report['file_count']} files / {report['aggregate_bytes']} bytes: "
        f"{bundle.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
