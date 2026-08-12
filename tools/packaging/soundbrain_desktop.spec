# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


project_root = Path(SPECPATH).resolve().parents[1]
entry_point = project_root / "brain" / "ui" / "__main__.py"

analysis = Analysis(
    [str(entry_point)],
    pathex=[str(project_root)],
    binaries=[],
    datas=collect_data_files("brain.infrastructure.config"),
    hiddenimports=[
        "numpy",
        "scipy",
        "soundfile",
        "librosa",
        "transformers",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # The checked development environment contains a 4+ GB CUDA Torch build.
    # The Sprint 1 gate validates the Transformers application seam without
    # bundling a model backend. Production model/backend bundles need a
    # deliberate CPU/GPU packaging policy rather than inheriting this venv.
    excludes=[
        "torch",
        "torchaudio",
        "torchvision",
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
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="soundbrain-desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
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
    upx=True,
    upx_exclude=[],
    name="soundbrain-desktop",
)
