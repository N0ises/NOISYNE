from __future__ import annotations

import json
from datetime import UTC, datetime

from brain.ui.contracts import AnalysisViewResult, ReportDescriptor
from brain.ui.presentation_state import PageId, SessionState
from brain.ui.session_persistence import SessionRepository


def test_session_round_trip_is_allowlisted_and_marks_missing_paths(tmp_path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    report = tmp_path / "report.json"
    result = AnalysisViewResult(
        source_path=audio,
        status="ok",
        audio_type="mix",
        score=91.0,
        summary="secret free text must not persist",
        warnings=("private warning",),
        reports=(ReportDescriptor("analysis", "json", report, "JSON"),),
    )
    session = (
        SessionState(recent_limit=2)
        .navigate(PageId.REPORTS)
        .record_analysis(result, analyzed_at=datetime.now(UTC))
    )
    repository = SessionRepository(tmp_path / "state" / "session.json")

    repository.save(session)
    raw = repository.path.read_text(encoding="utf-8")
    loaded = repository.load().session

    assert "secret free text" not in raw
    assert "private warning" not in raw
    assert "current_operation" not in raw
    assert loaded.navigation.current_page is PageId.REPORTS
    assert loaded.selected_audio == audio
    assert loaded.last_analysis_result is not None
    assert loaded.last_analysis_result.summary == ""
    assert not loaded.recent_reports[0].exists


def test_missing_selected_files_are_safe_on_restore(tmp_path) -> None:
    repository = SessionRepository(tmp_path / "session.json")
    repository.path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "navigation": "overview",
                "selected_audio": str(tmp_path / "missing.wav"),
                "selected_references": [str(tmp_path / "missing-reference.wav")],
            }
        ),
        encoding="utf-8",
    )

    loaded = repository.load().session

    assert loaded.selected_audio is None
    assert loaded.selected_references == ()


def test_corrupt_session_is_quarantined_and_startup_recovers(tmp_path) -> None:
    repository = SessionRepository(tmp_path / "session.json")
    repository.path.write_text("{not-json", encoding="utf-8")

    loaded = repository.load()

    assert loaded.recovered_from_corruption
    assert loaded.warning
    assert loaded.backup_path is not None
    assert loaded.backup_path.exists()
    assert not repository.path.exists()
    assert loaded.session == SessionState()


def test_restored_recent_items_remain_deduplicated_and_bounded(tmp_path) -> None:
    repository = SessionRepository(tmp_path / "session.json")
    recent_files = [
        {
            "path": str(tmp_path / f"{index}.wav"),
            "last_used_at": datetime.now(UTC).isoformat(),
        }
        for index in range(25)
    ]
    recent_files.insert(1, recent_files[0])
    repository.path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "navigation": "overview",
                "selected_references": [],
                "recent_files": recent_files,
            }
        ),
        encoding="utf-8",
    )

    loaded = repository.load().session

    assert len(loaded.recent_files) == 20
    assert len({item.path for item in loaded.recent_files}) == 20
