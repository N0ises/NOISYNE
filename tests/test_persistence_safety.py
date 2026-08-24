from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from phasenox.infrastructure.persistence import (
    BackupStrategy,
    MigrationLock,
    MigrationLockHeldError,
    collect_persistence_inventory,
    compare_manifests,
    create_backup_plan,
    create_manifest,
    manifest_payload_from_json,
    read_migration_lock,
    validate_store_availability,
    write_manifest,
)

TEST_VERSIONS = {
    "chromadb": "test-chroma",
    "phasenox": "test-phasenox",
    "python": "test-python",
    "sqlite": "test-sqlite",
}


def _schema(space: str = "cosine") -> str:
    return json.dumps(
        {
            "keys": {
                "#embedding": {
                    "float_list": {
                        "vector_index": {
                            "config": {
                                "embedding_function": {"type": "legacy"},
                                "space": space,
                            }
                        }
                    }
                }
            }
        }
    )


def _create_fake_chroma(
    path: Path,
    collections: list[tuple[str, int, int]],
) -> None:
    path.mkdir(parents=True)
    database = path / "chroma.sqlite3"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executescript("""
            CREATE TABLE collections(
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                dimension INTEGER,
                config_json_str TEXT,
                schema_str TEXT
            );
            CREATE TABLE segments(
                id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                collection TEXT NOT NULL
            );
            CREATE TABLE embeddings(
                id INTEGER PRIMARY KEY,
                segment_id TEXT NOT NULL,
                embedding_id TEXT NOT NULL
            );
            CREATE TABLE collection_metadata(
                collection_id TEXT NOT NULL,
                key TEXT NOT NULL,
                str_value TEXT,
                int_value INTEGER,
                float_value REAL,
                bool_value INTEGER
            );
            """)
        embedding_id = 0
        for index, (name, dimension, count) in enumerate(collections):
            collection_id = f"collection-{index}"
            segment_id = f"segment-{index}"
            connection.execute(
                "INSERT INTO collections VALUES (?, ?, ?, ?, ?)",
                (collection_id, name, dimension, "{}", _schema()),
            )
            connection.execute(
                "INSERT INTO segments VALUES (?, 'METADATA', ?)",
                (segment_id, collection_id),
            )
            for _ in range(count):
                embedding_id += 1
                connection.execute(
                    "INSERT INTO embeddings VALUES (?, ?, ?)",
                    (embedding_id, segment_id, f"record-{embedding_id}"),
                )

    segment = path / "segment-files"
    segment.mkdir()
    (segment / "header.bin").write_bytes(b"fake-hnsw-header")


