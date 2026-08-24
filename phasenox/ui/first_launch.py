"""Minimal pre-backend Data Root confirmation for packaged first launch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .data_location import (
    DataRootAvailability,
    DataRootSource,
    InstallerDataRootHandoff,
    data_root_pointer_path,
    discard_installer_handoff,
    installer_handoff_path,
    normalize_path,
    read_installer_handoff,
    validate_data_root,
)
from .startup import DesktopStartupResolution, prepare_desktop_startup


@dataclass(frozen=True, slots=True)
class DataRootConfirmation:
    path: Path
    create_if_missing: bool
    source: DataRootSource


class DataRootDialog(QDialog):
    def __init__(
        self,
        candidate: Path | None,
        *,
        pointer_exists: bool,
        reason: str | None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("PHASENØX Data Location")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        title = QLabel("Confirm the PHASENOX Data Root before persistent services start.")
        title.setWordWrap(True)
        layout.addWidget(title)
        detail = QLabel(
            reason or "The installer suggestion is independent from the application install folder."
        )
        detail.setWordWrap(True)
        layout.addWidget(detail)
        if pointer_exists:
            warning = QLabel(
                "An existing Data Root pointer will remain unchanged unless you explicitly "
                "confirm a replacement below. No data will be moved or merged."
            )
            warning.setWordWrap(True)
            layout.addWidget(warning)

        row = QHBoxLayout()
        self.path_edit = QLineEdit(str(candidate) if candidate is not None else "")
        self.path_edit.setPlaceholderText("Select an existing root or enter a new empty folder")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        self.create_missing = QCheckBox("Create this folder if it does not exist")
        self.create_missing.setChecked(candidate is not None and not candidate.exists())
        layout.addWidget(self.create_missing)
        note = QLabel(
            "Models and persistent stores are not created by this step. Cancel keeps "
            "PHASENØX in recovery with persistent backends disabled."
        )
        note.setWordWrap(True)
        note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Confirm Data Location")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select existing PHASENOX Data Root",
            self.path_edit.text().strip(),
        )
        if selected:
            self.path_edit.setText(selected)
            self.create_missing.setChecked(False)

    def confirmation(self, source: DataRootSource) -> DataRootConfirmation | None:
        value = self.path_edit.text().strip()
        if not value:
            return None
        return DataRootConfirmation(normalize_path(value), self.create_missing.isChecked(), source)


def commit_data_root_confirmation(
    current: DesktopStartupResolution,
    confirmation: DataRootConfirmation,
    *,
    application_version: str,
) -> DesktopStartupResolution:
    """Validate an explicit choice and atomically commit it through Sprint 18."""
    candidate = confirmation.path
    if not candidate.exists() and confirmation.create_if_missing:
        candidate.mkdir(parents=True, exist_ok=False)
    availability = validate_data_root(candidate)
    if availability is not DataRootAvailability.AVAILABLE:
        raise ValueError(f"Selected Data Root is {availability.value}: {candidate}")
    resolved = prepare_desktop_startup(
        application_version=application_version,
        locations=current.locations,
        environ={},
        requested_data_root=candidate,
        requested_data_root_source=confirmation.source,
    )
    if resolved.backend_enabled:
        discard_installer_handoff(installer_handoff_path(current.locations.canonical_root))
    return resolved


def recover_data_root_interactively(
    current: DesktopStartupResolution,
    *,
    application_version: str,
) -> DesktopStartupResolution:
    """Show a pre-backend chooser; cancellation preserves the blocked resolution."""
    source = current.data_root.selection.source
    if source in {
        DataRootSource.PHASENOX_ENVIRONMENT,
        DataRootSource.NOISYNE_ENVIRONMENT,
        DataRootSource.SOUNDBRAIN_ENVIRONMENT,
    }:
        QMessageBox.critical(
            None,
            "PHASENØX Data Location unavailable",
            (current.reason or "The environment-selected Data Root is unavailable.")
            + "\n\nCorrect or remove the environment override, then retry.",
        )
        return current

    handoff_path = installer_handoff_path(current.locations.canonical_root)
    handoff, handoff_error = read_installer_handoff(handoff_path)
    candidate = handoff.candidate_path if handoff is not None else current.data_root.selection.path
    pointer_exists = data_root_pointer_path(current.locations.canonical_root).is_file()
    reason = current.reason
    if handoff_error:
        reason = f"The installer suggestion was invalid ({handoff_error}). Select a location."
    dialog = DataRootDialog(candidate, pointer_exists=pointer_exists, reason=reason)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return current
    source = (
        DataRootSource.INSTALLER
        if isinstance(handoff, InstallerDataRootHandoff)
        else DataRootSource.USER
    )
    confirmation = dialog.confirmation(source)
    if confirmation is None:
        QMessageBox.warning(None, "PHASENØX Data Location", "Select a Data Location first.")
        return current
    if pointer_exists:
        accepted = QMessageBox.question(
            None,
            "Replace Data Root pointer?",
            "Replace the existing pointer with this explicitly selected location? "
            "No data will be moved or merged.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if accepted is not QMessageBox.StandardButton.Yes:
            return current
    try:
        return commit_data_root_confirmation(
            current,
            confirmation,
            application_version=application_version,
        )
    except (OSError, ValueError) as exc:
        QMessageBox.critical(None, "PHASENØX Data Location unavailable", str(exc))
        return current


__all__ = [
    "DataRootConfirmation",
    "DataRootDialog",
    "commit_data_root_confirmation",
    "recover_data_root_interactively",
]
