"""Runtime checks used by the Windows packaging walking skeleton."""

from __future__ import annotations

import importlib
import json
import os
import sys
from importlib import resources
from pathlib import Path
from tempfile import NamedTemporaryFile

from .contracts import ProductMetadata
from .paths import user_data_directory

REPRESENTATIVE_IMPORTS = (
    "numpy",
    "scipy",
    "soundfile",
    "librosa",
    "transformers",
)
SOURCE_ONLY_IMPORTS = ("torch",)


def run_packaging_probe(output_path: Path, metadata: ProductMetadata) -> Path:
    """Validate packaged imports/resources/paths without loading a model."""
    imported: dict[str, str] = {}
    module_names = REPRESENTATIVE_IMPORTS
    if not getattr(sys, "frozen", False):
        module_names += SOURCE_ONLY_IMPORTS
    for module_name in module_names:
        module = importlib.import_module(module_name)
        imported[module_name] = str(getattr(module, "__version__", "unknown"))

    runtime_resource = resources.files("brain.infrastructure.config").joinpath(
        "resources", "runtime.yaml"
    )
    if not runtime_resource.is_file():
        raise RuntimeError("Packaged runtime.yaml resource is missing.")
    runtime_resource.read_text(encoding="utf-8")

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

    result = {
        "application_id": metadata.application_id,
        "cwd": str(Path.cwd()),
        "executable": str(Path(sys.executable).resolve()),
        "frozen": bool(getattr(sys, "frozen", False)),
        "imports": imported,
        "model_download_attempted": False,
        "qt_platform": os.environ.get("QT_QPA_PLATFORM", "native"),
        "runtime_resource": "brain.infrastructure.config/resources/runtime.yaml",
        "user_data_directory": str(resolved_data_directory),
        "user_data_outside_install": True,
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
