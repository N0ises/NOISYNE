"""Validate the clean Desktop Core build environment before freezing."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import re
import sys
from importlib import metadata
from pathlib import Path
from typing import Any


def canonicalize(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def locked_packages(path: Path) -> dict[str, str]:
    packages = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^ ]+) \\$", line)
        if match:
            packages[canonicalize(match.group(1))] = match.group(2)
    if not packages:
        raise ValueError(f"No locked packages in {path}")
    return packages


def validate(profile_path: Path, runtime_lock: Path, build_lock: Path) -> dict[str, Any]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    installed = {
        canonicalize(distribution.metadata["Name"]): distribution.version
        for distribution in metadata.distributions()
        if distribution.metadata.get("Name")
    }
    expected = locked_packages(runtime_lock) | locked_packages(build_lock)
    failures = []
    if platform.python_version() != profile["python"]:
        failures.append(
            f"Python version is {platform.python_version()}, expected {profile['python']}"
        )
    if platform.machine().casefold() not in {"amd64", "x86_64"} or sys.maxsize <= 2**32:
        failures.append(f"Build interpreter is not Windows x64: {platform.machine()}")
    for name, version in expected.items():
        if installed.get(name) != version:
            failures.append(
                f"Locked distribution mismatch: {name}={installed.get(name)!r}, {version=}"
            )
    forbidden = {}
    for name in profile["forbidden_distributions"]:
        normalized = canonicalize(name)
        forbidden[name] = normalized in installed
        if forbidden[name]:
            failures.append(f"Forbidden distribution is installed: {name}")
    forbidden_modules = {}
    for name in profile["forbidden_module_roots"]:
        available = importlib.util.find_spec(name) is not None
        forbidden_modules[name] = available
        if available:
            failures.append(f"Forbidden module is importable: {name}")
    result = {
        "schema_version": 1,
        "status": "PASS" if not failures else "FAIL",
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "expected_locked_packages": expected,
        "installed_packages": dict(sorted(installed.items())),
        "forbidden_distributions": forbidden,
        "forbidden_modules": forbidden_modules,
        "failures": failures,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--build-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    result = validate(options.profile, options.runtime_lock, options.build_lock)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for failure in result["failures"]:
        print(f"ERROR: {failure}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
