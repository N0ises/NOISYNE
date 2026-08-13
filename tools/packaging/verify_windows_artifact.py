"""Inspect and smoke-test a produced NØISYNE Windows one-folder bundle."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import tempfile
from pathlib import Path

BRAND_ASSETS = (
    "noisyne-app-icon-256.png",
    "noisyne-master.svg",
    "noisyne-master-light.svg",
    "noisyne-symbol.svg",
    "noisyne-symbol-dark.svg",
)
FORBIDDEN_NAMES = {".env", "pytest", "pytestqt", "black", "ruff", "tests"}


def _required_path(bundle: Path, *relative_parts: str) -> Path:
    candidate = bundle.joinpath(*relative_parts)
    if not candidate.exists():
        raise FileNotFoundError(f"Required packaged artifact is missing: {candidate}")
    return candidate


def verify_layout(bundle: Path) -> dict[str, object]:
    executable = _required_path(bundle, "NOISYNE.exe")
    internal = _required_path(bundle, "_internal")
    _required_path(internal, "PySide6", "plugins", "platforms", "qwindows.dll")
    _required_path(internal, "PySide6", "plugins", "imageformats", "qsvg.dll")
    _required_path(internal, "brain", "infrastructure", "config", "resources", "runtime.yaml")
    brand_root = _required_path(internal, "brain", "ui", "resources", "brand", "noisyne")
    for filename in BRAND_ASSETS:
        _required_path(brand_root, filename)

    forbidden = sorted(
        str(path.relative_to(bundle))
        for path in bundle.rglob("*")
        if path.name.casefold() in FORBIDDEN_NAMES
        or path.suffix.casefold() in {".key", ".p12", ".pfx"}
    )
    if forbidden:
        raise RuntimeError(f"Forbidden files were packaged: {forbidden}")
    return {"executable": str(executable), "forbidden_files": forbidden}


def windows_metadata(executable: Path, expected_version: str) -> dict[str, str]:
    script = (
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
        "$version=(Get-Item -LiteralPath $env:NOISYNE_VERIFY_EXE).VersionInfo; "
        "$version | Select-Object ProductName,FileDescription,CompanyName,"
        "FileVersion,ProductVersion,OriginalFilename | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "NOISYNE_VERIFY_EXE": str(executable)},
    )
    metadata = json.loads(completed.stdout.strip())
    expected = {
        "ProductName": "NØISYNE",
        "FileDescription": "NØISYNE Desktop",
        "CompanyName": "NOISYNE",
        "FileVersion": expected_version,
        "ProductVersion": expected_version,
        "OriginalFilename": "NOISYNE.exe",
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            raise RuntimeError(
                f"Unexpected Windows metadata {field}: {metadata.get(field)!r}; expected {value!r}."
            )
    return metadata


def has_windows_icon(executable: Path) -> bool:
    if os.name != "nt":
        return False
    load_library = ctypes.windll.kernel32.LoadLibraryExW
    load_library.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint]
    load_library.restype = ctypes.c_void_p
    module = load_library(str(executable), None, 0x00000002)
    if not module:
        raise OSError(f"Could not inspect Windows resources in {executable}.")
    count = 0
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )

    def found(_module, _resource_type, _name, _parameter):
        nonlocal count
        count += 1
        return True

    callback = callback_type(found)
    enumerate_names = ctypes.windll.kernel32.EnumResourceNamesW
    enumerate_names.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        callback_type,
        ctypes.c_void_p,
    ]
    enumerate_names.restype = ctypes.c_int
    free_library = ctypes.windll.kernel32.FreeLibrary
    free_library.argtypes = [ctypes.c_void_p]
    free_library.restype = ctypes.c_int
    try:
        enumerated = enumerate_names(module, ctypes.c_void_p(14), callback, None)
        if not enumerated and count == 0:
            raise RuntimeError("NOISYNE.exe has no Windows group-icon resource.")
    finally:
        free_library(module)
    return count > 0


def run_smoke(bundle: Path, working_directory: Path) -> dict[str, object]:
    executable = bundle / "NOISYNE.exe"
    probe_path = working_directory / "packaging-probe.json"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("VIRTUAL_ENV", None)
    completed = subprocess.run(
        [str(executable), "--packaging-probe", str(probe_path)],
        cwd=working_directory,
        env=environment,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Packaged smoke test exited {completed.returncode}.")
    if not probe_path.is_file():
        raise RuntimeError("Packaged smoke test did not produce its result file.")
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if not probe.get("frozen") or not probe.get("user_data_outside_install"):
        raise RuntimeError(f"Packaged runtime truth check failed: {probe}")
    return probe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--skip-smoke", action="store_true")
    options = parser.parse_args()
    bundle = options.bundle.resolve()
    result = {"layout": verify_layout(bundle)}
    executable = bundle / "NOISYNE.exe"
    result["windows_metadata"] = windows_metadata(executable, options.expected_version)
    result["windows_icon"] = has_windows_icon(executable)
    if not options.skip_smoke:
        with tempfile.TemporaryDirectory(prefix="NOISYNE package verification ") as directory:
            result["smoke"] = run_smoke(bundle, Path(directory))
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if options.output:
        options.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        options.output.resolve().write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
