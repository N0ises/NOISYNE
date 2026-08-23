"""Read-only discovery of PHASENOX persistence stores."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata as importlib_metadata
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PersistencePaths:
    """Resolved persistence paths for one active application root."""

    active_root: Path
    rag_chroma: Path
    memory_vector: Path
    sqlite_catalog: Path


@dataclass(frozen=True, slots=True)
class FileInventory:
    """Immutable metadata for one store file or symbolic link."""

    relative_path: str
    kind: str
    size_bytes: int
    modified_ns: int
    modified_at: str
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "modified_at": self.modified_at,
            "modified_ns": self.modified_ns,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class CollectionInventory:
    """Safely readable metadata for one vector collection."""

    name: str
    record_count: int | None = None
    dimension: int | None = None
    distance_space: str | None = None
    embedding_function: object | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "distance_space": self.distance_space,
            "embedding_function": self.embedding_function,
            "metadata": {key: self.metadata[key] for key in sorted(self.metadata)},
            "name": self.name,
            "record_count": self.record_count,
        }


@dataclass(frozen=True, slots=True)
class StoreInventory:
    """Read-only inventory for one persistence store."""

    name: str
    kind: str
    path: Path
    exists: bool
    available: bool
    size_bytes: int
    version: str | None
    files: tuple[FileInventory, ...] = ()
    collections: tuple[CollectionInventory, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "collections": [collection.to_dict() for collection in self.collections],
            "error": self.error,
            "exists": self.exists,
            "files": [item.to_dict() for item in self.files],
            "kind": self.kind,
            "metadata": {key: self.metadata[key] for key in sorted(self.metadata)},
            "name": self.name,
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class PersistenceInventory:
    """Complete read-only inventory for the active persistence boundary."""

    active_root: Path
    versions: dict[str, str | None]
    stores: tuple[StoreInventory, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "active_root": str(self.active_root),
            "stores": [store.to_dict() for store in self.stores],
            "versions": {key: self.versions[key] for key in sorted(self.versions)},
        }


def discover_persistence_paths(root: str | Path | None = None) -> PersistencePaths:
    """Resolve current store paths without initializing any persistence client."""
    if root is None:
        from phasenox.infrastructure.config import get_application_root, settings

        active_root = get_application_root().expanduser().resolve()
        rag_chroma = Path(settings.chroma.path).expanduser().resolve()
    else:
        active_root = Path(root).expanduser().resolve()
        rag_chroma = active_root / "data" / "chroma"

    return PersistencePaths(
        active_root=active_root,
        rag_chroma=rag_chroma,
        memory_vector=active_root / "data" / "vector_db",
        sqlite_catalog=active_root / "data" / "index.db",
    )


def collect_persistence_inventory(
    root: str | Path | None = None,
    *,
    versions: dict[str, str | None] | None = None,
) -> PersistenceInventory:
    """Inventory persistence using file reads and immutable SQLite connections only."""
    paths = discover_persistence_paths(root)
    detected_versions = dict(versions) if versions is not None else _runtime_versions()

    stores = (
        _inspect_chroma_store(
            "rag_chroma",
            paths.rag_chroma,
            detected_versions.get("chromadb"),
        ),
        _inspect_chroma_store(
            "memory_vector",
            paths.memory_vector,
            detected_versions.get("chromadb"),
        ),
        _inspect_catalog_store(paths.sqlite_catalog),
    )
    return PersistenceInventory(
        active_root=paths.active_root,
        versions=detected_versions,
        stores=stores,
    )


def _runtime_versions() -> dict[str, str | None]:
    return {
        "chromadb": _distribution_version("chromadb"),
        "phasenox": _distribution_version("phasenox"),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
    }


def _distribution_version(name: str) -> str | None:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _inspect_chroma_store(name: str, path: Path, version: str | None) -> StoreInventory:
    path = path.resolve()
    files = _inventory_files(path)
    exists = path.is_dir()
    database = path / "chroma.sqlite3"
    if not exists:
        return StoreInventory(
            name=name,
            kind="chroma",
            path=path,
            exists=False,
            available=False,
            size_bytes=0,
            version=version,
            error="store directory is missing",
        )
    if not database.is_file():
        return StoreInventory(
            name=name,
            kind="chroma",
            path=path,
            exists=True,
            available=False,
            size_bytes=_total_size(files),
            version=version,
            files=files,
            error="chroma.sqlite3 is missing",
        )

    try:
        with closing(_read_only_sqlite(database)) as connection:
            tables = _table_names(connection)
            collections = _read_chroma_collections(connection, tables)
            sqlite_user_version = connection.execute("PRAGMA user_version").fetchone()[0]
    except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        return StoreInventory(
            name=name,
            kind="chroma",
            path=path,
            exists=True,
            available=False,
            size_bytes=_total_size(files),
            version=version,
            files=files,
            error=f"{type(exc).__name__}: {exc}",
        )

    return StoreInventory(
        name=name,
        kind="chroma",
        path=path,
        exists=True,
        available=True,
        size_bytes=_total_size(files),
        version=version,
        files=files,
        collections=collections,
        metadata={
            "sqlite_table_count": len(tables),
            "sqlite_user_version": sqlite_user_version,
        },
    )


def _inspect_catalog_store(path: Path) -> StoreInventory:
    path = path.resolve()
    files = _inventory_files(path)
    if not path.is_file():
        return StoreInventory(
            name="sqlite_catalog",
            kind="sqlite",
            path=path,
            exists=False,
            available=False,
            size_bytes=0,
            version=None,
            error="catalog database is missing",
        )

    try:
        with closing(_read_only_sqlite(path)) as connection:
            tables = _table_names(connection)
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]
            record_count = None
            schema = None
            if "indexed_audio" in tables:
                record_count = connection.execute("SELECT COUNT(*) FROM indexed_audio").fetchone()[
                    0
                ]
                row = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='indexed_audio'"
                ).fetchone()
                schema = row[0] if row else None
    except (OSError, sqlite3.Error) as exc:
        return StoreInventory(
            name="sqlite_catalog",
            kind="sqlite",
            path=path,
            exists=True,
            available=False,
            size_bytes=_total_size(files),
            version=None,
            files=files,
            error=f"{type(exc).__name__}: {exc}",
        )

    return StoreInventory(
        name="sqlite_catalog",
        kind="sqlite",
        path=path,
        exists=True,
        available=True,
        size_bytes=_total_size(files),
        version=str(user_version),
        files=files,
        metadata={
            "indexed_audio_count": record_count,
            "indexed_audio_schema": schema,
            "sqlite_tables": tables,
            "sqlite_user_version": user_version,
        },
    )


def _read_chroma_collections(
    connection: sqlite3.Connection,
    tables: tuple[str, ...],
) -> tuple[CollectionInventory, ...]:
    if "collections" not in tables:
        raise ValueError("Chroma collections table is missing")

    columns = _column_names(connection, "collections")
    selected = [
        name
        for name in ("id", "name", "dimension", "config_json_str", "schema_str")
        if name in columns
    ]
    if "id" not in selected or "name" not in selected:
        raise ValueError("Chroma collections table lacks required id/name columns")

    query = (
        "SELECT " + ", ".join(_quote_identifier(name) for name in selected) + " FROM collections"
    )
    counts = _chroma_record_counts(connection, tables)
    output = []
    for row in connection.execute(query):
        values = dict(zip(selected, row))
        collection_id = str(values["id"])
        collection_metadata = _chroma_collection_metadata(connection, tables, collection_id)
        distance_space, embedding_function = _chroma_schema_metadata(
            values.get("schema_str"),
            collection_metadata,
        )
        output.append(
            CollectionInventory(
                name=str(values["name"]),
                record_count=counts.get(collection_id),
                dimension=values.get("dimension"),
                distance_space=distance_space,
                embedding_function=embedding_function,
                metadata=collection_metadata,
            )
        )
    return tuple(sorted(output, key=lambda item: item.name))


def _chroma_record_counts(
    connection: sqlite3.Connection,
    tables: tuple[str, ...],
) -> dict[str, int]:
    if not {"segments", "embeddings"}.issubset(tables):
        return {}
    query = """
        SELECT s.collection, COUNT(e.id)
        FROM segments AS s
        LEFT JOIN embeddings AS e ON e.segment_id = s.id
        WHERE s.scope = 'METADATA'
        GROUP BY s.collection
    """
    return {str(collection_id): int(count) for collection_id, count in connection.execute(query)}


def _chroma_collection_metadata(
    connection: sqlite3.Connection,
    tables: tuple[str, ...],
    collection_id: str,
) -> dict[str, object]:
    if "collection_metadata" not in tables:
        return {}
    columns = _column_names(connection, "collection_metadata")
    value_columns = [
        name for name in ("str_value", "int_value", "float_value", "bool_value") if name in columns
    ]
    if not value_columns or not {"collection_id", "key"}.issubset(columns):
        return {}

    selected = ["key", *value_columns]
    query = (
        "SELECT "
        + ", ".join(_quote_identifier(name) for name in selected)
        + " FROM collection_metadata WHERE collection_id = ?"
    )
    result: dict[str, object] = {}
    for row in connection.execute(query, (collection_id,)):
        key = str(row[0])
        value = next((item for item in row[1:] if item is not None), None)
        result[key] = value
    return result


def _chroma_schema_metadata(
    raw_schema: object,
    collection_metadata: dict[str, object],
) -> tuple[str | None, object | None]:
    distance_space = collection_metadata.get("hnsw:space")
    embedding_function = None
    if isinstance(raw_schema, str) and raw_schema:
        schema = json.loads(raw_schema)
        config = (
            schema.get("keys", {})
            .get("#embedding", {})
            .get("float_list", {})
            .get("vector_index", {})
            .get("config", {})
        )
        distance_space = config.get("space", distance_space)
        embedding_function = config.get("embedding_function")
    return (
        str(distance_space) if distance_space is not None else None,
        embedding_function,
    )


def _read_only_sqlite(path: Path) -> sqlite3.Connection:
    """Open a SQLite file without creating journals, sidecars, or migrations."""
    uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True)


def _table_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1]) for row in connection.execute(f"PRAGMA table_info({_quote_identifier(table)})")
    }


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _inventory_files(path: Path) -> tuple[FileInventory, ...]:
    if path.is_file() or path.is_symlink():
        return (_inventory_file(path, path.name),)
    if not path.is_dir():
        return ()

    files: list[FileInventory] = []
    for current_root, directory_names, file_names in os.walk(path, followlinks=False):
        directory_names[:] = sorted(
            name for name in directory_names if not (Path(current_root) / name).is_symlink()
        )
        for file_name in sorted(file_names):
            file_path = Path(current_root) / file_name
            relative_path = file_path.relative_to(path).as_posix()
            files.append(_inventory_file(file_path, relative_path))
    return tuple(sorted(files, key=lambda item: item.relative_path))


def _inventory_file(path: Path, relative_path: str) -> FileInventory:
    stat = path.lstat()
    if path.is_symlink():
        target = os.readlink(path)
        digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
        size = len(target.encode("utf-8"))
        kind = "symlink"
    else:
        digest = _sha256_file(path)
        size = stat.st_size
        kind = "file"
    current_stat = path.lstat()
    if (stat.st_mtime_ns, stat.st_size) != (current_stat.st_mtime_ns, current_stat.st_size):
        raise OSError(f"file changed while it was being inventoried: {path}")
    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
    return FileInventory(
        relative_path=relative_path,
        kind=kind,
        size_bytes=size,
        modified_ns=stat.st_mtime_ns,
        modified_at=modified,
        sha256=digest,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _total_size(files: tuple[FileInventory, ...]) -> int:
    return sum(item.size_bytes for item in files)


__all__ = [
    "CollectionInventory",
    "FileInventory",
    "PersistenceInventory",
    "PersistencePaths",
    "StoreInventory",
    "collect_persistence_inventory",
    "discover_persistence_paths",
]