def _create_fake_catalog(path: Path, count: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("""
            CREATE TABLE indexed_audio(
                file_hash TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                modified_time REAL NOT NULL,
                embedding_model TEXT NOT NULL
            )
            """)
        for index in range(count):
            connection.execute(
                "INSERT INTO indexed_audio VALUES (?, ?, ?, ?)",
                (f"hash-{index}", f"audio-{index}.wav", float(index), "clap"),
            )


@pytest.fixture
def fake_root(tmp_path: Path) -> Path:
    root = tmp_path / "application-root"
    _create_fake_chroma(root / "data" / "chroma", [("soundbrain", 1024, 3)])
    _create_fake_chroma(
        root / "data" / "vector_db",
        [("audio_clap_512", 512, 2), ("soundbrain", 1024, 1)],
    )
    _create_fake_catalog(root / "data" / "index.db")
    return root


def _store(inventory, name: str):
    return next(store for store in inventory.stores if store.name == name)


def _content_snapshot(root: Path) -> dict[str, tuple[int, bytes]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_mtime_ns, path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_inventory_discovers_fake_stores_without_modifying_them(fake_root: Path) -> None:
    before = _content_snapshot(fake_root)

    inventory = collect_persistence_inventory(fake_root, versions=TEST_VERSIONS)

    assert inventory.active_root == fake_root.resolve()
    assert inventory.versions == TEST_VERSIONS
    assert validate_store_availability(inventory).ok

    rag = _store(inventory, "rag_chroma")
    assert rag.path == fake_root.resolve() / "data" / "chroma"
    assert rag.available
    assert [(item.name, item.record_count) for item in rag.collections] == [("soundbrain", 3)]
    assert rag.collections[0].dimension == 1024
    assert rag.collections[0].distance_space == "cosine"
    assert rag.version == "test-chroma"
    assert rag.size_bytes == sum(item.size_bytes for item in rag.files)

    memory = _store(inventory, "memory_vector")
    assert [(item.name, item.record_count) for item in memory.collections] == [
        ("audio_clap_512", 2),
        ("soundbrain", 1),
    ]

    catalog = _store(inventory, "sqlite_catalog")
    assert catalog.metadata["indexed_audio_count"] == 2
    assert catalog.metadata["sqlite_user_version"] == 0
    assert (
        catalog.files[0].sha256
        == hashlib.sha256((fake_root / "data" / "index.db").read_bytes()).hexdigest()
    )

    assert _content_snapshot(fake_root) == before
    catalog_path = fake_root / "data" / "index.db"
    moved_catalog = catalog_path.with_suffix(".moved")
    catalog_path.rename(moved_catalog)
    moved_catalog.rename(catalog_path)


def test_manifest_json_is_deterministic_and_self_verifying(fake_root: Path) -> None:
    inventory = collect_persistence_inventory(fake_root, versions=TEST_VERSIONS)
    first = create_manifest(inventory)
    second = create_manifest(inventory)

    assert first.to_json() == second.to_json()
    assert first.manifest_sha256 == second.manifest_sha256
    payload = manifest_payload_from_json(first.to_json())
    assert payload["manifest_sha256"] == first.manifest_sha256
    assert "modified_at" in payload["inventory"]["stores"][0]["files"][0]
    assert payload["inventory"]["stores"][0]["collections"][0]["name"] == "soundbrain"


def test_manifest_writer_uses_only_explicit_destination(fake_root: Path, tmp_path: Path) -> None:
    manifest = create_manifest(collect_persistence_inventory(fake_root, versions=TEST_VERSIONS))
    target = tmp_path / "manifest.json"

    assert write_manifest(manifest, target) == target
    assert target.read_text(encoding="utf-8") == manifest.to_json()
    assert manifest_payload_from_json(target.read_text(encoding="utf-8"))
    with pytest.raises(FileExistsError):
        write_manifest(manifest, target)


def test_manifest_validation_reports_changed_and_missing_files(fake_root: Path) -> None:
    expected = create_manifest(collect_persistence_inventory(fake_root, versions=TEST_VERSIONS))
    changed = fake_root / "data" / "chroma" / "segment-files" / "header.bin"
    missing = fake_root / "data" / "vector_db" / "segment-files" / "header.bin"
    changed.write_bytes(b"changed-fake-header")
    missing.unlink()
    actual = create_manifest(collect_persistence_inventory(fake_root, versions=TEST_VERSIONS))

    report = compare_manifests(expected, actual)

    assert not report.ok
    assert {issue.code for issue in report.issues} >= {"changed_file", "missing_file"}
    assert all(str(fake_root) in issue.location for issue in report.issues)


def test_store_availability_reports_missing_and_corrupt_stores(tmp_path: Path) -> None:
    root = tmp_path / "application-root"
    corrupt = root / "data" / "chroma"
    corrupt.mkdir(parents=True)
    (corrupt / "chroma.sqlite3").write_bytes(b"not a sqlite database")

    inventory = collect_persistence_inventory(root, versions=TEST_VERSIONS)
    report = validate_store_availability(inventory)

    assert not report.ok
    assert {issue.code for issue in report.issues} == {
        "missing_store",
        "store_unavailable",
    }


def test_backup_plan_is_deterministic_and_does_not_execute(fake_root: Path, tmp_path: Path) -> None:
    manifest = create_manifest(collect_persistence_inventory(fake_root, versions=TEST_VERSIONS))
    destination = tmp_path / "backup-target"

    first = create_backup_plan(manifest, destination)
    second = create_backup_plan(manifest, destination)

    assert first == second
    assert first.plan_id == second.plan_id
    assert not destination.exists()
    assert {item.strategy for item in first.items} == {
        BackupStrategy.COLD_DIRECTORY_COPY,
        BackupStrategy.SQLITE_BACKUP_API,
    }
    assert {item.store_name for item in first.items} == {
        "rag_chroma",
        "memory_vector",
        "sqlite_catalog",
    }


def test_backup_plan_rejects_destination_inside_active_root(fake_root: Path) -> None:
    manifest = create_manifest(collect_persistence_inventory(fake_root, versions=TEST_VERSIONS))

    with pytest.raises(ValueError, match="outside the active application root"):
        create_backup_plan(manifest, fake_root / "backup")


def test_migration_lock_is_explicit_exclusive_and_releasable(tmp_path: Path) -> None:
    path = tmp_path / ".phasenox-migration.lock"
    fixed_time = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    lock = MigrationLock(
        path,
        token_factory=lambda: "owner-token",
        clock=lambda: fixed_time,
    )

    with lock:
        assert lock.acquired
        assert read_migration_lock(path).token == "owner-token"
        contender = MigrationLock(path, token_factory=lambda: "contender")
        with pytest.raises(MigrationLockHeldError):
            contender.acquire()

    assert not lock.acquired
    assert not path.exists()
    assert read_migration_lock(path) is None


def test_persistence_package_import_does_not_initialize_store_clients() -> None:
    assert "phasenox.rag.vectordb" not in sys.modules
    assert "phasenox.memory.vector.providers.chroma" not in sys.modules
