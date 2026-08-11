from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from brain.audio.analysis import AudioAnalyzer
from brain.audio.analysis.models import AnalysisResult
from brain.audio.context import AudioContext
from brain.audio.context.detector import AudioContextDetector
from brain.audio.engineer import AudioEngineer
from brain.audio.engineer.models import EngineerResult
from brain.audio.io import AudioIOService
from brain.audio.io.models import AudioData
from brain.report import ReportBuilder, ReportExporter, SoundBrainReport


@dataclass(slots=True, frozen=True)
class AudioReviewRequest:
    audio_path: str | Path
    include_semantic_analysis: bool = False
    summary: str = ""
    output_path: str | Path | None = None


@dataclass(slots=True)
class AudioReviewResult:
    audio: AudioData
    analysis: AnalysisResult
    context: AudioContext
    engineering: EngineerResult
    report: SoundBrainReport


class AudioReviewService:
    """Runs the deterministic V1 review flow for a single audio file."""

    def __init__(
        self,
        *,
        audio_io: AudioIOService | None = None,
        analyzer: AudioAnalyzer | None = None,
        context_detector: AudioContextDetector | None = None,
        engineer: AudioEngineer | None = None,
        report_builder: ReportBuilder | None = None,
        report_exporter: ReportExporter | None = None,
    ) -> None:
        self._audio_io = audio_io or AudioIOService()
        self._analyzer = analyzer or AudioAnalyzer()
        self._context_detector = context_detector or AudioContextDetector()
        self._engineer = engineer or AudioEngineer()
        self._report_builder = report_builder or ReportBuilder()
        self._report_exporter = report_exporter or ReportExporter()

    def review(
        self,
        request: AudioReviewRequest,
    ) -> AudioReviewResult:
        audio = self._audio_io.load(request.audio_path)
        analysis = self._analyzer.analyze(audio)

        context = self._context_detector.detect(
            analysis,
            audio if request.include_semantic_analysis else None,
        )

        engineering = self._engineer.analyze(
            analysis,
            context=context,
        )

        report = self._report_builder.build(
            analysis,
            engineering,
            context,
            request.summary,
            analysis_dict=asdict(analysis),
        )

        if request.output_path is not None:
            self._report_exporter.save_json(
                report,
                str(request.output_path),
            )

        return AudioReviewResult(
            audio=audio,
            analysis=analysis,
            context=context,
            engineering=engineering,
            report=report,
        )
