from __future__ import annotations

from brain.ui.design_system.gallery import ComponentGallery
from brain.ui.design_system.tokens import DEFAULT_TOKENS


def test_development_gallery_resizes_standalone(qtbot) -> None:
    gallery = ComponentGallery()
    qtbot.addWidget(gallery)
    gallery.show()

    gallery.resize(
        DEFAULT_TOKENS.controls.window_minimum_width,
        DEFAULT_TOKENS.controls.window_minimum_height,
    )
    qtbot.wait(10)
    assert gallery is not None
    assert gallery.widgetResizable()
    assert gallery.viewport().width() > 0
    assert gallery.horizontalScrollBar().maximum() == 0

    gallery.resize(1440, 900)
    qtbot.wait(10)
    assert gallery.width() == 1440
    assert gallery.height() == 900
    assert gallery.horizontalScrollBar().maximum() == 0
