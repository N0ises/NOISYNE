"""Generate disposable PHASENOX Windows icon, manifest, and version resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

from PIL import Image

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def project_version(pyproject: Path) -> str:
    with pyproject.open("rb") as stream:
        value = tomllib.load(stream)["project"]["version"]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("pyproject.toml has no project version")
    return value.strip()


def numeric_version(version: str) -> tuple[int, int, int, int]:
    pieces = version.split(".")
    if not 1 <= len(pieces) <= 4 or any(not piece.isdigit() for piece in pieces):
        raise ValueError(f"Windows RC version must be numeric: {version}")
    values = tuple(int(piece) for piece in pieces)
    if any(value < 0 or value > 65535 for value in values):
        raise ValueError(f"Windows RC version component is out of range: {version}")
    return (*values, *(0 for _ in range(4 - len(values))))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_assets(repository: Path, output: Path) -> dict[str, object]:
    version = project_version(repository / "pyproject.toml")
    file_version = numeric_version(version)
    source = repository / "assets" / "brand" / "exports" / "phasenox-logo-1024x1024.png"
    if not source.is_file():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)

    icon_path = output / "PHASENOX.ico"
    with Image.open(source) as image:
        rgba = image.convert("RGBA")
        rgba.save(icon_path, format="ICO", sizes=[(size, size) for size in ICON_SIZES])

    version_path = output / "PHASENOX-version.txt"
    numeric = ", ".join(str(value) for value in file_version)
    version_path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numeric}),
    prodvers=({numeric}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('FileDescription', 'PHASENØX Desktop'),
        StringStruct('FileVersion', '{version}.0'),
        StringStruct('InternalName', 'PHASENOX'),
        StringStruct('OriginalFilename', 'PHASENOX.exe'),
        StringStruct('ProductName', 'PHASENØX'),
        StringStruct('ProductVersion', '{version}'),
        StringStruct('SpecialBuild', 'UNSIGNED RELEASE CANDIDATE')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
        newline="\n",
    )

    manifest_path = output / "PHASENOX.exe.manifest"
    manifest_path.write_text(
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity name="PHASENOX.Desktop" processorArchitecture="amd64"
                    version="1.0.0.0" type="win32"/>
  <description>PHASENØX Desktop</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security><requestedPrivileges>
      <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
    </requestedPrivileges></security>
  </trustInfo>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
    </windowsSettings>
  </application>
</assembly>
""",
        encoding="utf-8",
        newline="\n",
    )

    metadata: dict[str, object] = {
        "schema_version": 1,
        "product_name": "PHASENØX",
        "file_description": "PHASENØX Desktop",
        "internal_name": "PHASENOX",
        "original_filename": "PHASENOX.exe",
        "product_version": version,
        "file_version": ".".join(str(value) for value in file_version),
        "legal_identity": "UNRESOLVED",
        "signing_status": "UNSIGNED",
        "icon_sizes": list(ICON_SIZES),
        "source": str(source.relative_to(repository)).replace("\\", "/"),
        "source_sha256": _sha256(source),
        "outputs": {
            icon_path.name: _sha256(icon_path),
            manifest_path.name: _sha256(manifest_path),
            version_path.name: _sha256(version_path),
        },
    }
    (output / "windows-assets.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    generate_assets(options.repository.resolve(), options.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
