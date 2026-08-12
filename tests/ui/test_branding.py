from __future__ import annotations

from brain.ui.branding import default_product_metadata


def test_default_product_identity_is_centralized() -> None:
    metadata = default_product_metadata()

    assert metadata.display_name
    assert metadata.application_title == metadata.display_name
    assert metadata.application_id == "soundbrain.desktop"
    assert metadata.version
