from __future__ import annotations

from datetime import UTC, datetime, timedelta

from brain.ui.presentation_state import SessionState


def test_recent_files_are_deduplicated_and_bounded(tmp_path) -> None:
    session = SessionState(recent_limit=2)
    start = datetime.now(UTC)
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    third = tmp_path / "third.wav"

    session = session.select_audio(first, used_at=start)
    session = session.select_audio(second, used_at=start + timedelta(seconds=1))
    session = session.select_audio(first, used_at=start + timedelta(seconds=2))
    session = session.select_audio(third, used_at=start + timedelta(seconds=3))

    assert [item.path for item in session.recent_files] == [third, first]
    assert all(not item.exists for item in session.recent_files)


def test_reference_selection_deduplicates_paths(tmp_path) -> None:
    reference = tmp_path / "reference.wav"

    session = SessionState().select_references((reference, reference))

    assert session.selected_references == (reference,)
    assert len(session.recent_references) == 1
