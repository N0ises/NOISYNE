"""Qt-independent access to packaged PHASENØX brand resources."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from types import MappingProxyType

DISPLAY_NAME = "PHASENØX"
ASCII_NAME = "PHASENOX"
WORDMARK_RHYTHM = "PHASE   NØX"


class BrandAssetName(StrEnum):
    """Stable logical names for assets intended for runtime consumption."""

    PRIMARY_LOGO_DARK = "primary_logo_dark"
    PRIMARY_LOGO_LIGHT = "primary_logo_light"
    WORDMARK_DARK = "wordmark_dark"
    WORDMARK_LIGHT = "wordmark_light"
    MONOCHROME_MARK = "monochrome_mark"
    SIGNAL_MARK = "signal_mark"
    SPLASH = "splash"
    APP_ICON_16 = "app_icon_16"
    APP_ICON_32 = "app_icon_32"
    APP_ICON_64 = "app_icon_64"
    APP_ICON_128 = "app_icon_128"
    APP_ICON_256 = "app_icon_256"
    APP_ICON_512 = "app_icon_512"
    APP_ICON_1024 = "app_icon_1024"


@dataclass(frozen=True, slots=True)
class BrandAsset:
    """Metadata and package-safe access for one immutable branding resource."""

    name: BrandAssetName
    filename: str
    media_type: str
    width: int
    height: int
    source_path: str

    def resource(self) -> Traversable:
        """Return the importlib resource without assuming a filesystem install."""
        return resources.files(__package__).joinpath(self.filename)

    def read_bytes(self) -> bytes:
        """Read the resource from a source checkout, wheel, or zip importer."""
        return self.resource().read_bytes()


def _asset(
    name: BrandAssetName,
    filename: str,
    media_type: str,
    dimensions: tuple[int, int],
    source_path: str,
) -> BrandAsset:
    return BrandAsset(name, filename, media_type, *dimensions, source_path)


_BRAND_ASSETS = {
    BrandAssetName.PRIMARY_LOGO_DARK: _asset(
        BrandAssetName.PRIMARY_LOGO_DARK,
        "phasenox-master.svg",
        "image/svg+xml",
        (1500, 300),
        "assets/brand/master/phasenox-master.svg",
    ),
    BrandAssetName.PRIMARY_LOGO_LIGHT: _asset(
        BrandAssetName.PRIMARY_LOGO_LIGHT,
        "phasenox-master-light.svg",
        "image/svg+xml",
        (1500, 300),
        "assets/brand/master/phasenox-master-light.svg",
    ),
    BrandAssetName.WORDMARK_DARK: _asset(
        BrandAssetName.WORDMARK_DARK,
        "phasenox-wordmark.svg",
        "image/svg+xml",
        (1500, 260),
        "assets/brand/master/phasenox-wordmark.svg",
    ),
    BrandAssetName.WORDMARK_LIGHT: _asset(
        BrandAssetName.WORDMARK_LIGHT,
        "phasenox-wordmark-light.svg",
        "image/svg+xml",
        (1500, 260),
        "assets/brand/master/phasenox-wordmark-light.svg",
    ),
    BrandAssetName.MONOCHROME_MARK: _asset(
        BrandAssetName.MONOCHROME_MARK,
        "phasenox-symbol.svg",
        "image/svg+xml",
        (1024, 1024),
        "assets/brand/master/phasenox-symbol.svg",
    ),
    BrandAssetName.SIGNAL_MARK: _asset(
        BrandAssetName.SIGNAL_MARK,
        "phasenox-symbol-dark.svg",
        "image/svg+xml",
        (1024, 1024),
        "assets/brand/master/phasenox-symbol-dark.svg",
    ),
    BrandAssetName.SPLASH: _asset(
        BrandAssetName.SPLASH,
        "phasenox-hero-banner.svg",
        "image/svg+xml",
        (1920, 720),
        "assets/brand/hero/phasenox-hero-banner.svg",
    ),
    BrandAssetName.APP_ICON_16: _asset(
        BrandAssetName.APP_ICON_16,
        "phasenox-logo-16x16.png",
        "image/png",
        (16, 16),
        "assets/brand/exports/phasenox-logo-16x16.png",
    ),
    BrandAssetName.APP_ICON_32: _asset(
        BrandAssetName.APP_ICON_32,
        "phasenox-logo-32x32.png",
        "image/png",
        (32, 32),
        "assets/brand/exports/phasenox-logo-32x32.png",
    ),
    BrandAssetName.APP_ICON_64: _asset(
        BrandAssetName.APP_ICON_64,
        "phasenox-logo-64x64.png",
        "image/png",
        (64, 64),
        "assets/brand/exports/phasenox-logo-64x64.png",
    ),
    BrandAssetName.APP_ICON_128: _asset(
        BrandAssetName.APP_ICON_128,
        "phasenox-logo-128x128.png",
        "image/png",
        (128, 128),
        "assets/brand/exports/phasenox-logo-128x128.png",
    ),
    BrandAssetName.APP_ICON_256: _asset(
        BrandAssetName.APP_ICON_256,
        "phasenox-logo-256x256.png",
        "image/png",
        (256, 256),
        "assets/brand/exports/phasenox-logo-256x256.png",
    ),
    BrandAssetName.APP_ICON_512: _asset(
        BrandAssetName.APP_ICON_512,
        "phasenox-logo-512x512.png",
        "image/png",
        (512, 512),
        "assets/brand/exports/phasenox-logo-512x512.png",
    ),
    BrandAssetName.APP_ICON_1024: _asset(
        BrandAssetName.APP_ICON_1024,
        "phasenox-logo-1024x1024.png",
        "image/png",
        (1024, 1024),
        "assets/brand/exports/phasenox-logo-1024x1024.png",
    ),
}

BRAND_ASSETS: Mapping[BrandAssetName, BrandAsset] = MappingProxyType(_BRAND_ASSETS)

PRIMARY_LOGO = BrandAssetName.PRIMARY_LOGO_DARK
WORDMARK = BrandAssetName.WORDMARK_DARK
APP_ICON = BrandAssetName.APP_ICON_256
MONOCHROME_MARK = BrandAssetName.MONOCHROME_MARK
SPLASH = BrandAssetName.SPLASH


def get_brand_asset(name: BrandAssetName | str) -> BrandAsset:
    """Return immutable metadata for a stable logical asset name."""
    try:
        asset_name = BrandAssetName(name)
    except ValueError as error:
        raise KeyError(f"Unknown PHASENOX brand asset: {name}") from error
    return BRAND_ASSETS[asset_name]


def read_brand_asset(name: BrandAssetName | str) -> bytes:
    """Read one packaged asset without relying on the current directory."""
    return get_brand_asset(name).read_bytes()


@contextmanager
def materialize_brand_asset(name: BrandAssetName | str) -> Iterator[Path]:
    """Yield a temporary or installed filesystem path for path-only consumers."""
    with resources.as_file(get_brand_asset(name).resource()) as path:
        yield path


__all__ = [
    "APP_ICON",
    "ASCII_NAME",
    "BRAND_ASSETS",
    "DISPLAY_NAME",
    "MONOCHROME_MARK",
    "PRIMARY_LOGO",
    "SPLASH",
    "WORDMARK",
    "WORDMARK_RHYTHM",
    "BrandAsset",
    "BrandAssetName",
    "get_brand_asset",
    "materialize_brand_asset",
    "read_brand_asset",
]
