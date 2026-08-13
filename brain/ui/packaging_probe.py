"""Runtime checks used by the Windows packaging walking skeleton."""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
from importlib import resources
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import QLibraryInfo

from .brand_resources import APPROVED_BRAND_ASSETS, brand_asset_bytes
from .contracts import ProductMetadata
from .paths import desktop_path_layout, user_data_directory

REPRESENTATIVE_IMPORTS = (
    "numpy",
    "scipy",
    "soundfile",
    "librosa",
)
OPTIONAL_RUNTIME_IMPORTS = ("torch", "torchaudio", "transformers")


def run_packaging_probe(output_path: Path, metadata: ProductMetadata) -> Path:
    """Validate packaged imports/resources/paths without loading a model."""
    imported: dict[str, str] = {}
    for module_name in REPRESENTATIVE_IMPORTS:
        module = importlib.import_module(module_name)
        imported[module_name] = str(getattr(module, "__version__", "unknown"))
    optional_runtime: dict[str, dict[str, str | bool]] = {}
    for module_name in OPTIONAL_RUNTIME_IMPORTS:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            optional_runtime[module_name] = {
                "available": False,
                "reason": "The optional runtime is not installed in this distribution.",
            }
        else:
            optional_runtime[module_name] = {
                "available": True,
                "reason": "Installed; model initialization is intentionally not part of startup.",
            }

    runtime_resource = resources.files("brain.infrastructure.config").joinpath(
        "resources", "runtime.yaml"
    )
    if not runtime_resource.is_file():
        raise RuntimeError("Packaged runtime.yaml resource is missing.")
    runtime_resource.read_text(encoding="utf-8")

    missing_brand_assets = tuple(
        filename for filename in APPROVED_BRAND_ASSETS if brand_asset_bytes(filename) is None
    )
    if missing_brand_assets:
        raise RuntimeError(f"Packaged brand assets are missing: {missing_brand_assets}")

    data_directory = user_data_directory()
    data_directory.mkdir(parents=True, exist_ok=True)
    install_directory = Path(sys.executable).resolve().parent
    resolved_data_directory = data_directory.resolve()
    if resolved_data_directory == install_directory or resolved_data_directory.is_relative_to(
        install_directory
    ):
        raise RuntimeError("User data directory resolves inside the install directory.")

    sentinel = data_directory / "packaging-probe.tmp"
    sentinel.write_text("writable", encoding="utf-8")
    sentinel.unlink()
    layout = desktop_path_layout()
    missing_directories = tuple(
        str(path) for path in layout.writable_directories if not path.is_dir()
    )
    if getattr(sys, "frozen", False) and missing_directories:
        raise RuntimeError(f"Writable first-run directories are missing: {missing_directories}")

    qt_plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    platform_plugin = qt_plugins / "platforms" / "qwindows.dll"
    if sys.platform == "win32" and not platform_plugin.is_file():
        raise RuntimeError("The packaged Windows Qt platform plugin is missing.")

    result = {
        "application_id": metadata.application_id,
        "cwd": str(Path.cwd()),
        "executable": str(Path(sys.executable).resolve()),
        "frozen": bool(getattr(sys, "frozen", False)),
        "imports": imported,
        "optional_runtime": optional_runtime,
        "brand_assets": list(APPROVED_BRAND_ASSETS),
        "model_download_attempted": False,
        "qt_platform": os.environ.get("QT_QPA_PLATFORM", "native"),
        "qt_plugins": str(qt_plugins.resolve()),
        "windows_platform_plugin": str(platform_plugin.resolve()),
        "runtime_resource": "brain.infrastructure.config/resources/runtime.yaml",
        "user_data_directory": str(resolved_data_directory),
        "user_data_outside_install": True,
        "writable_directories": [str(path.resolve()) for path in layout.writable_directories],
        "version": metadata.version,
    }

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
        json.dump(result, temporary, indent=2, ensure_ascii=False)
    temporary_path.replace(output_path)
    return output_path
