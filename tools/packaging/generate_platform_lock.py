"""Generate a Windows-specific hash lock from an audited wheelhouse."""

from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from email.parser import Parser
from pathlib import Path


def canonicalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def wheel_identity(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA") and name.count("/") == 1
        ]
        if len(metadata_names) != 1:
            raise ValueError(f"Expected one distribution METADATA file in {path.name}")
        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
    name = metadata.get("Name")
    version = metadata.get("Version")
    if not name or not version:
        raise ValueError(f"Missing Name or Version metadata in {path.name}")
    return canonicalize_name(name), version


def generate_lock(wheelhouse: Path, output: Path) -> None:
    wheels = sorted(wheelhouse.glob("*.whl"), key=lambda item: item.name.casefold())
    if not wheels:
        raise ValueError(f"No wheels found in {wheelhouse}")
    entries: dict[str, tuple[str, str]] = {}
    for wheel in wheels:
        name, version = wheel_identity(wheel)
        if name in entries:
            raise ValueError(f"Duplicate distribution in wheelhouse: {name}")
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        entries[name] = (version, digest)

    lines = [
        "# Generated for CPython 3.12 / Windows x64 from audited wheels.",
        "# Regenerate only from a clean, profile-specific wheelhouse.",
        "--only-binary=:all:",
        "",
    ]
    for name in sorted(entries):
        version, digest = entries[name]
        lines.extend((f"{name}=={version} \\", f"    --hash=sha256:{digest}"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheelhouse", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    generate_lock(options.wheelhouse.resolve(), options.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
