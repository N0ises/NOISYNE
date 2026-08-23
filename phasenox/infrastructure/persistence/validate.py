"""Validation for persistence inventories and deterministic manifests."""

from __future__ import annotations

from dataclasses import dataclass

from .inventory import PersistenceInventory, StoreInventory
from .manifest import PersistenceManifest


@dataclass(frozen=True, slots=True, order=True)
class ValidationIssue:
    code: str
    location: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "location": self.location,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "issues": [issue.to_dict() for issue in self.issues],
            "ok": self.ok,
        }


def validate_store_availability(inventory: PersistenceInventory) -> ValidationReport:
    """Report missing and unreadable stores without attempting repair."""
    issues = []
    for store in inventory.stores:
        if not store.exists:
            issues.append(
                ValidationIssue(
                    "missing_store",
                    str(store.path),
                    f"{store.name} does not exist",
                )
            )
        elif not store.available:
            issues.append(
                ValidationIssue(
                    "store_unavailable",
                    str(store.path),
                    store.error or f"{store.name} is unavailable",
                )
            )
    return _report(issues)


def compare_manifests(
    expected: PersistenceManifest,
    actual: PersistenceManifest,
) -> ValidationReport:
    """Compare store availability, files, collections, roots, and versions."""
    issues: list[ValidationIssue] = []
    if expected.inventory.active_root != actual.inventory.active_root:
        issues.append(
            ValidationIssue(
                "changed_root",
                str(actual.inventory.active_root),
                f"expected active root {expected.inventory.active_root}",
            )
        )

    for name in sorted(set(expected.inventory.versions) | set(actual.inventory.versions)):
        before = expected.inventory.versions.get(name)
        after = actual.inventory.versions.get(name)
        if before != after:
            issues.append(
                ValidationIssue(
                    "changed_version",
                    name,
                    f"expected {before!r}, found {after!r}",
                )
            )

    expected_stores = {store.name: store for store in expected.inventory.stores}
    actual_stores = {store.name: store for store in actual.inventory.stores}
    for name in sorted(set(expected_stores) | set(actual_stores)):
        before = expected_stores.get(name)
        after = actual_stores.get(name)
        if before is None:
            issues.append(ValidationIssue("unexpected_store", name, "store was not in manifest"))
            continue
        if after is None or not after.exists:
            issues.append(ValidationIssue("missing_store", str(before.path), f"{name} is missing"))
            continue
        if not after.available:
            issues.append(
                ValidationIssue(
                    "store_unavailable",
                    str(after.path),
                    after.error or f"{name} is unavailable",
                )
            )
        _compare_store(before, after, issues)
    return _report(issues)


def _compare_store(
    expected: StoreInventory,
    actual: StoreInventory,
    issues: list[ValidationIssue],
) -> None:
    if expected.path != actual.path:
        issues.append(
            ValidationIssue(
                "changed_store_path",
                actual.name,
                f"expected {expected.path}, found {actual.path}",
            )
        )

    expected_files = {item.relative_path: item for item in expected.files}
    actual_files = {item.relative_path: item for item in actual.files}
    for relative_path in sorted(set(expected_files) | set(actual_files)):
        before = expected_files.get(relative_path)
        after = actual_files.get(relative_path)
        location = str(actual.path / relative_path)
        if before is None:
            issues.append(ValidationIssue("unexpected_file", location, "file was not in manifest"))
        elif after is None:
            issues.append(ValidationIssue("missing_file", location, "manifest file is missing"))
        elif (
            before.sha256 != after.sha256
            or before.size_bytes != after.size_bytes
            or before.kind != after.kind
        ):
            issues.append(ValidationIssue("changed_file", location, "file content or type changed"))
        elif before.modified_ns != after.modified_ns:
            issues.append(ValidationIssue("changed_timestamp", location, "file timestamp changed"))

    expected_collections = {item.name: item.to_dict() for item in expected.collections}
    actual_collections = {item.name: item.to_dict() for item in actual.collections}
    for name in sorted(set(expected_collections) | set(actual_collections)):
        location = f"{actual.name}:{name}"
        if name not in expected_collections:
            issues.append(
                ValidationIssue("unexpected_collection", location, "collection was not in manifest")
            )
        elif name not in actual_collections:
            issues.append(ValidationIssue("missing_collection", location, "collection is missing"))
        elif expected_collections[name] != actual_collections[name]:
            issues.append(
                ValidationIssue(
                    "changed_collection", location, "collection metadata or count changed"
                )
            )

    if expected.metadata != actual.metadata:
        issues.append(
            ValidationIssue(
                "changed_store_metadata",
                actual.name,
                "store metadata changed",
            )
        )


def _report(issues: list[ValidationIssue]) -> ValidationReport:
    return ValidationReport(issues=tuple(sorted(set(issues))))


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "compare_manifests",
    "validate_store_availability",
]
