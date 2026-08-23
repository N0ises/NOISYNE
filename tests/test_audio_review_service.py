from pathlib import Path

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.context.models import AudioContext
from phasenox.audio.engineer.models import EngineerResult
from phasenox.audio.io.models import AudioData, AudioMetadata
from phasenox.report.models import SoundBrainReport
from phasenox.application.audio_review_service import (
    AudioReviewRequest,
    AudioReviewService,
)


class StubAudioIO:
    def __init__(self, audio: AudioData) -> None:
        self.audio = audio
        self.loaded_path = None

    def load(self, path: str | Path) -> AudioData:
        self.loaded_path = path
        return self.audio


class StubAnalyzer:
    def __init__(self, analysis: AnalysisResult) -> None:
        self.analysis = analysis

    def analyze(self, audio: AudioData) -> AnalysisResult:
        return self.analysis


class StubContextDetector:
    def __init__(self, context: AudioContext) -> None:
        self.context = context
        self.audio_argument = None

    def detect(self, analysis: AnalysisResult, audio: AudioData | None) -> AudioContext:
        self.audio_argument = audio
        return self.context


class StubEngineer:
    def __init__(self, result: EngineerResult) -> None:
        self.result = result

    def analyze(self, analysis: AnalysisResult, *, context: AudioContext) -> EngineerResult:
        return self.result


class StubReportBuilder:
    def __init__(self, report: SoundBrainReport) -> None:
        self.report = report
        self.summary = None

    def build(self, analysis, engineering, context, summary: str, analysis_dict=None) -> SoundBrainReport:
        self.summary = summary
        return self.report


class StubReportExporter:
    def __init__(self) -> None:
        self.saved_report = None
        self.saved_path = None

    def save_json(self, report: SoundBrainReport, path: str) -> None:
        self.saved_report = report
        self.saved_path = path


def create_analysis() -> AnalysisResult:
    return AnalysisResult(
        tempo=120.0,
        pitch=440.0,
        key="A major",
        lufs=-14.0,
        peak=0.8,
        rms=0.2,
        dynamic_range=12.0,
        crest_factor=6.0,
        stereo_width=0.5,
        phase=0.9,
        spectral_centroid=2000.0,
        spectral_bandwidth=2500.0,
        spectral_rolloff=4000.0,
        spectral_flatness=0.01,
        spectral_contrast=20.0,
        zero_crossing_rate=0.1,
        mfcc=[],
        chroma=[],
        onset_count=10,
    )


def test_review_runs_deterministic_flow_without_semantic_model() -> None:
    audio = AudioData(
        samples=[],
        metadata=AudioMetadata(
            path=Path("track.wav"),
            filename="track.wav",
            extension=".wav",
            format="wav",
            codec=None,
            sample_rate=44100,
            channels=2,
            duration=1.0,
            bit_depth=None,
            file_size=1,
        ),
    )
    context = AudioContext(audio_type="music", source_type="mix")
    engineering = EngineerResult(score=90.0)
    report = SoundBrainReport(
        audio_type="music",
        source_type="mix",
        instrument=None,
        is_full_mix=True,
        confidence=0.8,
    )
    context_detector = StubContextDetector(context)
    report_builder = StubReportBuilder(report)
    service = AudioReviewService(
        audio_io=StubAudioIO(audio),
        analyzer=StubAnalyzer(create_analysis()),
        context_detector=context_detector,
        engineer=StubEngineer(engineering),
        report_builder=report_builder,
    )

    result = service.review(
        AudioReviewRequest(
            audio_path="track.wav",
            summary="Deterministic review complete.",
        )
    )

    assert result.audio is audio
    assert result.analysis.key == "A major"
    assert result.context is context
    assert result.engineering is engineering
    assert result.report is report
    assert context_detector.audio_argument is None
    assert report_builder.summary == "Deterministic review complete."


def test_review_passes_audio_to_semantic_context_detection_when_requested() -> None:
    audio = AudioData(
        samples=[],
        metadata=AudioMetadata(
            path=Path("track.wav"),
            filename="track.wav",
            extension=".wav",
            format="wav",
            codec=None,
            sample_rate=44100,
            channels=2,
            duration=1.0,
            bit_depth=None,
            file_size=1,
        ),
    )
    context_detector = StubContextDetector(AudioContext("music", "mix"))
    service = AudioReviewService(
        audio_io=StubAudioIO(audio),
        analyzer=StubAnalyzer(create_analysis()),
        context_detector=context_detector,
        engineer=StubEngineer(EngineerResult(score=90.0)),
        report_builder=StubReportBuilder(
            SoundBrainReport("music", "mix", None, True, 0.8)
        ),
    )

    service.review(
        AudioReviewRequest(
            audio_path="track.wav",
            include_semantic_analysis=True,
        )
    )

    assert context_detector.audio_argument is audio


def test_review_exports_the_report_when_an_output_path_is_requested() -> None:
    audio = AudioData(
        samples=[],
        metadata=AudioMetadata(
            path=Path("track.wav"),
            filename="track.wav",
            extension=".wav",
            format="wav",
            codec=None,
            sample_rate=44100,
            channels=2,
            duration=1.0,
            bit_depth=None,
            file_size=1,
        ),
    )
    report = SoundBrainReport("music", "mix", None, True, 0.8)
    exporter = StubReportExporter()
    service = AudioReviewService(
        audio_io=StubAudioIO(audio),
        analyzer=StubAnalyzer(create_analysis()),
        context_detector=StubContextDetector(AudioContext("music", "mix")),
        engineer=StubEngineer(EngineerResult(score=90.0)),
        report_builder=StubReportBuilder(report),
        report_exporter=exporter,
    )

    service.review(
        AudioReviewRequest(
            audio_path="track.wav",
            output_path="reports/track.json",
        )
    )

    assert exporter.saved_report is report
    assert exporter.saved_path == "reports/track.json"
