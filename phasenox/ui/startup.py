"""Pre-backend Desktop startup orchestration."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from .data_location import (
    DataRootAvailability,
    DataRootPointer,
    DataRootResolution,
    DataRootSource,
    DesktopStateLocations,
    RecoveryIntent,
    data_root_pointer_path,
    desktop_state_locations,
    normalize_path,
    resolve_data_root,
    validate_data_root,
    write_data_root_pointer,
)
from .identity_migration import (
    SessionMigrationDecision,
    SessionMigrationPlan,
    adopt_identical_sessions,
    execute_session_migration,
    plan_session_migration,
    session_path,
)


class DesktopStartupMode(StrEnum):
    PERSISTENT = "persistent"
    TEMPORARY = "temporary"
    RECOVERY_REQUIRED = "recovery_required"


class SessionChoice(StrEnum):
    LEGACY = "legacy"
    CANONICAL = "canonical"


@dataclass(frozen=True, slots=True)
class DesktopStartupResolution:
    mode: DesktopStartupMode
    locations: DesktopStateLocations
    data_root: DataRootResolution
    session_plan: SessionMigrationPlan
    active_session_path: Path | None
    reason: str | None = None
    recovery_intents: tuple[RecoveryIntent, ...] = ()

    @property
    def backend_enabled(self) -> bool:
        return self.mode is DesktopStartupMode.PERSISTENT


def prepare_desktop_startup(
    *,
    application_version: str,
    locations: DesktopStateLocations | None = None,
    environ: Mapping[str, str] | None = None,
    frozen: bool | None = None,
    requested_data_root: Path | None = None,
    temporary: bool = False,
    session_choice: SessionChoice | None = None,
) -> DesktopStartupResolution:
    """Resolve Data Root and small state before Qt identity/backend startup."""
    state_locations = locations or desktop_state_locations()
    environment = os.environ if environ is None else environ
    pointer_path = data_root_pointer_path(state_locations.canonical_root)

    if requested_data_root is not None:
        requested = normalize_path(requested_data_root)
        availability = validate_data_root(requested)
        if availability is not DataRootAvailability.AVAILABLE:
            data_root = resolve_data_root(
                pointer_path=pointer_path,
                environ={"PHASENOX_ROOT": str(requested)},
            )
            plan = plan_session_migration(state_locations)
            return DesktopStartupResolution(
                DesktopStartupMode.RECOVERY_REQUIRED,
                state_locations,
                data_root,
                plan,
                None,
                data_root.selection.reason_unavailable,
                data_root.recovery_intents,
            )
        write_data_root_pointer(
            pointer_path,
            DataRootPointer(requested, DataRootSource.USER, datetime.now(UTC)),
        )

    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    legacy_upgrade = (
        state_locations.legacy_root if is_frozen and state_locations.legacy_root.is_dir() else None
    )
    data_root = resolve_data_root(
        pointer_path=pointer_path,
        environ=environment,
        legacy_upgrade_root=legacy_upgrade,
        temporary=temporary,
    )
    if temporary:
        plan = plan_session_migration(state_locations)
        return DesktopStartupResolution(
            DesktopStartupMode.TEMPORARY,
            state_locations,
            data_root,
            plan,
            None,
            "Temporary session mode disables persistent backend services.",
        )
    if (
        data_root.selection.source is DataRootSource.LEGACY_UPGRADE
        and data_root.selection.persistent_backend_enabled
        and not pointer_path.exists()
    ):
        write_data_root_pointer(
            pointer_path,
            DataRootPointer(
                data_root.selection.path,
                DataRootSource.LEGACY_UPGRADE,
                datetime.now(UTC),
            ),
        )

    plan = plan_session_migration(state_locations)
    if plan.decision in {
        SessionMigrationDecision.MIGRATE_LEGACY,
        SessionMigrationDecision.RESUME_MIGRATION,
    }:
        plan = execute_session_migration(
            plan,
            state_locations,
            application_version=application_version,
        )
    elif plan.decision is SessionMigrationDecision.ADOPT_IDENTICAL:
        plan = adopt_identical_sessions(
            plan,
            state_locations,
            application_version=application_version,
        )

    active_session = _select_session_path(plan, state_locations, session_choice)
    if active_session is None:
        return DesktopStartupResolution(
            DesktopStartupMode.RECOVERY_REQUIRED,
            state_locations,
            data_root,
            plan,
            None,
            plan.reason,
            plan.recovery_intents,
        )
    if not data_root.selection.persistent_backend_enabled:
        return DesktopStartupResolution(
            DesktopStartupMode.RECOVERY_REQUIRED,
            state_locations,
            data_root,
            plan,
            active_session,
            data_root.selection.reason_unavailable or "A PHASENOX Data Root is required.",
            data_root.recovery_intents,
        )
    return DesktopStartupResolution(
        DesktopStartupMode.PERSISTENT,
        state_locations,
        data_root,
        plan,
        active_session,
    )


def activate_backend_root(
    resolution: DesktopStartupResolution,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> Path:
    """Export the validated root immediately before backend imports are allowed."""
    if not resolution.backend_enabled or resolution.data_root.selection.path is None:
        raise RuntimeError("Persistent backend activation requires an available Data Root.")
    values = os.environ if environ is None else environ
    path = resolution.data_root.selection.path
    values["PHASENOX_ROOT"] = str(path)
    return path


def _select_session_path(
    plan: SessionMigrationPlan,
    locations: DesktopStateLocations,
    choice: SessionChoice | None,
) -> Path | None:
    if choice is SessionChoice.LEGACY:
        return session_path(locations.legacy_root)
    if choice is SessionChoice.CANONICAL:
        return session_path(locations.canonical_root)
    if plan.requires_user_choice:
        return None
    return session_path(locations.canonical_root)


__all__ = [
    "DesktopStartupMode",
    "DesktopStartupResolution",
    "SessionChoice",
    "activate_backend_root",
    "prepare_desktop_startup",
]
