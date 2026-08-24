from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from phasenox.ui.data_location import (
    DataRootAvailability,
    DataRootPointer,
    DataRootSource,
    data_root_pointer_path,
    desktop_state_locations,
    read_data_root_pointer,
    resolve_data_root,
    validate_data_root,
    write_data_root_pointer,
)


def test_known_desktop_locations_are_deterministic_and_qt_free(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")

    assert locations.legacy_root == tmp_path / "PHASENOX" / "soundbrain.desktop"
    assert locations.canonical_root == tmp_path / "PHASENOX" / "phasenox.desktop"
    assert locations.migration_lock == tmp_path / "PHASENOX" / ".desktop-state-migration.lock"
    assert not locations.organization_root.exists()


def test_pointer_round_trip_is_atomic_and_normalized(tmp_path: Path) -> None:
    canonical = tmp_path / "state-root"
    data_root = tmp_path / "data" / ".." / "data"
    path = data_root_pointer_path(canonical)
    pointer = DataRootPointer(data_root, DataRootSource.USER, datetime.now(UTC))

    write_data_root_pointer(path, pointer)
    loaded, error = read_data_root_pointer(path)

    assert error is None
    assert loaded is not None
    assert loaded.path == (tmp_path / "data").resolve()
    assert loaded.selection_source is DataRootSource.USER
    assert not tuple(path.parent.glob("*.tmp"))


@pytest.mark.parametrize("source", [DataRootSource.PHASENOX_ENVIRONMENT, DataRootSource.TEMPORARY])
def test_pointer_refuses_ephemeral_sources(tmp_path: Path, source: DataRootSource) -> None:
    pointer = DataRootPointer(tmp_path, source, datetime.now(UTC))

    with pytest.raises(ValueError, match="must not be persisted"):
        write_data_root_pointer(tmp_path / "pointer.json", pointer)


def test_pointer_read_is_bounded_and_read_only(tmp_path: Path) -> None:
    path = tmp_path / "data-root.json"
    path.write_bytes(b"x" * (16 * 1024 + 1))
    before = path.read_bytes()

    pointer, error = read_data_root_pointer(path)

    assert pointer is None
    assert error == "pointer_too_large"
    assert path.read_bytes() == before


def test_precedence_and_conflicts_do_not_rewrite_pointer(tmp_path: Path) -> None:
    canonical_root = tmp_path / "canonical-data"
    pointer_root = tmp_path / "pointer-data"
    legacy_root = tmp_path / "legacy-data"
    for root in (canonical_root, pointer_root, legacy_root):
        root.mkdir()
    pointer_path = tmp_path / "state" / "data-root.json"
    write_data_root_pointer(
        pointer_path,
        DataRootPointer(pointer_root, DataRootSource.USER, datetime.now(UTC)),
    )
    pointer_bytes = pointer_path.read_bytes()

    resolution = resolve_data_root(
        pointer_path=pointer_path,
        environ={"PHASENOX_ROOT": str(canonical_root), "NOISYNE_ROOT": str(legacy_root)},
    )

    assert resolution.selection.path == canonical_root.resolve()
    assert resolution.selection.source is DataRootSource.PHASENOX_ENVIRONMENT
    assert resolution.selection.availability is DataRootAvailability.AVAILABLE
    assert resolution.conflicts == (
        f"pointer={pointer_root.resolve()}",
        f"noisyne_environment={legacy_root.resolve()}",
    )
    assert pointer_path.read_bytes() == pointer_bytes


def test_pointer_wins_over_legacy_environment_fallbacks(tmp_path: Path) -> None:
    pointer_root = tmp_path / "pointer"
    noisyne_root = tmp_path / "noisyne"
    soundbrain_root = tmp_path / "soundbrain"
    for root in (pointer_root, noisyne_root, soundbrain_root):
        root.mkdir()
    pointer_path = tmp_path / "data-root.json"
    write_data_root_pointer(
        pointer_path,
        DataRootPointer(pointer_root, DataRootSource.INSTALLER, datetime.now(UTC)),
    )

    result = resolve_data_root(
        pointer_path=pointer_path,
        environ={
            "NOISYNE_ROOT": str(noisyne_root),
            "SOUNDBRAIN_ROOT": str(soundbrain_root),
        },
    )

    assert result.selection.path == pointer_root.resolve()
    assert result.selection.source is DataRootSource.POINTER
    assert result.selection.pointer_source is DataRootSource.INSTALLER


@pytest.mark.parametrize(
    ("environment", "expected_source"),
    [
        ({"NOISYNE_ROOT": "{root}"}, DataRootSource.NOISYNE_ENVIRONMENT),
        ({"SOUNDBRAIN_ROOT": "{root}"}, DataRootSource.SOUNDBRAIN_ENVIRONMENT),
    ],
)
def test_legacy_environment_fallbacks(
    tmp_path: Path,
    environment: dict[str, str],
    expected_source: DataRootSource,
) -> None:
    root = tmp_path / "legacy"
    root.mkdir()
    values = {key: value.format(root=root) for key, value in environment.items()}

    result = resolve_data_root(pointer_path=tmp_path / "missing.json", environ=values)

    assert result.selection.path == root.resolve()
    assert result.selection.source is expected_source
    assert result.selection.persistent_backend_enabled


def test_unavailable_root_never_creates_or_falls_back(tmp_path: Path) -> None:
    missing = tmp_path / "offline-drive" / "data"

    result = resolve_data_root(
        pointer_path=tmp_path / "missing-pointer.json",
        environ={"PHASENOX_ROOT": str(missing)},
    )

    assert result.status_code == "DATA_LOCATION_UNAVAILABLE"
    assert result.selection.path == missing.resolve()
    assert result.selection.availability is DataRootAvailability.UNAVAILABLE
    assert not missing.exists()
    assert str(result.selection.path).startswith(str(tmp_path))
    assert len(result.recovery_intents) == 4


def test_file_is_not_accepted_as_data_root(tmp_path: Path) -> None:
    path = tmp_path / "not-a-directory"
    path.write_text("data", encoding="utf-8")

    assert validate_data_root(path) is DataRootAvailability.NOT_DIRECTORY


def test_legacy_packaged_root_is_preserved_without_creation(tmp_path: Path) -> None:
    legacy = tmp_path / "PHASENOX" / "soundbrain.desktop"
    legacy.mkdir(parents=True)

    result = resolve_data_root(
        pointer_path=tmp_path / "missing.json",
        environ={},
        legacy_upgrade_root=legacy,
    )

    assert result.selection.path == legacy.resolve()
    assert result.selection.source is DataRootSource.LEGACY_UPGRADE
    assert result.selection.legacy_upgrade_compatibility
    assert tuple(legacy.iterdir()) == ()


def test_temporary_mode_has_no_path_or_persistent_backend(tmp_path: Path) -> None:
    result = resolve_data_root(
        pointer_path=tmp_path / "missing.json",
        environ=os.environ,
        temporary=True,
    )

    assert result.status_code == "TEMPORARY_SESSION"
    assert result.selection.path is None
    assert not result.selection.persistent_backend_enabled
    assert not (tmp_path / "missing.json").exists()


def test_malformed_pointer_is_reported_without_mutation(tmp_path: Path) -> None:
    pointer_path = tmp_path / "data-root.json"
    payload = {"schema_version": 99, "path": str(tmp_path), "selection_source": "user"}
    pointer_path.write_text(json.dumps(payload), encoding="utf-8")
    before = pointer_path.read_bytes()

    result = resolve_data_root(pointer_path=pointer_path, environ={})

    assert result.status_code == "DATA_LOCATION_UNAVAILABLE"
    assert result.pointer_error is not None
    assert pointer_path.read_bytes() == before
