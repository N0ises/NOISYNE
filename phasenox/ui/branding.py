"""Canonical desktop product identity with stable user-data compatibility."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from phasenox.resources.branding import ASCII_NAME, DISPLAY_NAME

from .contracts import ProductMetadata

# Deliberately retained in Sprint 17B: changing this value changes Qt's
# AppLocalDataLocation and would silently split existing Desktop user state.
DESKTOP_APPLICATION_ID = "soundbrain.desktop"


def _installed_version() -> str:
    try:
        return version("phasenox")
    except PackageNotFoundError:
        return "0.0.0-dev"


def default_product_metadata() -> ProductMetadata:
    """Return canonical PHASENOX identity and the stable Desktop application ID."""
    return ProductMetadata(
        display_name=DISPLAY_NAME,
        application_title=DISPLAY_NAME,
        version=_installed_version(),
        organization_name=ASCII_NAME,
        organization_domain=None,
        application_id=DESKTOP_APPLICATION_ID,
        ascii_name=ASCII_NAME,
        technical_identity=ASCII_NAME,
    )


__all__ = ["DESKTOP_APPLICATION_ID", "default_product_metadata"]
