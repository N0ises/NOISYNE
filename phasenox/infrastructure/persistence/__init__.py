"""Persistence migration safety primitives.

This package does not initialize production stores or execute migrations.
"""

from .backup import BackupBackend, BackupItem, BackupPlan, BackupStrategy, create_backup_plan
from .inventory import (
    CollectionInventory,
    FileInventory,
    PersistenceInventory,
    PersistencePaths,
    StoreInventory,
    collect_persistence_inventory,
    discover_persistence_paths,
)
from .locking import (
    MigrationLock,
    MigrationLockError,
    MigrationLockHeldError,
    MigrationLockInfo,
    MigrationLockOwnershipError,
    read_migration_lock,
)
from .manifest import (
    MANIFEST_FORMAT_VERSION,
    PersistenceManifest,
    create_manifest,
    manifest_payload_from_json,
    write_manifest,
)
from .validate import (
    ValidationIssue,
    ValidationReport,
    compare_manifests,
    validate_store_availability,
)

__all__ = [
    "MANIFEST_FORMAT_VERSION",
    "BackupBackend",
    "BackupItem",
    "BackupPlan",
    "BackupStrategy",
    "CollectionInventory",
    "FileInventory",
    "MigrationLock",
    "MigrationLockError",
    "MigrationLockHeldError",
    "MigrationLockInfo",
    "MigrationLockOwnershipError",
    "PersistenceInventory",
    "PersistenceManifest",
    "PersistencePaths",
    "StoreInventory",
    "ValidationIssue",
    "ValidationReport",
    "collect_persistence_inventory",
    "compare_manifests",
    "create_backup_plan",
    "create_manifest",
    "discover_persistence_paths",
    "manifest_payload_from_json",
    "read_migration_lock",
    "validate_store_availability",
    "write_manifest",
]
