from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QStandardPaths

from phasenox.ui.app import create_application
from phasenox.ui.branding import default_product_metadata
from phasenox.ui.data_location import (
    DataRootSource,
    data_root_pointer_path,
    desktop_state_locations,
    read_data_root_pointer,
)
from phasenox.ui.identity_migration import session_path
from phasenox.ui.logging_setup import configure_logging
from phasenox.ui.startup import (
    DesktopStartupMode,
    SessionChoice,
    activate_backend_root,
    prepare_desktop_startup,
)


def _session(page: str = "overview") -> bytes:
    return json.dumps({"schema_version": 2, "navigation": page}).encode()


def _write_session(root: Path, raw: bytes | None = None) -> Path:
    path = session_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw or _session())
    return path


def test_canonical_qt_identity_and_app_local_data_path(qapp) -> None:
    application = create_application(default_product_metadata())

    assert application.applicationName() == "phasenox.desktop"
    assert application.applicationDisplayName() == "PHASENØX"
    assert application.organizationName() == "PHASENOX"
    assert Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)).parts[
        -2:
    ] == ("PHASENOX", "phasenox.desktop")


def test_packaged_upgrade_preserves_exact_legacy_backend_root(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")
    source = _write_session(locations.legacy_root)
    backend_sentinel = locations.legacy_root / "data" / "index.db"
    backend_sentinel.parent.mkdir(parents=True)
    backend_sentinel.write_bytes(b"do-not-open-or-move")
    before = backend_sentinel.read_bytes()

    result = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ={},
        frozen=True,
    )

    assert result.mode is DesktopStartupMode.PERSISTENT
    assert result.data_root.selection.path == locations.legacy_root.resolve()
    assert result.data_root.selection.source is DataRootSource.LEGACY_UPGRADE
    assert source.read_bytes() == _session()
    assert backend_sentinel.read_bytes() == before
    assert not (locations.canonical_root / "data").exists()
    pointer, error = read_data_root_pointer(data_root_pointer_path(locations.canonical_root))
    assert error is None
    assert pointer is not None
    assert pointer.path == locations.legacy_root.resolve()
    assert pointer.selection_source is DataRootSource.LEGACY_UPGRADE


def test_clean_first_launch_requires_selection_without_creating_state(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")

    result = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ={},
        frozen=True,
    )

    assert result.mode is DesktopStartupMode.RECOVERY_REQUIRED
    assert result.data_root.status_code == "DATA_LOCATION_UNAVAILABLE"
    assert not locations.organization_root.exists()


def test_requested_existing_data_root_is_persisted_and_selected(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")
    data_root = tmp_path / "E-drive" / "PHASENOX Data"
    data_root.mkdir(parents=True)

    result = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ={},
        requested_data_root=data_root,
    )

    assert result.mode is DesktopStartupMode.PERSISTENT
    assert result.data_root.selection.path == data_root.resolve()
    assert result.data_root.selection.source is DataRootSource.POINTER
    pointer, _error = read_data_root_pointer(data_root_pointer_path(locations.canonical_root))
    assert pointer is not None and pointer.selection_source is DataRootSource.USER


def test_unavailable_selected_root_blocks_activation_without_fallback(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")
    missing = tmp_path / "offline" / "data"

    result = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ={"PHASENOX_ROOT": str(missing)},
    )

    assert result.mode is DesktopStartupMode.RECOVERY_REQUIRED
    assert result.data_root.status_code == "DATA_LOCATION_UNAVAILABLE"
    assert not missing.exists()
    with pytest.raises(RuntimeError, match="available Data Root"):
        activate_backend_root(result, environ={})


def test_temporary_mode_is_read_only_and_never_exports_backend_root(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")
    _write_session(locations.legacy_root)
    before = {
        path: path.read_bytes() for path in locations.legacy_root.rglob("*") if path.is_file()
    }
    environment: dict[str, str] = {}

    result = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ=environment,
        temporary=True,
    )

    assert result.mode is DesktopStartupMode.TEMPORARY
    assert not result.backend_enabled
    assert environment == {}
    assert not locations.canonical_root.exists()
    assert {
        path: path.read_bytes() for path in locations.legacy_root.rglob("*") if path.is_file()
    } == before


def test_divergent_session_requires_explicit_choice(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")
    data_root = tmp_path / "data"
    data_root.mkdir()
    _write_session(locations.legacy_root, _session("overview"))
    _write_session(locations.canonical_root, _session("reports"))

    blocked = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ={"PHASENOX_ROOT": str(data_root)},
    )
    recovered = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ={"PHASENOX_ROOT": str(data_root)},
        session_choice=SessionChoice.LEGACY,
    )

    assert blocked.mode is DesktopStartupMode.RECOVERY_REQUIRED
    assert recovered.mode is DesktopStartupMode.PERSISTENT
    assert recovered.active_session_path == session_path(locations.legacy_root)


def test_backend_root_is_exported_only_after_persistent_resolution(tmp_path: Path) -> None:
    locations = desktop_state_locations(tmp_path / "PHASENOX")
    data_root = tmp_path / "data"
    data_root.mkdir()
    environment: dict[str, str] = {"PHASENOX_ROOT": str(data_root)}
    result = prepare_desktop_startup(
        application_version="1.0",
        locations=locations,
        environ=environment,
    )
    activated: dict[str, str] = {}

    selected = activate_backend_root(result, environ=activated)

    assert selected == data_root.resolve()
    assert activated == {"PHASENOX_ROOT": str(data_root.resolve())}


def test_prebootstrap_does_not_import_backend_config_or_store_clients(tmp_path: Path) -> None:
    repository = Path(__file__).parents[2]
    code = """
import json
import sys
from pathlib import Path
from phasenox.ui.data_location import desktop_state_locations
from phasenox.ui.startup import prepare_desktop_startup
root = Path(sys.argv[1])
result = prepare_desktop_startup(
    application_version='1.0',
    locations=desktop_state_locations(root / 'PHASENOX'),
    environ={},
    temporary=True,
)
names = ('phasenox.infrastructure.config', 'chromadb', 'sqlite3', 'torch', 'transformers')
print(json.dumps({'mode': result.mode.value, **{name: name in sys.modules for name in names}}))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository)

    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "mode": "temporary",
        "phasenox.infrastructure.config": False,
        "chromadb": False,
        "sqlite3": False,
        "torch": False,
        "transformers": False,
    }


def test_logging_uses_canonical_root_and_leaves_legacy_log_unchanged(tmp_path: Path) -> None:
    canonical = tmp_path / "phasenox.desktop"
    legacy_log = tmp_path / "soundbrain.desktop" / "logs" / "desktop.log"
    legacy_log.parent.mkdir(parents=True)
    legacy_log.write_bytes(b"legacy-log")
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    for handler in original_handlers:
        root_logger.removeHandler(handler)
    try:
        log_path = configure_logging(canonical)
        logging.getLogger("test").warning("canonical message")
        for handler in root_logger.handlers:
            handler.flush()

        assert log_path == canonical / "logs" / "desktop.log"
        assert log_path.is_file()
        assert legacy_log.read_bytes() == b"legacy-log"
        desktop_handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, "_desktop_handler", False)
        ]
        assert desktop_handlers[0].maxBytes == 5 * 1024 * 1024
        assert desktop_handlers[0].backupCount == 3
    finally:
        for handler in list(root_logger.handlers):
            if getattr(handler, "_desktop_handler", False):
                handler.close()
                root_logger.removeHandler(handler)
        for handler in original_handlers:
            root_logger.addHandler(handler)
