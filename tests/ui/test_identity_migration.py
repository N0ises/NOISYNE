from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from phasenox.ui.data_location import desktop_state_locations
from phasenox.ui.identity_migration import (
    MigrationLock,
    SessionFileStatus,
    SessionMigrationDecision,
    adopt_identical_sessions,
    execute_session_migration,
    inspect_session,
    migration_marker_path,
    plan_session_migration,
    read_migration_marker,
    session_path,
)


def _session_bytes(*, schema: int = 2, page: str = "overview", pretty: bool = False) -> bytes:
    payload = {"schema_version": schema, "navigation": page}
    if pretty:
        return (json.dumps(payload, indent=2) + "\n").encode()
    return json.dumps(payload, separators=(",", ":")).encode()


def _write_session(root: Path, raw: bytes) -> Path:
    path = session_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def _locations(tmp_path: Path):
    return desktop_state_locations(tmp_path / "PHASENOX")


def test_neither_session_is_clean_first_launch_without_writes(tmp_path: Path) -> None:
    locations = _locations(tmp_path)

    plan = plan_session_migration(locations)

    assert plan.decision is SessionMigrationDecision.CLEAN_CANONICAL
    assert not locations.organization_root.exists()


@pytest.mark.parametrize("schema", [1, 2])
def test_legacy_only_session_copies_exact_bytes_and_preserves_source(
    tmp_path: Path, schema: int
) -> None:
    locations = _locations(tmp_path)
    raw = _session_bytes(schema=schema, pretty=True)
    source = _write_session(locations.legacy_root, raw)
    plan = plan_session_migration(locations)

    result = execute_session_migration(plan, locations, application_version="1.0")

    target = session_path(locations.canonical_root)
    assert result.decision is SessionMigrationDecision.USE_CANONICAL
    assert source.read_bytes() == raw
    assert target.read_bytes() == raw
    marker, error = read_migration_marker(migration_marker_path(locations.canonical_root))
    assert error is None
    assert marker is not None and marker.status == "completed"
    assert marker.source_session_sha256 == marker.target_session_sha256
    assert not locations.migration_lock.exists()


