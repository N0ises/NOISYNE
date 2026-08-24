from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from phasenox.ui.data_location import (
    DataRootPointer,
    DataRootSource,
    InstallerDataRootHandoff,
    data_root_pointer_path,
    desktop_state_locations,
    installer_handoff_path,
    read_data_root_pointer,
    read_installer_handoff,
    write_data_root_pointer,
    write_installer_handoff,
)
from phasenox.ui.first_launch import DataRootConfirmation, commit_data_root_confirmation
from phasenox.ui.startup import DesktopStartupMode, prepare_desktop_startup


def test_installer_handoff_round_trip_does_not_create_or_select_candidate(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "Local AppData" / "PHASENOX")
    candidate = tmp_path / "E drive" / "PHASENOX Data"
    path = installer_handoff_path(locations.canonical_root)

    write_installer_handoff(
        path,
        InstallerDataRootHandoff(candidate, "1.0.0", datetime(2026, 8, 23, tzinfo=UTC)),
    )
    loaded, error = read_installer_handoff(path)

    assert error is None
    assert loaded is not None
    assert loaded.candidate_path == candidate.resolve()
    assert loaded.installer_version == "1.0.0"
    assert not candidate.exists()
    assert not data_root_pointer_path(locations.canonical_root).exists()


def test_confirmed_installer_candidate_commits_pointer_then_consumes_handoff(
    tmp_path: Path,
) -> None:
    locations = desktop_state_locations(tmp_path / "Local AppData" / "PHASENOX")
    candidate = tmp_path / "Data" / "PHASENOX Data"
    handoff_path = installer_handoff_path(locations.canonical_root)
    write_installer_handoff(
        handoff_path,
        InstallerDataRootHandoff(candidate, "1.0.0", datetime.now(UTC)),
    )
    current = prepare_desktop_startup(
        application_version="1.0.0",
        locations=locations,
        environ={},
        frozen=True,
    )

    resolved = commit_data_root_confirmation(
        current,
        DataRootConfirmation(candidate, True, DataRootSource.INSTALLER),
        application_version="1.0.0",
    )

    assert resolved.mode is DesktopStartupMode.PERSISTENT
    assert candidate.is_dir()
    pointer, error = read_data_root_pointer(data_root_pointer_path(locations.canonical_root))
    assert error is None
    assert pointer is not None
    assert pointer.path == candidate.resolve()
    assert pointer.selection_source is DataRootSource.INSTALLER
    assert not handoff_path.exists()


def test_unconfirmed_or_unavailable_candidate_preserves_existing_pointer_bytes(
    tmp_path: Path,
) -> None:
    locations = desktop_state_locations(tmp_path / "Local AppData" / "PHASENOX")
    unavailable = tmp_path / "offline" / "old data"
    pointer_path = data_root_pointer_path(locations.canonical_root)
    write_data_root_pointer(
        pointer_path,
        DataRootPointer(unavailable, DataRootSource.USER, datetime.now(UTC)),
    )
    before = pointer_path.read_bytes()
    candidate = tmp_path / "missing replacement"
    current = prepare_desktop_startup(
        application_version="1.0.0",
        locations=locations,
        environ={},
        frozen=True,
    )

    with pytest.raises(ValueError, match="unavailable"):
        commit_data_root_confirmation(
            current,
            DataRootConfirmation(candidate, False, DataRootSource.USER),
            application_version="1.0.0",
        )

    assert current.mode is DesktopStartupMode.RECOVERY_REQUIRED
    assert pointer_path.read_bytes() == before
    assert not candidate.exists()


def test_environment_selected_unavailable_root_cannot_be_replaced_by_handoff(
    tmp_path: Path,
) -> None:
    locations = desktop_state_locations(tmp_path / "Local AppData" / "PHASENOX")
    environment_root = tmp_path / "offline environment root"
    candidate = tmp_path / "installer candidate"
    candidate.mkdir()
    write_installer_handoff(
        installer_handoff_path(locations.canonical_root),
        InstallerDataRootHandoff(candidate, "1.0.0", datetime.now(UTC)),
    )

    current = prepare_desktop_startup(
        application_version="1.0.0",
        locations=locations,
        environ={"PHASENOX_ROOT": str(environment_root)},
        frozen=True,
    )

    assert current.mode is DesktopStartupMode.RECOVERY_REQUIRED
    assert current.data_root.selection.source is DataRootSource.PHASENOX_ENVIRONMENT
    assert not data_root_pointer_path(locations.canonical_root).exists()
