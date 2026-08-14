from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from noisyne.infrastructure.config import get_application_root

from .errors import MemoryConfigurationError
from .models import MemoryBundle, ProjectProfile, UserProfile


_DEFAULT_MEMORY_ROOT = "configs/memory"


def _resolve_root(root: str | Path) -> Path:
    path = Path(root)
    if path.is_absolute():
        return path.resolve()
    return (get_application_root() / path).resolve()


class MemoryLoader:
    """Load a MemoryBundle from YAML files or an inline dictionary."""

    def __init__(self, root: str | Path = _DEFAULT_MEMORY_ROOT) -> None:
        self._root = _resolve_root(root)

    def load(self) -> MemoryBundle:
        """Load the default memory bundle from ``root/memory_bundle.yaml``."""
        return self.load_from_path(self._root / "memory_bundle.yaml")

    def load_from_path(self, path: str | Path) -> MemoryBundle:
        """Load a memory bundle from a master YAML file."""
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise MemoryConfigurationError(
                reason="missing",
                path=path,
                message="Memory bundle file does not exist.",
                details=exc,
            ) from exc
        except OSError as exc:
            raise MemoryConfigurationError(
                reason="invalid",
                path=path,
                message="Memory bundle file could not be read.",
                details=exc,
            ) from exc

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise MemoryConfigurationError(
                reason="invalid",
                path=path,
                message="Memory bundle contains invalid YAML.",
                details=exc,
            ) from exc

        if not isinstance(data, dict):
            raise MemoryConfigurationError(
                reason="invalid",
                path=path,
                message="Memory bundle must be a YAML mapping.",
                details=data,
            )
        return self._parse_bundle(data, path.parent)

    def load_from_dict(self, data: dict[str, Any]) -> MemoryBundle:
        """Load a memory bundle from a fully populated dictionary."""
        if not isinstance(data, dict):
            raise MemoryConfigurationError(
                reason="invalid",
                path=None,
                message="Memory bundle must be a mapping.",
                details=data,
            )
        return self._parse_bundle(data, None)

    def _parse_bundle(
        self,
        data: dict[str, Any],
        base_dir: Path | None,
    ) -> MemoryBundle:
        version = str(data.get("version", "0.0.0"))

        user_profile = self._load_section(
            "user_profile",
            data,
            base_dir,
            default_factory=dict,
        )
        project_profile = self._load_section(
            "project_profile",
            data,
            base_dir,
            default_factory=dict,
        )

        return MemoryBundle(
            version=version,
            user_profile=self._parse_user_profile(user_profile),
            project_profile=self._parse_project_profile(project_profile),
        )

    def _load_section(
        self,
        name: str,
        data: dict[str, Any],
        base_dir: Path | None,
        default_factory: Any = None,
    ) -> Any:
        """Resolve a section either inline or from a referenced YAML file.

        An inline empty dictionary (``{}``) is an intentionally empty profile.
        A referenced file that is missing or unreadable is a configuration
        failure and raises :class:`MemoryConfigurationError`.
        """
        value = data.get(name, default_factory() if default_factory else None)
        if isinstance(value, str):
            if base_dir is None:
                raise MemoryConfigurationError(
                    reason="invalid",
                    path=None,
                    message=f"Cannot resolve relative {name} reference without a base directory.",
                    details=value,
                )
            section_path = (base_dir / value).resolve()
            try:
                section_text = section_path.read_text(encoding="utf-8")
            except FileNotFoundError as exc:
                raise MemoryConfigurationError(
                    reason="missing",
                    path=section_path,
                    message=f"Referenced {name} file does not exist.",
                    details=exc,
                ) from exc
            except OSError as exc:
                raise MemoryConfigurationError(
                    reason="invalid",
                    path=section_path,
                    message=f"Referenced {name} file could not be read.",
                    details=exc,
                ) from exc

            try:
                section_data = yaml.safe_load(section_text)
            except yaml.YAMLError as exc:
                raise MemoryConfigurationError(
                    reason="invalid",
                    path=section_path,
                    message=f"Referenced {name} file contains invalid YAML.",
                    details=exc,
                ) from exc

            if not isinstance(section_data, dict):
                raise MemoryConfigurationError(
                    reason="invalid",
                    path=section_path,
                    message=f"Referenced {name} file must contain a YAML mapping.",
                    details=section_data,
                )
            if name in section_data:
                return section_data[name]
            return section_data
        return value

    def _parse_user_profile(self, data: dict[str, Any]) -> UserProfile:
        return UserProfile(
            user_id=str(data.get("user_id", "default")),
            preferred_loudness_by_platform=dict(data.get("preferred_loudness_by_platform", {})),
            preferred_true_peak_max=data.get("preferred_true_peak_max"),
            preferred_dynamic_range_min=data.get("preferred_dynamic_range_min"),
            preferred_plugin_brands=list(data.get("preferred_plugin_brands", [])),
            preferred_genres=list(data.get("preferred_genres", [])),
            preferred_processing_order=list(data.get("preferred_processing_order", [])),
            preferred_export_targets=list(data.get("preferred_export_targets", [])),
            notes=list(data.get("notes", [])),
        )

    def _parse_project_profile(self, data: dict[str, Any]) -> ProjectProfile:
        return ProjectProfile(
            project_id=str(data.get("project_id", "default")),
            target_platform=data.get("target_platform"),
            genre=data.get("genre"),
            reference_paths=list(data.get("reference_paths", [])),
            delivery_targets=list(data.get("delivery_targets", [])),
            notes=list(data.get("notes", [])),
        )
