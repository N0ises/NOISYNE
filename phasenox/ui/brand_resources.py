"""Qt bridge over the approved packaged PHASENOX branding resources."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

from phasenox.resources.branding import (
    APP_ICON,
    PRIMARY_LOGO,
    BrandAssetName,
    read_brand_asset,
)

logger = logging.getLogger(__name__)

DARK_LOCKUP = BrandAssetName.PRIMARY_LOGO_DARK
LIGHT_LOCKUP = BrandAssetName.PRIMARY_LOGO_LIGHT
DARK_SYMBOL = BrandAssetName.SIGNAL_MARK
LIGHT_SYMBOL = BrandAssetName.MONOCHROME_MARK
APPROVED_BRAND_ASSETS = (
    APP_ICON,
    DARK_LOCKUP,
    LIGHT_LOCKUP,
    DARK_SYMBOL,
    LIGHT_SYMBOL,
)


def brand_asset_bytes(asset_name: BrandAssetName | str) -> bytes | None:
    """Return an approved packaged asset, or ``None`` on a noncritical failure."""
    try:
        return read_brand_asset(asset_name)
    except (FileNotFoundError, ModuleNotFoundError, OSError, TypeError, KeyError, ValueError):
        logger.warning("Desktop brand asset is unavailable: %s", asset_name)
        return None


def brand_pixmap(
    asset_name: BrandAssetName | str,
    *,
    width: int,
    height: int,
) -> QPixmap | None:
    payload = brand_asset_bytes(asset_name)
    if payload is None:
        return None
    pixmap = QPixmap()
    if not pixmap.loadFromData(payload):
        logger.warning("Desktop brand asset could not be decoded: %s", asset_name)
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


def sidebar_lockup(*, light_theme: bool = False) -> QPixmap | None:
    asset = PRIMARY_LOGO if light_theme else LIGHT_LOCKUP
    return brand_pixmap(asset, width=180, height=42)


__all__ = [
    "APPROVED_BRAND_ASSETS",
    "DARK_LOCKUP",
    "DARK_SYMBOL",
    "LIGHT_LOCKUP",
    "LIGHT_SYMBOL",
    "application_icon",
    "brand_asset_bytes",
    "brand_pixmap",
    "sidebar_lockup",
]
