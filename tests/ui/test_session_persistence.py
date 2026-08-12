from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from brain.ui.contracts import AnalysisViewResult, OperationHandle, ReportDescriptor
from brain.ui.presentation_state import PageId, PresentationState, SessionState
from brain.ui.presentation_store import PresentationStore
from brain.ui.session_persistence import SessionPersistenceBinding, SessionRepository


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
        reports=(ReportDescriptor("analysis", "json", report, "JSON", audio),),
    )
    session = (
        SessionState(recent_limit=2)
        .navigate(PageId.REPORTS)
        .record_analysis(result, analyzed_at=datetime.now(UTC))
        .select_report(report)
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
    assert loaded.recent_reports[0].descriptor.source_path == audio
    assert loaded.selected_report_path == report


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

    assert loaded.selected_audio == tmp_path / "missing.wav"
    assert loaded.selected_references == (tmp_path / "missing-reference.wav",)
    assert not loaded.selected_audio.exists()


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


def test_v1_session_migrates_with_v2_fields_at_safe_defaults(tmp_path) -> None:
    repository = SessionRepository(tmp_path / "session.json")
    repository.path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "navigation": "knowledge",
                "selected_audio": None,
                "selected_references": [],
            }
        ),
        encoding="utf-8",
    )

    loaded = repository.load().session

    assert loaded.navigation.current_page is PageId.KNOWLEDGE
    assert loaded.selected_report_path is None
    assert loaded.last_knowledge_query == ""
    assert loaded.recent_knowledge_queries == ()


def test_v2_round_trip_retains_bounded_queries_and_no_transient_or_sensitive_data(
    tmp_path,
) -> None:
    repository = SessionRepository(tmp_path / "session.json")
    session = SessionState(
        last_knowledge_query="latest",
        recent_knowledge_queries=("latest", "latest", *map(str, range(30))),
        current_operation=OperationHandle("secret-operation-id", "analysis"),
    )

    repository.save(session)
    raw = repository.path.read_text(encoding="utf-8")
    loaded = repository.load().session

    assert loaded.recent_knowledge_queries[0] == "latest"
    assert len(loaded.recent_knowledge_queries) == 20
    assert len(set(loaded.recent_knowledge_queries)) == 20
    assert loaded.current_operation is None
    assert "secret-operation-id" not in raw
    assert "settings" not in raw
    assert "credential" not in raw
    assert "chunks" not in raw


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"schema_version": 999, "navigation": "overview"},
        {"schema_version": 2, "navigation": "not-a-page"},
        {"schema_version": 2, "navigation": "overview", "selected_audio": 42},
        {"schema_version": 2, "navigation": "overview", "selected_references": {}},
    ],
)
def test_invalid_schema_root_version_enum_or_types_recover_safely(tmp_path, payload) -> None:
    repository = SessionRepository(tmp_path / "session.json")
    repository.path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = repository.load()

    assert loaded.recovered_from_corruption
    assert loaded.session == SessionState()
    assert loaded.backup_path is not None and loaded.backup_path.exists()


def test_atomic_save_leaves_no_temporary_file(tmp_path) -> None:
    repository = SessionRepository(tmp_path / "state" / "session.json")

    repository.save(SessionState().navigate(PageId.SETTINGS))

    assert repository.load().session.navigation.current_page is PageId.SETTINGS
    assert list(repository.path.parent.glob("*.tmp")) == []


class _RecordingRepository:
    def __init__(self, *, failure: OSError | None = None) -> None:
        self.failure = failure
        self.saved: list[SessionState] = []

    def save(self, session: SessionState) -> None:
        if self.failure:
            raise self.failure
        self.saved.append(session)


def test_autosave_ignores_operation_only_changes_and_tracks_meaningful_session_changes(
    tmp_path,
) -> None:
    repository = _RecordingRepository()
    store = PresentationStore()
    binding = SessionPersistenceBinding(repository, store)  # type: ignore[arg-type]

    store.begin_operation(OperationHandle("operation-1", "analysis"))
    assert repository.saved == []

    store.select_audio(tmp_path / "selected.wav")
    assert repository.saved[-1].selected_audio == tmp_path / "selected.wav"
    binding.close()


def test_autosave_failure_is_structured_and_does_not_recurse_or_crash(tmp_path) -> None:
    repository = _RecordingRepository(failure=OSError("disk unavailable"))
    store = PresentationStore(PresentationState())
    binding = SessionPersistenceBinding(repository, store)  # type: ignore[arg-type]

    store.select_audio(tmp_path / "selected.wav")

    assert len(store.state.notifications.active) == 1
    error = store.state.notifications.active[0].error
    assert error is not None
    assert error.code == "session_persistence_failed"
    assert "disk unavailable" not in error.user_message
    assert store.state.session.selected_audio == tmp_path / "selected.wav"
    binding.close()
