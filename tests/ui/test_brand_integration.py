from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget

from brain.ui import shell_surfaces
from brain.ui.app import build_main_window, create_application
from brain.ui.brand_resources import (
    APP_ICON,
    DARK_LOCKUP,
    DARK_SYMBOL,
    LIGHT_LOCKUP,
    LIGHT_SYMBOL,
    application_icon,
    brand_asset_bytes,
)
from brain.ui.branding import default_product_metadata
from brain.ui.design_system.semantics import VisualState
from brain.ui.design_system.tokens import DEFAULT_TOKENS
from brain.ui.session_persistence import SCHEMA_VERSION
from brain.ui.shell_surfaces import ProductIdentity
from brain.ui.state import ApplicationStateStore


def test_product_metadata_exposes_public_ascii_and_technical_identity() -> None:
    metadata = default_product_metadata()

    assert metadata.display_name == "NØISYNE"
    assert metadata.application_title == "NØISYNE"
    assert metadata.ascii_name == "NOISYNE"
    assert metadata.technical_identity == "SoundBrain"
    assert metadata.application_id == "soundbrain.desktop"


def test_approved_runtime_assets_are_packaged_and_decodable(qapp) -> None:
    for filename in (APP_ICON, DARK_LOCKUP, LIGHT_LOCKUP, DARK_SYMBOL, LIGHT_SYMBOL):
        payload = brand_asset_bytes(filename)
        assert payload is not None and payload

    assert not application_icon().isNull()
    for filename in (DARK_LOCKUP, LIGHT_LOCKUP):
        assert b"<text" not in brand_asset_bytes(filename)


def test_application_window_and_sidebar_use_central_identity(qtbot, monkeypatch) -> None:
    metadata = default_product_metadata()
    application = create_application(metadata)

    class BrandedAdapter:
        def product_metadata(self):
            return metadata

        def settings_snapshot(self):
            raise RuntimeError("not needed")

    window = build_main_window(BrandedAdapter(), ApplicationStateStore())
    qtbot.addWidget(window)
    identity = window.findChild(ProductIdentity, "productIdentity")

    assert application.applicationDisplayName() == metadata.display_name
    assert not application.windowIcon().isNull()
    assert window.windowTitle() == metadata.application_title
    assert not window.windowIcon().isNull()
    assert identity.accessibleName().startswith(metadata.display_name)
    assert identity.brand_mark.pixmap() is not None
    assert identity.brand_mark.pixmap().width() <= 164
    assert identity.brand_mark.pixmap().height() <= 34
    assert window.findChild(QListWidget, "primaryNavigation").horizontalScrollBarPolicy() is (
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )


def test_missing_brand_assets_fall_back_to_metadata_without_crashing(qtbot, monkeypatch) -> None:
    monkeypatch.setattr(shell_surfaces, "brand_pixmap", lambda *args, **kwargs: None)
    metadata = default_product_metadata()

    identity = ProductIdentity(metadata)
    qtbot.addWidget(identity)

    assert identity.name_label.text() == metadata.display_name
    assert not identity.name_label.isHidden()
    assert identity.brand_mark.pixmap().isNull()


def test_brand_tokens_match_approved_package_and_cover_status_language() -> None:
    colors = DEFAULT_TOKENS.colors

    assert colors.background == "#0A0A0A"
    assert colors.surface == "#141414"
    assert colors.surface_raised == "#1E1E1E"
    assert colors.border == "#2E2E2E"
    assert colors.border_strong == "#404040"
    assert colors.text_primary == "#EDEDED"
    assert colors.text_secondary == "#A3A3A3"
    assert colors.text_muted == "#737373"
    assert colors.disabled_text == "#525252"
    assert colors.success == "#10B981"
    assert colors.warning == "#F59E0B"
    assert colors.error == "#EF4444"
    assert colors.unavailable == "#525252"
    assert colors.unknown == "#8B5CF6"
    assert colors.running == "#3B82F6"
    assert colors.degraded == "#F97316"
    assert colors.intelligence == "#6366F1"
    assert VisualState.INTELLIGENCE.value == "intelligence"


def test_ai_reasoning_uses_restrained_central_intelligence_semantic(qtbot) -> None:
    from brain.ui.intelligence_page import IntelligencePage

    page = IntelligencePage()
    qtbot.addWidget(page)

    assert DEFAULT_TOKENS.colors.intelligence == "#6366F1"
    source = Path("brain/ui/intelligence_page.py").read_text(encoding="utf-8")
    assert 'setProperty("semantic", "intelligence")' in source
    assert "#6366F1" not in source


def test_user_facing_ui_sources_do_not_contain_legacy_display_brand() -> None:
    ui_root = Path("brain/ui")
    user_facing_sources = (
        "analyze_page.py",
        "dashboard.py",
        "intelligence_page.py",
        "knowledge_page.py",
        "main_window.py",
        "pages.py",
        "presentation.py",
        "reference_page.py",
        "reports_page.py",
        "settings_page.py",
        "shell_surfaces.py",
    )

    assert all(
        "SoundBrain" not in (ui_root / filename).read_text(encoding="utf-8")
        for filename in user_facing_sources
    )
    assert (ui_root.parent / "application" / "soundbrain_service.py").exists()
    assert SCHEMA_VERSION == 2


def test_page_modules_do_not_scatter_raw_brand_colors() -> None:
    ui_root = Path("brain/ui")
    pages = tuple(ui_root.glob("*_page.py")) + (ui_root / "dashboard.py",)

    assert all("#6366F1" not in path.read_text(encoding="utf-8") for path in pages)
    assert all("#0A0A0A" not in path.read_text(encoding="utf-8") for path in pages)
