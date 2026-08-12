"""Central desktop product identity."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .contracts import ProductMetadata


def _installed_version() -> str:
    try:
        return version("soundbrain")
    except PackageNotFoundError:
        return "0.0.0-dev"


def default_product_metadata() -> ProductMetadata:
    """Return the single source for public and intentionally separate technical identity."""
    display_name = "NØISYNE"
    return ProductMetadata(
        display_name=display_name,
        application_title=display_name,
        version=_installed_version(),
        organization_name="NOISYNE",
        organization_domain=None,
        application_id="soundbrain.desktop",
        ascii_name="NOISYNE",
        technical_identity="SoundBrain",
    )
