"""Generate deterministic Windows icon and version inputs for PyInstaller."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

from PIL import Image

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def project_version(project_root: Path) -> str:
    with (project_root / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def _numeric_version(version: str) -> tuple[int, int, int, int]:
    numeric = []
    for part in version.split("."):
        digits = "".join(character for character in part if character.isdigit())
        numeric.append(int(digits or 0))
        if len(numeric) == 4:
            break
    return tuple((*numeric, 0, 0, 0, 0)[:4])


def generate_icon(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        rgba = image.convert("RGBA")
        if rgba.width < 256 or rgba.height < 256:
            raise ValueError("The approved icon source must be at least 256x256 pixels.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        rgba.save(destination, format="ICO", sizes=[(size, size) for size in ICON_SIZES])


def generate_version_file(version: str, destination: Path) -> None:
    numeric = _numeric_version(version)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric},
    prodvers={numeric},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'NOISYNE'),
         StringStruct('FileDescription', 'NØISYNE Desktop'),
         StringStruct('FileVersion', '{version}'),
         StringStruct('InternalName', 'soundbrain-desktop'),
         StringStruct('OriginalFilename', 'NOISYNE.exe'),
         StringStruct('ProductName', 'NØISYNE'),
         StringStruct('ProductVersion', '{version}')]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)\n""",
        encoding="utf-8",
    )


def generate(project_root: Path, output_directory: Path) -> tuple[Path, Path]:
    icon = output_directory / "NOISYNE.ico"
    version_file = output_directory / "NOISYNE-version.txt"
    source = (
        project_root
        / "brain"
        / "ui"
        / "resources"
        / "brand"
        / "noisyne"
        / "noisyne-app-icon-256.png"
    )
    generate_icon(source, icon)
    generate_version_file(project_version(project_root), version_file)
    return icon, version_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    icon, version_file = generate(options.project_root.resolve(), options.output.resolve())
    print(icon)
    print(version_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
