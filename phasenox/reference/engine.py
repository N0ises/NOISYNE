from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from phasenox.audio.io.models import AudioData

from .models import ReferenceIntent, ReferenceReport
from .report_builder import ReferenceReportBuilder
from .service import ReferenceService


class ReferenceEngine:
    """
    High level entry point for PHASENOX Reference Intelligence.

    Workflow

        Reference Audio
                │
                ▼
        ReferenceService
                │
                ▼
        ReferenceComparison
                │
                ▼
        Engineering Decisions
                │
                ▼
        Report Builder
    """

    def __init__(
        self,
        service: ReferenceService | None = None,
        report_builder: ReferenceReportBuilder | None = None,
    ) -> None:

        self.service = service or ReferenceService()

        self.report_builder = report_builder or ReferenceReportBuilder()

    def compare(
        self,
        reference: AudioData,
        current: AudioData,
        *,
        intent: ReferenceIntent | None = None,
    ) -> ReferenceReport:

        return self.service.compare(
            reference=reference,
            current=current,
            intent=intent,
        )

    def compare_files(
        self,
        reference_audio: str | Path,
        current_audio: str | Path,
        *,
        intent: ReferenceIntent | None = None,
    ) -> ReferenceReport:

        return self.service.compare_files(
            reference_audio=reference_audio,
            current_audio=current_audio,
            intent=intent,
        )

    def compare_files_multiple(
        self,
        reference_audio: Sequence[str | Path],
        current_audio: str | Path,
        *,
        intent: ReferenceIntent | None = None,
    ) -> ReferenceReport:

        return self.service.compare_files_multiple(
            reference_audio=reference_audio,
            current_audio=current_audio,
            intent=intent,
        )

    def export_json(
        self,
        report: ReferenceReport,
        output: str | Path,
    ) -> Path:

        return self.report_builder.save_json(
            report,
            output,
        )

    def export_markdown(
        self,
        report: ReferenceReport,
        output: str | Path,
    ) -> Path:

        return self.report_builder.save_markdown(
            report,
            output,
        )

    def compare_and_export(
        self,
        reference_audio: str | Path | Sequence[str | Path],
        current_audio: str | Path,
        output_directory: str | Path,
        *,
        intent: ReferenceIntent | None = None,
    ) -> ReferenceReport:

        output_directory = Path(output_directory)

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        if isinstance(reference_audio, (str, Path)):

            report = self.compare_files(
                reference_audio=reference_audio,
                current_audio=current_audio,
                intent=intent,
            )

        else:

            report = self.compare_files_multiple(
                reference_audio=reference_audio,
                current_audio=current_audio,
                intent=intent,
            )

        self.export_json(
            report,
            output_directory / "reference_report.json",
        )

        self.export_markdown(
            report,
            output_directory / "reference_report.md",
        )

        return report
