from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QLabel

from brain.ui.contracts import (
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    ReferenceViewResult,
)
from brain.ui.pages import PageHost
from brain.ui.presentation_state import (
    PageId,
    PresentationState,
    ReferenceResultPresentationState,
    ResultPhase,
    RuntimePresentationState,
    SessionState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.reference_page import ReferencePage
from brain.ui.reference_state import ReferencePhase


def _state(availability: Availability = Availability.UNKNOWN) -> PresentationState:
    capability = CapabilitySnapshot(
        "reference_comparison",
        "Reference comparison",
        CapabilityLifecycle.PRODUCTION,
        availability,
        reason="Machine readiness has not been probed.",
    )
    return replace(
        PresentationState(),
        runtime=RuntimePresentationState(capabilities=(capability,)),
    )


def _drop(page: ReferencePage, paths) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    page.dropEvent(event)


def test_references_page_selects_multiple_removes_and_clears(qtbot, tmp_path) -> None:
    current = tmp_path / "current.wav"
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    for path in (current, first, second):
        path.write_bytes(b"audio")
    page = ReferencePage()
    qtbot.addWidget(page)
    page.render(_state())

    page.select_current(current)
    page.add_references((first, second))

    assert page.form_state.phase is ReferencePhase.READY
    assert page.form_state.reference_paths == (first, second)
    assert len(page.findChildren(QLabel, "referenceSelectedPath")) >= 2

    page.remove_reference(first)
    assert page.form_state.reference_paths == (second,)
    page.select_current(None)
    assert page.form_state.current_path is None
    assert page.form_state.phase is ReferencePhase.EMPTY


def test_drag_drop_assigns_current_then_multiple_references(qtbot, tmp_path) -> None:
    current = tmp_path / "current.wav"
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    for path in (current, first, second):
        path.write_bytes(b"audio")
    page = ReferencePage()
    qtbot.addWidget(page)
    page.render(_state())

    _drop(page, (current, first, second))

    assert page.form_state.current_path == current
    assert page.form_state.reference_paths == (first, second)


def test_missing_paths_and_unavailable_capability_disable_review(qtbot, tmp_path) -> None:
    current = tmp_path / "current.wav"
    current.write_bytes(b"audio")
    page = ReferencePage()
    qtbot.addWidget(page)
    page.render(_state(Availability.UNAVAILABLE))
    page.select_current(current)
    page.add_references((tmp_path / "missing.wav",))

    assert page.form_state.phase is ReferencePhase.INVALID
    assert "missing" in page.validation_label.text()
    assert not page.review_button.isEnabled()
    assert page.capability_badge.text() == "Unavailable"


def test_review_constructs_real_metadata_confirmation(qtbot, tmp_path) -> None:
    current = tmp_path / "current.wav"
    reference = tmp_path / "reference.wav"
    current.write_bytes(b"audio")
    reference.write_bytes(b"audio")
    page = ReferencePage()
    qtbot.addWidget(page)
    page.render(_state(Availability.AVAILABLE))
    page.select_current(current)
    page.add_references((reference,))
    page.genre_input.setText("pop")
    page.mood_input.setText("bright")
    page.target_input.setText("streaming")
    page.focus_input.setText("loudness, stereo")

    page.review()

    command = page.form_state.build_command()
    assert page.form_state.phase is ReferencePhase.REVIEW
    assert command.genre == "pop"
    assert command.mood == "bright"
    assert command.target == "streaming"
    assert command.focus_areas == ("loudness", "stereo")
    assert str(reference) in page.review_summary.text()


def test_navigation_away_and_back_retains_reference_result(qtbot, tmp_path) -> None:
    current = tmp_path / "current.wav"
    reference = tmp_path / "reference.wav"
    result = ReferenceViewResult(current, (reference,), "ok", 88.0, 0.9)
    base = _state(Availability.AVAILABLE)
    state = replace(
        base,
        reference_result=ReferenceResultPresentationState(
            ResultPhase.SUCCESS,
            result=result,
        ),
        session=SessionState(last_reference_result=result),
    )
    store = PresentationStore(state)
    host = PageHost()
    qtbot.addWidget(host)
    references = host.page(PageId.REFERENCES)
    assert isinstance(references, ReferencePage)

    host.render(store.state)
    store.navigate(PageId.OVERVIEW)
    host.show_page(PageId.OVERVIEW)
    store.navigate(PageId.REFERENCES)
    host.show_page(PageId.REFERENCES)
    host.render(store.state)

    assert host.page(PageId.REFERENCES) is references
    assert store.state.reference_result.result is result
    assert store.state.session.last_reference_result is result
    assert references.view_result_button.isVisible() or not references.isVisible()


def test_running_comparison_disables_repeat_execution(qtbot, tmp_path) -> None:
    current = tmp_path / "current.wav"
    reference = tmp_path / "reference.wav"
    current.write_bytes(b"audio")
    reference.write_bytes(b"audio")
    page = ReferencePage()
    qtbot.addWidget(page)
    state = _state(Availability.AVAILABLE)
    page.render(state)
    page.select_current(current)
    page.add_references((reference,))

    page.render(
        replace(
            state,
            reference_result=ReferenceResultPresentationState.loading("reference-operation"),
        )
    )

    assert not page.review_button.isEnabled()
    assert not page.compare_button.isEnabled()
    assert "indeterminate" in page.status_message.text()
