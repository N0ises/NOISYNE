# -*- mode: python ; coding: utf-8 -*-

import os
from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


project_root = Path(SPECPATH).resolve().parents[1]
entry_point = project_root / "brain" / "ui" / "__main__.py"
generated_root = project_root / "build" / "packaging"
icon_path = generated_root / "NOISYNE.ico"
version_path = generated_root / "NOISYNE-version.txt"
profile = os.environ.get("NOISYNE_PACKAGE_PROFILE", "cpu").strip().lower()

if profile not in {"cpu", "shell"}:
    raise SystemExit("NOISYNE_PACKAGE_PROFILE must be 'cpu' or 'shell'.")
if not icon_path.is_file() or not version_path.is_file():
    raise SystemExit("Run tools/packaging/generate_windows_assets.py before PyInstaller.")

hidden_imports = ["numpy", "scipy", "soundfile", "librosa", "pyloudnorm", "transformers"]
excludes = [
    "tensorflow",
    "jax",
    "flax",
    "datasets",
    "spacy",
    "cv2",
    "onnxruntime",
    "chromadb",
    "langchain",
    "nltk",
    "pandas",
    "pyarrow",
    "tkinter",
    "pytest",
    "pytestqt",
    "black",
    "ruff",
    "sklearn.datasets.tests",
    "torch.fx.passes.tests",
]

if profile == "cpu":
    if find_spec("torch") is None or find_spec("torchaudio") is None:
        raise SystemExit("The CPU release profile requires Torch and Torchaudio.")
    import torch

    if torch.version.cuda is not None:
        raise SystemExit("Refusing to package a CUDA Torch environment; use a CPU-only build venv.")
    hidden_imports.extend(("torch", "torchaudio"))
else:
    excludes.extend(("torch", "torchaudio", "torchvision"))

datas = []
datas += collect_data_files("brain.infrastructure.config", includes=["resources/*.yaml"])
datas += collect_data_files("brain.ui.resources", includes=["brand/noisyne/*"])
datas += copy_metadata("soundbrain")

analysis = Analysis(
    [str(entry_point)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
analysis.datas = TOC(
    item
    for item in analysis.datas
    if not item[0].replace("/", "\\").startswith("sklearn\\datasets\\tests\\")
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="NOISYNE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_path),
    version=str(version_path),
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NOISYNE",
)
