from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QFileDialog

from brain.ui.analyze_page import AnalyzePage
from brain.ui.analyze_state import AnalyzePhase
from brain.ui.contracts import Availability, CapabilityLifecycle, CapabilitySnapshot
from brain.ui.presentation_state import PresentationState, RuntimePresentationState


def _drop(page: AnalyzePage, path: Path) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    page.dropEvent(event)


def test_selection_drag_drop_clear_and_confirmation(qtbot, tmp_path) -> None:
    source = tmp_path / "source.wav"
    reference = tmp_path / "reference.wav"
    source.write_bytes(b"source")
    reference.write_bytes(b"reference")
    page = AnalyzePage()
    qtbot.addWidget(page)

    _drop(page, source)
    assert page.form_state.source_path == source
    assert page.form_state.phase is AnalyzePhase.READY

    page.select_reference(reference)
    page.intent_input.setText("review")
    page.delivery_input.setText("streaming")
    page.review()

    assert page.form_state.phase is AnalyzePhase.REVIEW
    assert page.review_card.isVisible() or not page.isVisible()
    assert str(source) in page.review_summary.text()
    assert str(reference) in page.review_summary.text()

    page.select_source(None)
    assert page.form_state.source_path is None
    assert page.form_state.phase is AnalyzePhase.EMPTY


def test_native_file_picker_selects_source(qtbot, monkeypatch, tmp_path) -> None:
    source = tmp_path / "picked.wav"
    source.write_bytes(b"source")
    page = AnalyzePage()
    qtbot.addWidget(page)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(source), "Audio files"),
    )

    page.choose_source_button.click()

    assert page.form_state.source_path == source
    assert page.form_state.phase is AnalyzePhase.READY


def test_missing_file_shows_validation_error(qtbot, tmp_path) -> None:
    page = AnalyzePage()
    qtbot.addWidget(page)

    page.select_source(tmp_path / "missing.wav")

    assert page.form_state.phase is AnalyzePhase.INVALID
    assert "no longer exists" in page.validation_label.text()
    assert not page.review_button.isEnabled()


def test_capability_disabled_degraded_and_unknown_controls(qtbot) -> None:
    capabilities = (
        CapabilitySnapshot(
            "llm_reasoning",
            "Reasoning",
            CapabilityLifecycle.PLANNED,
            Availability.AVAILABLE,
            reason="Planned",
        ),
        CapabilitySnapshot(
            "rag_retrieval",
            "RAG",
            CapabilityLifecycle.IMPLEMENTED,
            Availability.DEGRADED,
            reason="Limited corpus",
        ),
        CapabilitySnapshot(
            "mix_intelligence",
            "Mix",
            CapabilityLifecycle.PRODUCTION,
            Availability.UNKNOWN,
            reason="Not checked",
        ),
    )
    page = AnalyzePage()
    qtbot.addWidget(page)
    page.render(
        replace(
            PresentationState(),
            runtime=RuntimePresentationState(capabilities=capabilities),
        )
    )

    assert not page.feature_toggles["include_reasoning"].isEnabled()
    assert page.feature_toggles["include_rag"].isEnabled()
    assert "availability: degraded" in page.feature_reasons["include_rag"].text()
    assert not page.feature_toggles["include_mix_intelligence"].isEnabled()
    assert "availability: unknown" in page.feature_reasons["include_mix_intelligence"].text()
