"""Qt brand resources loaded from the installed package, never the working directory."""

from __future__ import annotations

import logging
from importlib import resources

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

logger = logging.getLogger(__name__)

_RESOURCE_PACKAGE = "brain.ui.resources"
_BRAND_ROOT = ("brand", "noisyne")
APP_ICON = "noisyne-app-icon-256.png"
DARK_LOCKUP = "noisyne-master.svg"
LIGHT_LOCKUP = "noisyne-master-light.svg"
DARK_SYMBOL = "noisyne-symbol-dark.svg"
LIGHT_SYMBOL = "noisyne-symbol.svg"
APPROVED_BRAND_ASSETS = (
    APP_ICON,
    DARK_LOCKUP,
    LIGHT_LOCKUP,
    DARK_SYMBOL,
    LIGHT_SYMBOL,
)


def brand_asset_bytes(filename: str) -> bytes | None:
    """Return an approved packaged asset, or None for a noncritical load failure."""
    try:
        asset = resources.files(_RESOURCE_PACKAGE).joinpath(*_BRAND_ROOT, filename)
        return asset.read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, OSError, TypeError):
        logger.warning("Desktop brand asset is unavailable: %s", filename)
        return None


def brand_pixmap(filename: str, *, width: int, height: int) -> QPixmap | None:
    payload = brand_asset_bytes(filename)
    if payload is None:
        return None
    pixmap = QPixmap()
    if not pixmap.loadFromData(payload):
        logger.warning("Desktop brand asset could not be decoded: %s", filename)
        return None
    return pixmap.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def application_icon() -> QIcon:
    pixmap = brand_pixmap(APP_ICON, width=256, height=256)
    return QIcon(pixmap) if pixmap is not None else QIcon()
