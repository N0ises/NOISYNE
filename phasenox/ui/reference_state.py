"""Qt-free deterministic state for the Reference Intelligence workflow."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from .contracts import (
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    ReferenceComparisonCommand,
)


class ReferencePhase(str, Enum):
    EMPTY = "empty"
    INVALID = "invalid"
    READY = "ready"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class ReferenceCapabilityState:
    lifecycle: CapabilityLifecycle | None = None
    availability: Availability = Availability.UNKNOWN
    reason: str = "Capability status has not been reported."

    @property
    def executable(self) -> bool:
        return (
            self.lifecycle is not None
            and self.lifecycle is not CapabilityLifecycle.PLANNED
            and self.availability is not Availability.UNAVAILABLE
        )


@dataclass(frozen=True, slots=True)
class ReferenceFormState:
    phase: ReferencePhase = ReferencePhase.EMPTY
    current_path: Path | None = None
    reference_paths: tuple[Path, ...] = ()
    genre: str = ""
    mood: str = ""
    target: str = ""
    focus_areas: tuple[str, ...] = ()
    output_directory: Path | None = None
    capability: ReferenceCapabilityState = ReferenceCapabilityState()
    validation_message: str = "Choose a current track and at least one reference."

    @classmethod
    def initial(cls, capabilities: tuple[CapabilitySnapshot, ...] = ()) -> ReferenceFormState:
        return cls(capability=_reference_capability(capabilities))

    def with_capabilities(self, capabilities: tuple[CapabilitySnapshot, ...]) -> ReferenceFormState:
        return replace(self, capability=_reference_capability(capabilities)).validate()

    def select_current(self, path: Path | None) -> ReferenceFormState:
        return replace(self, current_path=path).validate()

    def add_references(self, paths: tuple[Path, ...]) -> ReferenceFormState:
        existing = {_path_key(path) for path in self.reference_paths}
        references = list(self.reference_paths)
        for path in paths:
            if _path_key(path) not in existing:
                existing.add(_path_key(path))
                references.append(path)
        return replace(self, reference_paths=tuple(references)).validate()

    def remove_reference(self, path: Path) -> ReferenceFormState:
        key = _path_key(path)
        return replace(
            self,
            reference_paths=tuple(item for item in self.reference_paths if _path_key(item) != key),
        ).validate()

    def configure(
        self,
        *,
        genre: str,
        mood: str,
        target: str,
        focus_areas: tuple[str, ...],
        output_directory: Path | None,
    ) -> ReferenceFormState:
        return replace(
            self,
            genre=genre.strip(),
            mood=mood.strip(),
            target=target.strip(),
            focus_areas=tuple(item.strip() for item in focus_areas if item.strip()),
            output_directory=output_directory,
        ).validate()

    def validate(self) -> ReferenceFormState:
        if self.current_path is None:
            return replace(
                self,
                phase=ReferencePhase.EMPTY,
                validation_message="Choose a current track.",
            )
        if not self.current_path.exists() or not self.current_path.is_file():
            return replace(
                self,
                phase=ReferencePhase.INVALID,
                validation_message="The selected current track is missing or is not a file.",
            )
        if not self.reference_paths:
            return replace(
                self,
                phase=ReferencePhase.EMPTY,
                validation_message="Choose at least one reference track.",
            )
        if any(not path.exists() or not path.is_file() for path in self.reference_paths):
            return replace(
                self,
                phase=ReferencePhase.INVALID,
                validation_message="A selected reference track is missing or is not a file.",
            )
        if (
            self.output_directory is not None
            and self.output_directory.exists()
            and not self.output_directory.is_dir()
        ):
            return replace(
                self,
                phase=ReferencePhase.INVALID,
                validation_message="The report output path is not a directory.",
            )
        if not self.capability.executable:
            return replace(
                self,
                phase=ReferencePhase.INVALID,
                validation_message=(
                    "Reference comparison is unavailable. " + self.capability.reason
                ).strip(),
            )
        return replace(self, phase=ReferencePhase.READY, validation_message="Ready to review.")

    def review(self) -> ReferenceFormState:
        validated = self.validate()
        return (
            replace(validated, phase=ReferencePhase.REVIEW)
            if validated.phase is ReferencePhase.READY
            else validated
        )

    def build_command(self) -> ReferenceComparisonCommand:
        if self.phase is not ReferencePhase.REVIEW or self.current_path is None:
            raise ValueError("Reference comparison must be valid and confirmed before dispatch.")
        return ReferenceComparisonCommand(
            current_path=self.current_path,
            reference_paths=self.reference_paths,
            genre=self.genre,
            mood=self.mood,
            target=self.target,
            focus_areas=self.focus_areas,
            output_directory=self.output_directory,
        )


def _reference_capability(
    capabilities: tuple[CapabilitySnapshot, ...],
) -> ReferenceCapabilityState:
    capability = next((item for item in capabilities if item.id == "reference_comparison"), None)
    if capability is None:
        return ReferenceCapabilityState()
    return ReferenceCapabilityState(
        lifecycle=capability.lifecycle,
        availability=capability.availability,
        reason=capability.reason or "No availability reason was supplied.",
    )


def _path_key(path: Path) -> str:
    return str(path.resolve(strict=False)).casefold()

