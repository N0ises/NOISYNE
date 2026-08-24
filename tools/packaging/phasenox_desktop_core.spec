# -*- mode: python ; coding: utf-8 -*-
"""Canonical PHASENOX Desktop Core PyInstaller specification."""

import json
import os
import tomllib
from pathlib import Path

from PyInstaller.building.datastruct import TOC
from PyInstaller.utils.hooks import copy_metadata

SPEC_DIR = Path(SPECPATH).resolve()
REPOSITORY = SPEC_DIR.parents[1]
PROFILE = json.loads(
    (SPEC_DIR / "profiles" / "desktop-core-windows-x64.json").read_text(encoding="utf-8")
)
with (REPOSITORY / "pyproject.toml").open("rb") as stream:
    VERSION = tomllib.load(stream)["project"]["version"]
GENERATED = Path(os.environ["PHASENOX_WINDOWS_ASSETS"]).resolve()

datas = []
for filename in PROFILE["config_resources"]:
    datas.append(
        (
            str(REPOSITORY / "phasenox" / "infrastructure" / "config" / "resources" / filename),
            "phasenox/infrastructure/config/resources",
        )
    )
for filename in PROFILE["branding_resources"]:
    datas.append(
        (
            str(REPOSITORY / "phasenox" / "resources" / "branding" / filename),
            "phasenox/resources/branding",
        )
    )
datas += copy_metadata("phasenox")

forbidden_modules = PROFILE["forbidden_module_roots"] + [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtVirtualKeyboard",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "numba.np.ufunc.tbbpool",
]

analysis = Analysis(
    [str(REPOSITORY / PROFILE["application"]["entry_module"])],
    pathex=[str(REPOSITORY)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "librosa",
        "numpy",
        "pyloudnorm",
        "scipy",
        "soundfile",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=forbidden_modules,
    noarchive=False,
    optimize=1,
)

allowed_plugins = {value.casefold() for value in PROFILE["qt_plugins"]}


def keep_qt_payload(item):
    destination = "/" + item[0].replace("\\", "/").casefold().lstrip("/")
    if "/qt/qml/" in destination:
        return False
    markers = ("/qt/plugins/", "/pyside6/plugins/")
    marker = next((value for value in markers if value in destination), None)
    if marker is None:
        return True
    relative = destination.split(marker, 1)[1]
    return relative in allowed_plugins


def keep_runtime_data(item):
    destination = item[0].replace("\\", "/").casefold()
    return "/tests/" not in f"/{destination}/" and not destination.startswith("tests/")


analysis.binaries = TOC(item for item in analysis.binaries if keep_qt_payload(item))
analysis.datas = TOC(
    item for item in analysis.datas if keep_qt_payload(item) and keep_runtime_data(item)
)

pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="PHASENOX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(GENERATED / "PHASENOX.ico"),
    version=str(GENERATED / "PHASENOX-version.txt"),
    manifest=str(GENERATED / "PHASENOX.exe.manifest"),
)
collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name=f"PHASENOX-{VERSION}-win-x64",
)
