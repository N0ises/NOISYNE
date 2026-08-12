from __future__ import annotations

from PySide6.QtWidgets import QScrollArea

from brain.ui.app import build_main_window
from brain.ui.design_system.gallery import ComponentGallery
from brain.ui.design_system.tokens import DEFAULT_TOKENS
from brain.ui.presentation_store import PresentationStore
from brain.ui.state import ApplicationStateStore


def test_shell_and_gallery_resize_at_narrow_and_large_sizes(qtbot, fake_adapter) -> None:
    window = build_main_window(fake_adapter, ApplicationStateStore(), PresentationStore())
    qtbot.addWidget(window)
    window.show()
    gallery = window.findChild(ComponentGallery, "internalComponentGallery")

    window.resize(
        DEFAULT_TOKENS.controls.window_minimum_width,
        DEFAULT_TOKENS.controls.window_minimum_height,
    )
    qtbot.wait(10)
    assert gallery is not None
    assert gallery.widgetResizable()
    assert gallery.viewport().width() > 0
    assert gallery.horizontalScrollBar().maximum() == 0

    window.resize(1440, 900)
    qtbot.wait(10)
    assert window.width() == 1440
    assert window.height() == 900
    assert gallery.horizontalScrollBar().maximum() == 0
    assert window.findChild(QScrollArea, "internalComponentGallery") is gallery