def test_canonical_only_is_used_without_creating_legacy(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    target = _write_session(locations.canonical_root, _session_bytes())

    plan = plan_session_migration(locations)

    assert plan.decision is SessionMigrationDecision.USE_CANONICAL
    assert target.is_file()
    assert not locations.legacy_root.exists()


def test_identical_dual_sessions_are_adopted_and_idempotent(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    raw = _session_bytes(pretty=True)
    _write_session(locations.legacy_root, raw)
    _write_session(locations.canonical_root, raw)

    plan = plan_session_migration(locations)
    adopted = adopt_identical_sessions(plan, locations, application_version="1.0")
    rerun = plan_session_migration(locations)

    assert adopted.decision is SessionMigrationDecision.USE_CANONICAL
    assert rerun.decision is SessionMigrationDecision.USE_CANONICAL


def test_semantically_equal_but_byte_different_requires_choice(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    _write_session(locations.legacy_root, _session_bytes(pretty=False))
    _write_session(locations.canonical_root, _session_bytes(pretty=True))

    plan = plan_session_migration(locations)

    assert plan.decision is SessionMigrationDecision.CHOICE_REQUIRED
    assert plan.requires_user_choice
    assert "semantically equal" in (plan.reason or "")


def test_divergent_dual_sessions_require_choice_without_mutation(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    legacy = _write_session(locations.legacy_root, _session_bytes(page="overview"))
    canonical = _write_session(locations.canonical_root, _session_bytes(page="analyze"))
    before = (legacy.read_bytes(), canonical.read_bytes())

    plan = plan_session_migration(locations)

    assert plan.decision is SessionMigrationDecision.CHOICE_REQUIRED
    assert "diverge" in (plan.reason or "")
    assert (legacy.read_bytes(), canonical.read_bytes()) == before


def test_corrupt_legacy_is_preserved_without_quarantine(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    source = _write_session(locations.legacy_root, b"not-json")

    plan = plan_session_migration(locations)

    assert plan.decision is SessionMigrationDecision.SAFE_DEFAULT_REQUIRED
    assert plan.legacy.status is SessionFileStatus.CORRUPT
    assert source.read_bytes() == b"not-json"
    assert list(source.parent.iterdir()) == [source]


def test_corrupt_canonical_is_never_overwritten_automatically(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    _write_session(locations.legacy_root, _session_bytes())
    target = _write_session(locations.canonical_root, b"partial")

    plan = plan_session_migration(locations)

    assert plan.decision is SessionMigrationDecision.CHOICE_REQUIRED
    assert target.read_bytes() == b"partial"


def test_started_marker_resumes_only_when_source_hash_is_unchanged(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    _write_session(locations.legacy_root, _session_bytes())
    initial = plan_session_migration(locations)
    marker_path = migration_marker_path(locations.canonical_root)
    marker_path.parent.mkdir(parents=True)
    marker_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "started",
                "source_identity": "soundbrain.desktop",
                "target_identity": "phasenox.desktop",
                "source_path": str(initial.legacy.path),
                "target_path": str(initial.canonical.path),
                "source_session_sha256": initial.legacy.sha256,
                "target_session_sha256": None,
                "started_at": "2026-01-01T00:00:00+00:00",
                "completed_at": None,
                "application_version": "1.0",
            }
        ),
        encoding="utf-8",
    )

    assert plan_session_migration(locations).decision is SessionMigrationDecision.RESUME_MIGRATION
    _write_session(locations.legacy_root, _session_bytes(page="analyze"))
    changed = plan_session_migration(locations)
    assert changed.decision is SessionMigrationDecision.CHOICE_REQUIRED
    assert "changed" in (changed.reason or "")


def test_source_change_after_plan_aborts_without_target(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    source = _write_session(locations.legacy_root, _session_bytes())
    plan = plan_session_migration(locations)
    source.write_bytes(_session_bytes(page="reports"))

    with pytest.raises(RuntimeError, match="changed"):
        execute_session_migration(plan, locations, application_version="1.0")

    assert not session_path(locations.canonical_root).exists()


def test_existing_target_is_never_overwritten(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    _write_session(locations.legacy_root, _session_bytes())
    plan = plan_session_migration(locations)
    target = _write_session(locations.canonical_root, _session_bytes(page="reports"))

    with pytest.raises(FileExistsError, match="already exists"):
        execute_session_migration(plan, locations, application_version="1.0")

    assert target.read_bytes() == _session_bytes(page="reports")


def test_missing_referenced_files_remain_a_valid_session(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    payload = {
        "schema_version": 2,
        "navigation": "overview",
        "selected_audio": str(tmp_path / "missing.wav"),
        "selected_references": [str(tmp_path / "missing-reference.wav")],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspected = inspect_session(path)

    assert inspected.status is SessionFileStatus.VALID
    assert inspected.session is not None
    assert inspected.session.selected_audio == tmp_path / "missing.wav"


def test_oversized_session_is_corrupt_but_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_bytes(b" " * (1024 * 1024 + 1))

    inspected = inspect_session(path)

    assert inspected.status is SessionFileStatus.CORRUPT
    assert path.stat().st_size == 1024 * 1024 + 1


def test_migration_lock_rejects_concurrent_holder_and_recovers_stale_lock(
    tmp_path: Path,
) -> None:
    path = tmp_path / "organization" / ".lock"
    first = MigrationLock(path)
    first.acquire()
    with pytest.raises(RuntimeError, match="in progress"):
        MigrationLock(path).acquire()
    first.release()

    path.write_text("stale", encoding="utf-8")
    os.utime(path, (0, 0))
    with MigrationLock(path, stale_after_seconds=1):
        assert path.exists()
    assert not path.exists()
