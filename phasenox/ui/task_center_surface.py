"""Polling Qt Task Center over presentation-safe Desktop job snapshots."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .job_gateway import DesktopJobGateway, DesktopJobSnapshot
from .task_center import TaskCenterState


class TaskCenterDialog(QDialog):
    def __init__(self, gateway: DesktopJobGateway, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gateway = gateway
        self._state = TaskCenterState()
        self.setWindowTitle("PHASENØX Task Center")
        self.setMinimumSize(640, 360)

        layout = QVBoxLayout(self)
        self._jobs = QListWidget()
        self._jobs.setAccessibleName("Scheduled task history")
        self._jobs.currentItemChanged.connect(self._render_selection)
        self._detail = QLabel("No tasks have been submitted in this session.")
        self._detail.setWordWrap(True)
        actions = QHBoxLayout()
        self._pause = QPushButton("Pause queued task")
        self._resume = QPushButton("Resume task")
        self._cancel = QPushButton("Cancel task")
        self._pause.clicked.connect(self._pause_selected)
        self._resume.clicked.connect(self._resume_selected)
        self._cancel.clicked.connect(self._cancel_selected)
        actions.addWidget(self._pause)
        actions.addWidget(self._resume)
        actions.addWidget(self._cancel)
        actions.addStretch(1)
        layout.addWidget(self._jobs, 1)
        layout.addWidget(self._detail)
        layout.addLayout(actions)
        self.render(self._state)

    def render(self, state: TaskCenterState) -> None:
        selected_id = self._selected_job_id()
        self._state = state
        self._jobs.clear()
        for job in state.jobs:
            stage = f" · {job.progress.current_stage}" if job.progress.current_stage else ""
            item = QListWidgetItem(f"{job.operation} · {job.state}{stage}")
            item.setData(256, job.job_id)
            self._jobs.addItem(item)
            if job.job_id == selected_id:
                self._jobs.setCurrentItem(item)
        if self._jobs.currentItem() is None and self._jobs.count():
            self._jobs.setCurrentRow(0)
        self._render_selection()

    def _selected_job_id(self) -> str | None:
        item = self._jobs.currentItem()
        return str(item.data(256)) if item is not None else None

    def _selected(self) -> DesktopJobSnapshot | None:
        job_id = self._selected_job_id()
        return self._state.find(job_id) if job_id is not None else None

    def _render_selection(self, *_args: object) -> None:
        job = self._selected()
        if job is None:
            self._detail.setText("No tasks have been submitted in this session.")
            self._pause.setEnabled(False)
            self._resume.setEnabled(False)
            self._cancel.setEnabled(False)
            return
        details = [f"State: {job.state}", f"Created: {job.created_at}"]
        if job.started_at:
            details.append(f"Started: {job.started_at}")
        if job.finished_at:
            details.append(f"Finished: {job.finished_at}")
        if job.cancellation_mode == "cooperative":
            details.append("Cancellation is cooperative and may not be immediate.")
        if job.error_message:
            details.append(job.error_message)
        if job.resource is not None:
            resource = job.resource
            if resource.cpu_percent is not None:
                details.append(f"Sampled CPU: {resource.cpu_percent:.1f}%")
            if resource.ram_used_bytes is not None:
                details.append(f"Sampled RAM: {resource.ram_used_bytes} bytes")
            if resource.gpu_memory_used_bytes is not None:
                details.append(f"Sampled VRAM: {resource.gpu_memory_used_bytes} bytes")
        self._detail.setText("\n".join(details))
        self._pause.setEnabled(job.can_pause)
        self._resume.setEnabled(job.can_resume)
        self._cancel.setEnabled(job.can_cancel)

    def _pause_selected(self) -> None:
        if (job_id := self._selected_job_id()) is not None:
            self._gateway.pause_job(job_id)

    def _resume_selected(self) -> None:
        if (job_id := self._selected_job_id()) is not None:
            self._gateway.resume_job(job_id)

    def _cancel_selected(self) -> None:
        if (job_id := self._selected_job_id()) is not None:
            self._gateway.cancel_job(job_id)


class TaskCenterSurface(QWidget):
    """Compact global task status with bounded-history polling."""

    def __init__(
        self,
        gateway: DesktopJobGateway,
        *,
        poll_interval_ms: int = 500,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._gateway = gateway
        self._state = TaskCenterState()
        self._dialog = TaskCenterDialog(gateway, self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._summary = QLabel(self._state.summary)
        self._open = QPushButton("Task Center")
        self._open.clicked.connect(self._dialog.show)
        layout.addWidget(self._summary)
        layout.addWidget(self._open)
        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def refresh(self) -> None:
        self._state = TaskCenterState(self._gateway.list_jobs(include_history=True))
        self._summary.setText(self._state.summary)
        self._dialog.render(self._state)

    def stop(self) -> None:
        self._timer.stop()


__all__ = ["TaskCenterDialog", "TaskCenterSurface"]
