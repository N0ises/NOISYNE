"""Small, versioned persistence boundary for non-sensitive desktop session state."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from .contracts import AnalysisViewResult, ReportDescriptor
from .presentation_state import (
    NavigationState,
    PageId,
    PresentationState,
    RecentAnalysis,
    RecentPath,
    RecentReport,
    SessionState,
)

if TYPE_CHECKING:
    from .presentation_store import PresentationStore

SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = frozenset({1, 2})


@dataclass(frozen=True, slots=True)
class SessionLoadResult:
    session: SessionState
    recovered_from_corruption: bool = False
    warning: str | None = None
    backup_path: Path | None = None


class SessionRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> SessionLoadResult:
        try:
            if not self.path.exists():
                return SessionLoadResult(SessionState())
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return SessionLoadResult(_decode_session(payload))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            backup_path = self._quarantine_corrupt_file()
            return SessionLoadResult(
                SessionState(),
                recovered_from_corruption=True,
                warning=(
                    "Saved desktop session data was invalid and was replaced with safe defaults."
                ),
                backup_path=backup_path,
            )

    def save(self, session: SessionState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(_encode_session(session), indent=2, sort_keys=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _quarantine_corrupt_file(self) -> Path | None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = self.path.with_name(f"{self.path.stem}.corrupt-{timestamp}{self.path.suffix}")
        counter = 1
        while backup.exists():
            backup = self.path.with_name(
                f"{self.path.stem}.corrupt-{timestamp}-{counter}{self.path.suffix}"
            )
            counter += 1
        try:
            self.path.replace(backup)
        except OSError:
            return None
        return backup


class SessionPersistenceBinding:
    """Persist only meaningful immutable SessionState transitions."""

    def __init__(self, repository: SessionRepository, store: PresentationStore) -> None:
        self._repository = repository
        self._store = store
        self._last_payload = _encode_session(store.state.session)
        self._unsubscribe = store.subscribe(self._state_changed)

    def save_current(self) -> bool:
        return self._save(self._store.state.session)

    def close(self) -> None:
        self._unsubscribe()

    def _state_changed(self, state: PresentationState) -> None:
        payload = _encode_session(state.session)
        if payload == self._last_payload:
            return
        self._save(state.session)

    def _save(self, session: SessionState) -> bool:
        try:
            self._repository.save(session)
        except OSError as exc:
            from .errors import session_persistence_error

            self._last_payload = _encode_session(session)
            self._store.add_error(session_persistence_error(exc))
            return False
        self._last_payload = _encode_session(session)
        return True


def _encode_session(session: SessionState) -> dict[str, object]:
    result = session.last_analysis_result
    return {
        "schema_version": SCHEMA_VERSION,
        "navigation": session.navigation.current_page.value,
        "selected_audio": _path_or_none(session.selected_audio),
        "selected_references": [str(path) for path in session.selected_references],
        "selected_report_path": _path_or_none(session.selected_report_path),
        "last_analysis": _encode_result(result) if result is not None else None,
        "last_knowledge_query": session.last_knowledge_query,
        "recent_knowledge_queries": list(session.recent_knowledge_queries),
        "recent_analyses": [_encode_analysis(item) for item in session.recent_analyses],
        "recent_reports": [_encode_report(item) for item in session.recent_reports],
        "recent_references": [_encode_recent_path(item) for item in session.recent_references],
        "recent_files": [_encode_recent_path(item) for item in session.recent_files],
    }


def _decode_session(payload: object) -> SessionState:
    if not isinstance(payload, dict):
        raise TypeError("Expected a JSON object.")
    version = payload.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError("Unsupported desktop session schema.")
    navigation = NavigationState(current_page=PageId(str(payload["navigation"])))
    selected_audio = _optional_path(payload.get("selected_audio"))
    selected_references = _unique_paths(
        Path(_string(value)) for value in _list(payload.get("selected_references"))
    )
    recent_analyses = _unique_items(
        (_decode_analysis(item) for item in _list(payload.get("recent_analyses"))),
        lambda item: _path_key(item.source_path),
    )
    recent_reports = _unique_items(
        (_decode_report(item) for item in _list(payload.get("recent_reports"))),
        lambda item: _path_key(item.descriptor.path),
    )
    recent_references = _unique_items(
        (_decode_recent_path(item) for item in _list(payload.get("recent_references"))),
        lambda item: _path_key(item.path),
    )
    recent_files = _unique_items(
        (_decode_recent_path(item) for item in _list(payload.get("recent_files"))),
        lambda item: _path_key(item.path),
    )
    return SessionState(
        navigation=navigation,
        selected_audio=selected_audio,
        selected_references=selected_references,
        selected_report_path=_optional_path(payload.get("selected_report_path")),
        last_analysis_result=_decode_result(payload.get("last_analysis")),
        last_knowledge_query=_string(payload.get("last_knowledge_query", "")),
        recent_knowledge_queries=_unique_strings(_list(payload.get("recent_knowledge_queries"))),
        recent_analyses=recent_analyses,
        recent_reports=recent_reports,
        recent_references=recent_references,
        recent_files=recent_files,
    )


def _encode_result(result: AnalysisViewResult) -> dict[str, object]:
    # Deliberately omit free-text analysis, issues, metrics, and warnings.
    return {
        "source_path": str(result.source_path),
        "status": result.status,
        "audio_type": result.audio_type,
        "score": result.score,
        "reference_similarity": result.reference_similarity,
        "reports": [_encode_descriptor(item) for item in result.reports],
    }


def _decode_result(value: object) -> AnalysisViewResult | None:
    if value is None:
        return None
    item = _dict(value)
    return AnalysisViewResult(
        source_path=Path(str(item["source_path"])),
        status=str(item["status"]),
        audio_type=str(item["audio_type"]),
        score=float(item["score"]),
        summary="",
        reference_similarity=_optional_float(item.get("reference_similarity")),
        reports=tuple(_decode_descriptor(entry) for entry in _list(item.get("reports"))),
    )


def _encode_analysis(item: RecentAnalysis) -> dict[str, object]:
    return {
        "source_path": str(item.source_path),
        "analyzed_at": item.analyzed_at.isoformat(),
        "status": item.status,
        "audio_type": item.audio_type,
        "score": item.score,
    }


def _decode_analysis(value: object) -> RecentAnalysis:
    item = _dict(value)
    path = Path(str(item["source_path"]))
    return RecentAnalysis(
        source_path=path,
        analyzed_at=_datetime(item["analyzed_at"]),
        status=str(item["status"]),
        audio_type=str(item["audio_type"]),
        score=float(item["score"]),
        source_exists=path.exists(),
    )


def _encode_report(item: RecentReport) -> dict[str, object]:
    return {
        "descriptor": _encode_descriptor(item.descriptor),
        "created_at": item.created_at.isoformat(),
    }


def _decode_report(value: object) -> RecentReport:
    item = _dict(value)
    descriptor = _decode_descriptor(item["descriptor"])
    return RecentReport(
        descriptor=descriptor,
        created_at=_datetime(item["created_at"]),
        exists=descriptor.path.exists(),
    )


def _encode_descriptor(item: ReportDescriptor) -> dict[str, str]:
    encoded = {
        "kind": item.kind,
        "format": item.format,
        "path": str(item.path),
        "display_label": item.display_label,
    }
    if item.source_path is not None:
        encoded["source_path"] = str(item.source_path)
    return encoded


def _decode_descriptor(value: object) -> ReportDescriptor:
    item = _dict(value)
    return ReportDescriptor(
        kind=str(item["kind"]),
        format=str(item["format"]),
        path=Path(str(item["path"])),
        display_label=str(item["display_label"]),
        source_path=(
            Path(str(item["source_path"])) if item.get("source_path") is not None else None
        ),
    )


def _encode_recent_path(item: RecentPath) -> dict[str, str]:
    return {"path": str(item.path), "last_used_at": item.last_used_at.isoformat()}


def _decode_recent_path(value: object) -> RecentPath:
    item = _dict(value)
    path = Path(str(item["path"]))
    return RecentPath(path=path, last_used_at=_datetime(item["last_used_at"]), exists=path.exists())


def _dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object.")
    return value


def _list(value: object) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("Expected a JSON list.")
    return value


def _datetime(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _path_or_none(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def _optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("Expected a path string.")
    return Path(value)


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _path_key(path: Path) -> str:
    return str(path.expanduser().resolve(strict=False)).casefold()


def _unique_paths(paths, limit: int = 20) -> tuple[Path, ...]:
    return _unique_items(paths, _path_key, limit)


def _unique_items(items, key, limit: int = 20) -> tuple:
    unique = []
    seen = set()
    for item in items:
        item_key = key(item)
        if item_key in seen:
            continue
        seen.add(item_key)
        unique.append(item)
        if len(unique) == limit:
            break
    return tuple(unique)


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected a string.")
    return value


def _unique_strings(values: list[object], limit: int = 20) -> tuple[str, ...]:
    strings = (_string(value) for value in values)
    return _unique_items((value for value in strings if value.strip()), str, limit)
