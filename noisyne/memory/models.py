from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class UserProfile:
    """User-level preferences that may override Knowledge defaults."""

    user_id: str = "default"
    preferred_loudness_by_platform: dict[str, float] = field(default_factory=dict)
    preferred_true_peak_max: float | None = None
    preferred_dynamic_range_min: float | None = None
    preferred_plugin_brands: list[str] = field(default_factory=list)
    preferred_genres: list[str] = field(default_factory=list)
    preferred_processing_order: list[str] = field(default_factory=list)
    preferred_export_targets: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProjectProfile:
    """Project-level context that may influence Memory overrides."""

    project_id: str = "default"
    target_platform: str | None = None
    genre: str | None = None
    reference_paths: list[str] = field(default_factory=list)
    delivery_targets: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MemoryBundle:
    """Complete versioned memory bundle for a user/project session."""

    version: str
    user_profile: UserProfile
    project_profile: ProjectProfile

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dictionary representation for serialization."""
        from dataclasses import asdict

        return asdict(self)
