from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ._serialization import JsonContract
from .common import MethodMetadata, ScalarValue, _require_identifier, _require_non_negative


class ListeningLevel(str, Enum):
    """Qualitative listening-level assumption; not a medical hearing model."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class MonoCompatibility(str, Enum):
    """Declared delivery expectation for mono compatibility."""

    NOT_REQUIRED = "not_required"
    PREFERRED = "preferred"
    REQUIRED = "required"


@dataclass(frozen=True, slots=True)
class PlaybackConstraint(JsonContract):
    """Named profile constraint without implementing a filter or transformation."""

    constraint_id: str
    value: ScalarValue | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.constraint_id, "constraint_id")


@dataclass(frozen=True, slots=True)
class PlaybackProfileReference(JsonContract):
    """Stable identity of a target playback profile."""

    profile_id: str
    version: str

    def __post_init__(self) -> None:
        _require_identifier(self.profile_id, "profile_id")
        _require_identifier(self.version, "profile version")


@dataclass(frozen=True, slots=True)
class PlaybackProfile(JsonContract):
    """Versioned reproduction context description; it makes no emulation claim."""

    profile_id: str
    display_name: str
    version: str
    description: str
    assumptions: list[str] = field(default_factory=list)
    method: MethodMetadata | None = None
    constraints: list[PlaybackConstraint] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.profile_id, "profile_id")
        _require_identifier(self.display_name, "display_name")
        _require_identifier(self.version, "profile version")
        _require_identifier(self.description, "profile description")

    @property
    def reference(self) -> PlaybackProfileReference:
        return PlaybackProfileReference(profile_id=self.profile_id, version=self.version)


@dataclass(frozen=True, slots=True)
class PerceptualContext(JsonContract):
    """Optional listener, genre, artistic, delivery, and playback assumptions."""

    genre: str | None = None
    style: str | None = None
    artistic_intent: str | None = None
    delivery_target: str | None = None
    playback_expectation: PlaybackProfileReference | None = None
    listening_level: ListeningLevel | None = None
    listening_level_db_spl: float | None = None
    mono_compatibility: MonoCompatibility | None = None
    listener_use_case: str | None = None
    listener_preferences: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.listening_level_db_spl is not None:
            _require_non_negative(self.listening_level_db_spl, "listening_level_db_spl")
